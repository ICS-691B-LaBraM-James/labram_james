import os
import logging

import httpx

from schemas import EEGFindings
from agents.report_generator.prompts import REPORT_SYSTEM_PROMPT, REPORT_USER_TEMPLATE

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
REPORT_MODEL = os.getenv("REPORT_MODEL", "meditron")


def generate_report(findings: EEGFindings, patient_metadata: dict) -> str:
    print(f"[Report Generator] Generating report via {REPORT_MODEL}...")

    user_prompt = REPORT_USER_TEMPLATE.format(
        age=patient_metadata.get("age", "unknown"),
        sex=patient_metadata.get("sex", "unknown"),
        symptoms=patient_metadata.get("symptoms", "not provided"),
        history=patient_metadata.get("history", "not provided"),
        cognitive_state=findings.cognitive_state,
        emotional_state=findings.emotional_state,
        dominant_frequency_shift=findings.dominant_frequency_shift,
        delta=findings.band_power.delta,
        theta=findings.band_power.theta,
        alpha=findings.band_power.alpha,
        beta=findings.band_power.beta,
        gamma=findings.band_power.gamma,
        ad_risk_score=findings.ad_risk_score,
        seizure_risk=findings.seizure_risk,
        confidence=findings.confidence,
        notable_patterns="; ".join(findings.notable_patterns),
    )

    try:
        with httpx.Client(base_url=OLLAMA_BASE_URL, timeout=120.0) as client:
            resp = client.post("/api/chat", json={
                "model": REPORT_MODEL,
                "messages": [
                    {"role": "system", "content": REPORT_SYSTEM_PROMPT.strip()},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
            })
            resp.raise_for_status()
            return resp.json()["message"]["content"]
    except Exception as e:
        logger.error(f"Ollama report generation failed: {e}")
        return _fallback_report(findings, patient_metadata)


def _fallback_report(findings: EEGFindings, patient_metadata: dict) -> str:
    """Static fallback when Ollama/meditron is unreachable."""
    age = patient_metadata.get("age", "unknown")
    sex = patient_metadata.get("sex", "unknown")
    bp = findings.band_power
    return (
        f"EEG Interpretation Report\n"
        f"========================\n"
        f"Patient: {age}y {sex}\n\n"
        f"NOTE: This is a fallback report generated without the medical LLM. "
        f"Ensure Ollama is running with the meditron model for full reports.\n\n"
        f"Summary of Findings:\n"
        f"- Dominant frequency shift: {findings.dominant_frequency_shift}\n"
        f"- Cognitive state: {findings.cognitive_state}\n"
        f"- Emotional state: {findings.emotional_state}\n"
        f"- Band power: delta={bp.delta}, theta={bp.theta}, alpha={bp.alpha}, "
        f"beta={bp.beta}, gamma={bp.gamma}\n"
        f"- AD risk score: {findings.ad_risk_score:.2f}\n"
        f"- Seizure risk: {findings.seizure_risk}\n"
        f"- Confidence: {findings.confidence:.0%}\n\n"
        f"Recommendation: Clinical correlation advised. This report must be "
        f"reviewed by a qualified clinician."
    )
