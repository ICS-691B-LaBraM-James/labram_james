from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SessionState:
    conversation_history: list = field(default_factory=list)
    patient_metadata: dict = field(default_factory=dict)
    eeg_findings: Optional[dict] = None
    last_report: Optional[str] = None
    has_eeg: bool = False


def create_initial_state() -> SessionState:
    return SessionState()
