from typing import Optional
from pydantic import BaseModel


class PatientMetadata(BaseModel):
    age: str = ""
    sex: str = ""
    mmse: str = ""
    medications: str = ""
    symptoms: str = ""
    history: str = ""


class BandPower(BaseModel):
    """Relative band power (fraction of total spectral power, 0-1)."""
    delta: float
    theta: float
    alpha: float
    beta: float
    gamma: float


class EEGFindings(BaseModel):
    cognitive_state: str
    emotional_state: str
    dominant_frequency_shift: str
    band_power: BandPower
    ad_risk_score: float
    seizure_risk: str
    confidence: float
    notable_patterns: list[str] = []


class ChatRequest(BaseModel):
    message: str
    patient_metadata: PatientMetadata
    has_eeg: bool = False


class ChatResponse(BaseModel):
    response: str
    findings: Optional[EEGFindings] = None
    report: Optional[str] = None
