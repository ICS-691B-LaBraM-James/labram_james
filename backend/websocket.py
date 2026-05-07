import json
import logging
import os
import tempfile

import mne
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile

from schemas import PatientMetadata
from orchestrator.orchestrator import Orchestrator
from orchestrator.state import create_initial_state

logger = logging.getLogger(__name__)
router = APIRouter()

orchestrator = Orchestrator()


@router.post("/upload-eeg")
async def upload_eeg(file: UploadFile):
    suffix = os.path.splitext(file.filename or "")[1] or ".edf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    return {"path": tmp_path}


@router.websocket("/ws/stream")
async def stream(ws: WebSocket):
    await ws.accept()
    state = create_initial_state()

    async def safe_send(payload: dict):
        try:
            await ws.send_json(payload)
        except Exception:
            # socket already closed — ignore
            pass

    try:
        first_frame = await ws.receive_text()
        data = json.loads(first_frame)

        message = data.get("message", "")
        raw_metadata = data.get("patient_metadata", {})
        has_eeg = data.get("has_eeg", False)
        filename = data.get("filename", "")

        metadata = (
            PatientMetadata(**raw_metadata)
            if isinstance(raw_metadata, dict)
            else PatientMetadata()
        )

        state.patient_metadata = metadata.model_dump()
        state.has_eeg = has_eeg
        state.conversation_history.append(
            {"role": "user", "content": message}
        )

        eeg_bytes: bytes | None = None

        # Frontend sends raw EEG bytes as second binary frame
        if has_eeg:
            uploaded_bytes = await ws.receive_bytes()

            ext = os.path.splitext(filename)[1].lower()

            # EDF → use directly
            if ext == ".edf":
                eeg_bytes = uploaded_bytes

            # EEGLAB SET → convert to EDF
            elif ext == ".set":
                with tempfile.TemporaryDirectory() as tmpdir:
                    set_path = os.path.join(tmpdir, filename)

                    with open(set_path, "wb") as f:
                        f.write(uploaded_bytes)

                    raw = mne.io.read_raw_eeglab(
                        set_path,
                        preload=True
                    )

                    edf_filename = (
                        f"{os.path.splitext(filename)[0]}.edf"
                    )

                    edf_path = os.path.join(tmpdir, edf_filename)

                    raw.export(
                        edf_path,
                        fmt="edf",
                        overwrite=True
                    )

                    with open(edf_path, "rb") as f:
                        eeg_bytes = f.read()

            else:
                raise ValueError(
                    "Unsupported EEG format. Please upload .edf or .set files."
                )

        async def send_token(token: str):
            await safe_send({
                "type": "token",
                "content": token
            })

        async def send_step(step: str, status: str):
            await safe_send({
                "type": "step",
                "step": step,
                "status": status
            })

        await orchestrator.stream_response(
            state,
            eeg_bytes,
            send_token,
            send_step
        )

        # FINAL RESULTS
        if state.eeg_findings:
            await safe_send({
                "type": "findings",
                "data": state.eeg_findings
            })

        if state.last_report:
            await safe_send({
                "type": "report",
                "data": state.last_report
            })

        await safe_send({"type": "done"})

    except WebSocketDisconnect:
        logger.info("Client disconnected")

    except Exception as e:
        logger.exception("WebSocket error")

        try:
            await ws.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass
