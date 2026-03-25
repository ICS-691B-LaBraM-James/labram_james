import asyncio
from typing import Callable, Awaitable, Optional

from schemas import ChatResponse, EEGFindings
from orchestrator.state import SessionState
from agents.eeg_cleaner.cleaner import clean_eeg
from agents.labram.encoder import encode_eeg
from agents.labram.head_cognitive import classify_cognitive_state
from agents.labram.head_neurological import detect_neurological_patterns
from agents.labram.findings import assemble_findings
from agents.report_generator.generator import generate_report


class Orchestrator:
    def __init__(self):
        # TODO: initialize model client once hosting is decided
        # Options: Groq, Together AI, Ollama, HuggingFace Inference Endpoint
        self.model_client = None

    async def run(self, state: SessionState, eeg_bytes: Optional[bytes]) -> ChatResponse:
        findings_obj: Optional[EEGFindings] = None
        report: Optional[str] = None

        if eeg_bytes is not None:
            cleaned = clean_eeg(eeg_bytes)
            embeddings = encode_eeg(cleaned)
            cognitive = classify_cognitive_state(embeddings)
            neuro = detect_neurological_patterns(embeddings)
            findings_obj = assemble_findings(cognitive, neuro)
            state.eeg_findings = findings_obj.model_dump()
            report = generate_report(findings_obj, state.patient_metadata)
            state.last_report = report

        response_text = _build_stub_response(state)
        state.conversation_history.append({"role": "assistant", "content": response_text})

        return ChatResponse(
            response=response_text,
            findings=findings_obj,
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

        response_text = _build_stub_response(state)
        state.conversation_history.append({"role": "assistant", "content": response_text})

        for word in response_text.split(" "):
            await on_token(word + " ")
            await asyncio.sleep(0.05)


def _build_stub_response(state: SessionState) -> str:
    # TODO: replace with real LLM call once model is decided
    if state.eeg_findings:
        findings = state.eeg_findings
        return (
            f"Based on the EEG analysis, I'm observing {findings.get('dominant_frequency_shift', 'some frequency changes')}. "
            f"The cognitive state appears to be {findings.get('cognitive_state', 'unclear')}. "
            f"The Alzheimer's risk score is {findings.get('ad_risk_score', 0):.2f}, "
            f"which warrants further clinical evaluation. "
            f"Notable patterns include: {', '.join(findings.get('notable_patterns', []))}. "
            f"Please refer to the clinical report for the full interpretation."
        )
    return (
        "I'm ready to analyze EEG data and answer questions about neurological findings. "
        "You can upload an EEG file along with patient metadata for a full analysis, "
        "or ask me general questions about EEG interpretation and neurology."
    )
