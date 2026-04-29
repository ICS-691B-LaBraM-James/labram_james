import asyncio
import json
import os
import logging
from pathlib import Path
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
from agents.lead.eeg_features import compute_eeg_features

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
ORCHESTRATOR_MODEL = os.getenv("ORCHESTRATOR_MODEL", "llama3.1")

# /app/orchestrator/orchestrator.py -> parents[1] is /app (project root in container).
_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _resolve_checkpoint_root() -> str:
    default_root = _PROJECT_ROOT / "third_party" / "LEAD" / "checkpoints" / "LEADv2" / "finetune" / "LEADv2" / "P-Base-F-Merged400-AD-vs-HC"
    configured = os.getenv("CHECKPOINT_ROOT")

    if not configured:
        return str(default_root)

    configured_path = Path(configured)
    if configured_path.exists():
        return str(configured_path)

    # Backward compatibility: older setups used /LEAD/... or /app/LEAD/... inside Docker.
    if configured.startswith("/LEAD/"):
        docker_path = Path("/app") / configured_path.relative_to("/")
        if docker_path.exists():
            logger.warning(
                "CHECKPOINT_ROOT '%s' not found; using '%s' instead",
                configured,
                str(docker_path),
            )
            return str(docker_path)
    if configured.startswith("/app/LEAD/"):
        docker_path = Path("/app/third_party/LEAD") / configured_path.relative_to("/app/LEAD")
        if docker_path.exists():
            logger.warning(
                "CHECKPOINT_ROOT '%s' not found; using '%s' instead",
                configured,
                str(docker_path),
            )
            return str(docker_path)

    logger.warning(
        "CHECKPOINT_ROOT '%s' not found; falling back to default '%s'",
        configured,
        str(default_root),
    )
    return str(default_root)


LEAD_CHECKPOINT_ROOT = _resolve_checkpoint_root()
LEAD_SEED_FOLDERS = os.getenv(
    "SEED_FOLDERS",
    "nh8_el12_dm128_df256_seed41,nh8_el12_dm128_df256_seed42,nh8_el12_dm128_df256_seed43,nh8_el12_dm128_df256_seed44",
)
LEAD_DEVICE = os.getenv("DEVICE", "cpu")


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
            checkpoint_root=LEAD_CHECKPOINT_ROOT,
            seed_folders=LEAD_SEED_FOLDERS,
            device=LEAD_DEVICE,
        )

    def leadv2_to_findings(self, result: dict, features: dict) -> EEGFindings:
        probs = result["subject_prob"]
        label = int(result["subject_label"][0])

        cognitive_state = "impaired" if label == 1 else "normal"

        patterns = [
            f"HC probability: {probs[0]:.3f}",
            f"AD probability: {probs[1]:.3f}",
        ]

        rel = features["relative_powers"]
        return EEGFindings(
            cognitive_state=cognitive_state,
            emotional_state="not assessed",
            dominant_frequency_shift=features["dominant_frequency_shift"],
            band_power=BandPower(
                delta=float(rel["delta"]),
                theta=float(rel["theta"]),
                alpha=float(rel["alpha"]),
                beta=float(rel["beta"]),
                gamma=float(rel["gamma"]),
            ),
            ad_risk_score=float(probs[1]),
            seizure_risk="not assessed",
            confidence=float(probs[label]),
            notable_patterns=patterns,
        )

    async def run(self, state: SessionState, eeg_file_path: Optional[str]) -> ChatResponse:
        report: Optional[str] = None

        if eeg_file_path is not None:
            result = run_inference_on_edf(
                edf_path=eeg_file_path,
                checkpoint_root=LEAD_CHECKPOINT_ROOT,
                seed_folders=LEAD_SEED_FOLDERS,
                device=LEAD_DEVICE,
            )
            features = compute_eeg_features(eeg_file_path)

            findings_obj = self.leadv2_to_findings(result, features)

            state.eeg_findings = findings_obj.model_dump()
            state.raw_pipeline_output = _summarize_lead_result(result)

            logger.error(json.dumps(state.eeg_findings, indent=2))
            report = generate_report(
                findings_obj,
                state.patient_metadata,
                features,
                _latest_user_message(state),
            )
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

            try:
                result, features = await asyncio.gather(
                    asyncio.to_thread(
                        run_inference_on_edf,
                        filepath,
                        LEAD_CHECKPOINT_ROOT,
                        LEAD_SEED_FOLDERS,
                        LEAD_DEVICE,
                    ),
                    asyncio.to_thread(compute_eeg_features, filepath),
                )
            finally:
                try:
                    await asyncio.to_thread(os.unlink, filepath)
                except OSError:
                    pass

            findings_obj = self.leadv2_to_findings(result, features)

            state.eeg_findings = findings_obj.model_dump()
            state.raw_pipeline_output = _summarize_lead_result(result)

            logger.error(json.dumps(state.eeg_findings, indent=2))

            await _step("eeg_processing", "completed")

            await _step("report_generation", "in_progress")
            report = await asyncio.to_thread(
                generate_report,
                findings_obj,
                state.patient_metadata,
                features,
                _latest_user_message(state),
            )
            state.last_report = report
            await _step("report_generation", "completed")
            return

        # No EEG attached: plain chat reply via streamed tokens.
        messages = await self._build_messages(state)
        try:
            full_response = await asyncio.wait_for(
                self._stream_completion(messages, on_token),
                timeout=45.0,
            )
        except asyncio.TimeoutError:
            logger.error("Ollama streaming timed out after 45s")
            full_response = _fallback_response(messages)
            for word in full_response.split(" "):
                await on_token(word + " ")
                await asyncio.sleep(0.05)
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


def _latest_user_message(state: SessionState) -> str:
    for entry in reversed(state.conversation_history):
        if entry.get("role") == "user":
            return entry.get("content", "") or ""
    return ""


def _summarize_lead_result(result: dict) -> dict:
    """JSON-safe summary of LEAD ensemble output for use as LLM context."""
    probs = result["subject_prob"]
    seg_pred = result["segment_pred_labels"]
    n = int(len(seg_pred))
    return {
        "n_segments": n,
        "subject_hc_probability": float(probs[0]),
        "subject_ad_probability": float(probs[1]),
        "segment_ad_ratio": float((seg_pred == 1).sum()) / n if n else 0.0,
        "subject_label": "AD" if int(result["subject_label"][0]) == 1 else "HC",
    }


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
