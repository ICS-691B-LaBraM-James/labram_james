import asyncio
import json
import os
import logging
from typing import Callable, Awaitable, Optional

import httpx

from schemas import ChatResponse, EEGFindings, BandPower
from orchestrator.state import SessionState
from orchestrator.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from agents.eeg_cleaner.cleaner import clean_eeg
from agents.labram.encoder import encode_eeg
from agents.labram.head_cognitive import classify_cognitive_state
from agents.labram.head_neurological import detect_neurological_patterns
from agents.labram.findings import assemble_findings, findings_to_text
from agents.report_generator.generator import generate_report
from agents.lead.predict_ensemble import run_inference_on_edf

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
ORCHESTRATOR_MODEL = os.getenv("ORCHESTRATOR_MODEL", "llama3.1")


class Orchestrator:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=120.0)

    async def _build_messages(self, state: SessionState) -> list[dict]:
        messages = [{"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT.strip()}]

        if state.eeg_findings:
            messages.append({
                "role": "system",
                "content": f"""
EEG STRUCTURED DATA:
{json.dumps(state.eeg_findings, indent=2)}

You must base your reasoning on this data.
"""
            })
            print(json.dumps(state.eeg_findings, indent=2))
            logger.error(json.dumps(state.eeg_findings, indent=2))

        if getattr(state, "raw_pipeline_output", None):
            messages.append({
                "role": "system",
                "content": f"Raw EEG pipeline output:\n{json.dumps(state.raw_pipeline_output)}"
            })

        for entry in state.conversation_history:
            messages.append({"role": entry["role"], "content": entry["content"]})

        return messages

    def process_eeg(self, filepath):
        return run_inference_on_edf(
            edf_path=filepath,
            checkpoint_root=os.getenv("CHECKPOINT_ROOT", "./checkpoints"),
            seed_folders=os.getenv("SEED_FOLDERS", "seed41,seed43,seed44"),
            device=os.getenv("DEVICE", "cuda"),
        )

    def leadv2_to_findings(self, result: dict) -> EEGFindings:
        probs = result["subject_prob"]
        label = int(result["subject_label"][0])

        cognitive_state = "impaired" if label == 1 else "normal"

        patterns = [
            f"HC probability: {probs[0]:.3f}",
            f"AD probability: {probs[1]:.3f}",
        ]

        return EEGFindings(
            cognitive_state=cognitive_state,
            confidence=float(probs[label]),
            model_output={
                "hc_probability": float(probs[0]),
                "ad_probability": float(probs[1]),
            },
            biomarkers={},
            band_power={},
            dominant_frequency_shift="unknown",
            notable_patterns=patterns,
        )

    async def run(self, state: SessionState, eeg_file_path: Optional[str]) -> ChatResponse:
        report: Optional[str] = None

        if eeg_file_path is not None:
            result = run_inference_on_edf(
                edf_path=eeg_file_path,
                checkpoint_root=os.getenv("CHECKPOINT_ROOT", "./checkpoints"),
                seed_folders=os.getenv("SEED_FOLDERS", "seed41,seed43,seed44"),
                device=os.getenv("DEVICE", "cuda"),
            )

            findings_obj = self.leadv2_to_findings(result)

            state.eeg_findings = findings_obj.model_dump()
            state.raw_pipeline_output = result

            logger.error(json.dumps(state.eeg_findings, indent=2))
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
            findings=EEGFindings(**state.eeg_findings) if state.eeg_findings else None,
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
                await asyncio.sleep(0.1)

        if eeg_bytes is not None:
            await _step("eeg_processing", "in_progress")

            def _run():
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".edf") as tmp:
                    tmp.write(eeg_bytes)
                    return tmp.name

            filepath = await asyncio.to_thread(_run)

            result = await asyncio.to_thread(
                run_inference_on_edf,
                filepath,
                os.getenv("CHECKPOINT_ROOT", "./checkpoints"),
                os.getenv("SEED_FOLDERS", "seed41,seed43,seed44"),
                os.getenv("DEVICE", "cuda"),
            )

            findings_obj = self.leadv2_to_findings(result)

            state.eeg_findings = findings_obj.model_dump()
            state.raw_pipeline_output = result

            logger.error(json.dumps(state.eeg_findings, indent=2))

            await _step("eeg_processing", "completed")

            await _step("report_generation", "in_progress")
            report = generate_report(findings_obj, state.patient_metadata)
            state.last_report = report
            await _step("report_generation", "completed")

        messages = await self._build_messages(state)
        full_response = await self._stream_completion(messages, on_token)
        state.conversation_history.append({"role": "assistant", "content": full_response})

    async def _chat_completion(self, messages: list[dict]) -> str:
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
    has_eeg = any("EEG" in m.get("content", "") for m in messages)
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
