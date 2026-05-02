import asyncio
import json
import os
import logging
from typing import Callable, Awaitable, Optional

import httpx

import predict_ensemble

from schemas import ChatResponse, EEGFindings
from orchestrator.state import SessionState
from orchestrator.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from agents.eeg_cleaner.cleaner import clean_eeg
from agents.labram.encoder import encode_eeg
from agents.labram.head_cognitive import classify_cognitive_state
from agents.labram.head_neurological import detect_neurological_patterns
from agents.labram.findings import assemble_findings, findings_to_text
from agents.report_generator.generator import generate_report

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
ORCHESTRATOR_MODEL = os.getenv("ORCHESTRATOR_MODEL", "llama3.1")


class Orchestrator:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=120.0)

    def process_eeg(self, filepath):
        # ** change the checkpoints and seed_folders paths when you run this **
        result = predict_ensemble.run_inference_on_edf(filepath, "checkpoints", "seed_folders")
        return result

    async def _build_messages(self, state: SessionState) -> list[dict]:
        messages = [{"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT.strip()}]

        if state.eeg_findings:
            findings_text = findings_to_text(EEGFindings(**state.eeg_findings))
            messages.append({
                "role": "system",
                "content": f"EEG analysis results for this session:\n{findings_text}",
            })

        for entry in state.conversation_history:
            messages.append({"role": entry["role"], "content": entry["content"]})

        return messages

    async def run(self, state: SessionState, eeg_file_path: Optional[str]) -> ChatResponse:
        report: Optional[str] = None

        if eeg_file_path is not None:
            from agents.labram.pipeline import run_labram_pipeline
            from agents.labram.findings import EEGFindings
            from agents.report_generator.generator import generate_report

            labram_result = run_labram_pipeline(eeg_file_path)

            findings_obj = EEGFindings(
                cognitive_state=labram_result["label"],
                confidence=labram_result["confidence"],
                ad_risk_score=labram_result["alzheimer_rate"],
            )

            state.eeg_findings = findings_obj.model_dump()

            report = generate_report(findings_obj, state.patient_metadata)
            state.last_report = report

        messages = await self._build_messages(state)
        response_text = await self._chat_completion(messages)

        state.conversation_history.append({
            "role": "assistant",
            "content": response_text
        })

        return ChatResponse(
            response=response_text,
            report=report,
        )

    async def stream_response(
        self,
        state: SessionState,
        eeg_bytes: Optional[bytes],
        on_token: Callable[[str], Awaitable[None]],
        on_step: Optional[Callable[[str, str], Awaitable[None]]] = None,
    ):
        findings_obj: Optional[EEGFindings] = None
        report: Optional[str] = None

        async def _step(step: str, status: str):
            if on_step:
                await on_step(step, status)
                await asyncio.sleep(0.3)

        if eeg_bytes is not None:
            await _step("eeg_cleaning", "in_progress")
            cleaned = clean_eeg(eeg_bytes)
            await _step("eeg_cleaning", "completed")

            await _step("labram_encoding", "in_progress")
            embeddings = encode_eeg(cleaned)
            await _step("labram_encoding", "completed")

            await _step("cognitive_classification", "in_progress")
            cognitive = classify_cognitive_state(embeddings)
            await _step("cognitive_classification", "completed")

            await _step("neurological_detection", "in_progress")
            neuro = detect_neurological_patterns(embeddings)
            await _step("neurological_detection", "completed")

            findings_obj = assemble_findings(cognitive, neuro)
            state.eeg_findings = findings_obj.model_dump()

            await _step("report_generation", "in_progress")
            report = generate_report(findings_obj, state.patient_metadata)
            state.last_report = report
            await _step("report_generation", "completed")

        messages = await self._build_messages(state)
        full_response = await self._stream_completion(messages, on_token)
        state.conversation_history.append({"role": "assistant", "content": full_response})

    async def _chat_completion(self, messages: list[dict]) -> str:
        """Non-streaming completion via Ollama API."""
        try:
            prompt = "\n".join([m["content"] for m in messages])

            resp = await self.client.post("/api/generate", json={
                "model": ORCHESTRATOR_MODEL,
                "prompt": prompt,
                "stream": False,
            })

            resp.raise_for_status()
            return resp.json()["response"]
        except Exception as e:
            logger.error(f"Ollama chat completion failed: {e}")
            return _fallback_response(messages)

    async def _stream_completion(
        self,
        messages: list[dict],
        on_token: Callable[[str], Awaitable[None]],
    ) -> str:
        """Streaming completion via Ollama API — sends tokens as they arrive."""
        full_response = ""
        try:
            prompt = "\n".join([m["content"] for m in messages])

            async with self.client.stream("POST", "/api/generate", json={
                "model": ORCHESTRATOR_MODEL,
                "prompt": prompt,
                "stream": True,
            }) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        full_response += token
                        await on_token(token)
                    if chunk.get("done"):
                        break
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            if not full_response:
                full_response = _fallback_response(messages)
                for word in full_response.split(" "):
                    await on_token(word + " ")
                    await asyncio.sleep(0.05)
        return full_response


def _fallback_response(messages: list[dict]) -> str:
    """Fallback when Ollama is unreachable — checks if EEG context was injected."""
    has_eeg = any("EEG analysis results" in m.get("content", "") for m in messages)
    if has_eeg:
        return (
            "I've received the EEG analysis results. However, I'm currently unable to "
            "connect to the language model for a detailed interpretation. Please check "
            "that Ollama is running and the llama3.1 model is available, then try again. "
            "In the meantime, you can review the structured findings and clinical report below."
        )
    return (
        "I'm ready to help with EEG interpretation and neurology questions, but I'm "
        "currently unable to connect to the language model. Please ensure Ollama is "
        "running on port 11434 with the llama3.1 model loaded."
    )
