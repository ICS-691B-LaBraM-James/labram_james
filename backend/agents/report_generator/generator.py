import os
import json
import logging
import httpx
from schemas import EEGFindings
from agents.report_generator.prompts import REPORT_SYSTEM_PROMPT, REPORT_USER_TEMPLATE

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
REPORT_MODEL = os.getenv("REPORT_MODEL", "llama3.1")


def clean(value, fallback="None"):
    """Preserve real values, avoid wiping valid inputs."""
    if value is None:
        return fallback
    if isinstance(value, str) and value.strip() == "":
        return fallback
    return value


def normalize_list_field(value: str):
    """Convert comma-separated user input into clean list string."""
    if not value or value.strip() == "":
        return "None"
    return ", ".join([v.strip() for v in value.split(",") if v.strip()])


def generate_report(
    findings: EEGFindings,
    patient_metadata: dict,
    features: dict | None = None,
    user_notes: str = "",
) -> str:
    print(f"[Report Generator] Generating report via {REPORT_MODEL}...")

    features = features or {}
    ad_label = "AD" if findings.cognitive_state == "impaired" else "HC"

    age = clean(patient_metadata.get("age"), "Not provided")
    sex = clean(patient_metadata.get("sex"), "Not provided")
    mmse = clean(patient_metadata.get("mmse"), "Not assessed")
    medications = normalize_list_field(patient_metadata.get("medications"))
    symptoms = clean(patient_metadata.get("symptoms"), "None reported")

    try:
        raw_history = patient_metadata.get("history", "{}")
        h_dict = json.loads(raw_history) if isinstance(raw_history, str) else raw_history

        label_map = {
            "memoryLoss": "Memory Loss",
            "executiveDysfunction": "Executive Dysfunction",
            "behavioralChanges": "Behavioral Changes",
            "languageDifficulty": "Language Difficulty",
            "familyHistory": "Family History",
            "hypertension": "Hypertension"
        }

        active_history = [
            label_map[k]
            for k, v in h_dict.items()
            if v is True and k in label_map
        ]

        history_str = ", ".join(active_history) if active_history else "None"

    except Exception as e:
        logger.warning(f"History parsing failed: {e}")
        history_str = "None"

    bp = findings.band_power

    try:
        user_prompt = REPORT_USER_TEMPLATE.format(
            age=age,
            sex=sex,
            mmse=mmse,
            medications=medications,
            symptoms=symptoms,
            history=history_str,
            user_notes=user_notes.strip() or "No clinician notes provided.",
            ad_probability=findings.ad_risk_score,
            ad_label=ad_label,
            stability_index=features.get("stability_index", 0.0),
            delta=getattr(bp, 'delta', 0.0),
            theta=getattr(bp, 'theta', 0.0),
            alpha=getattr(bp, 'alpha', 0.0),
            beta=getattr(bp, 'beta', 0.0),
            gamma=getattr(bp, 'gamma', 0.0),
            theta_alpha_ratio=features.get("theta_alpha_ratio", 0.0),
            notes=features.get("notes") or "; ".join(findings.notable_patterns)
        )
    except KeyError as e:
        logger.error(f"Mapping error: Missing template key {e}")
        return f"Internal Error: Prompt template is missing key {e}"

    try:
        with httpx.Client(base_url=OLLAMA_BASE_URL, timeout=120.0) as client:
            resp = client.post(
                "/api/chat",
                json={
                    "model": REPORT_MODEL,
                    "messages": [
                        {"role": "system", "content": REPORT_SYSTEM_PROMPT.strip()},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                },
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return f"Error connecting to LLM: {e}"
