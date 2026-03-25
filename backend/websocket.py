import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from schemas import PatientMetadata
from orchestrator.orchestrator import Orchestrator
from orchestrator.state import create_initial_state

logger = logging.getLogger(__name__)
router = APIRouter()

orchestrator = Orchestrator()


@router.websocket("/ws/stream")
async def stream(ws: WebSocket):
    await ws.accept()
    state = create_initial_state()

    try:
        first_frame = await ws.receive_text()
        data = json.loads(first_frame)
        message = data.get("message", "")
        raw_metadata = data.get("patient_metadata", {})
        has_eeg = data.get("has_eeg", False)

        metadata = PatientMetadata(**raw_metadata) if isinstance(raw_metadata, dict) else PatientMetadata()
        state.patient_metadata = metadata.model_dump()
        state.has_eeg = has_eeg
        state.conversation_history.append({"role": "user", "content": message})

        eeg_bytes: bytes | None = None
        if has_eeg:
            eeg_bytes = await ws.receive_bytes()

        async def send_token(token: str):
            await ws.send_json({"type": "token", "content": token})

        async def send_step(step: str, status: str):
            await ws.send_json({"type": "step", "step": step, "status": status})

        await orchestrator.stream_response(state, eeg_bytes, send_token, send_step)

        if state.eeg_findings:
            await ws.send_json({"type": "findings", "data": state.eeg_findings})

        if state.last_report:
            await ws.send_json({"type": "report", "data": state.last_report})

        await ws.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.exception("WebSocket error")
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
