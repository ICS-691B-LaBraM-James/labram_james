import json

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from schemas import PatientMetadata, ChatResponse
from websocket import router as ws_router
from orchestrator.orchestrator import Orchestrator
from orchestrator.state import create_initial_state

app = FastAPI(title="EEG Interpreter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router)

orchestrator = Orchestrator()


@app.on_event("startup")
async def startup():
    print("EEG Interpreter API ready")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    message: str = Form(...),
    patient_metadata: str = Form("{}"),
    eeg_file: UploadFile | None = File(None),
):
    metadata = PatientMetadata(**json.loads(patient_metadata))
    eeg_bytes: bytes | None = None
    if eeg_file is not None:
        eeg_bytes = await eeg_file.read()

    state = create_initial_state()
    state.patient_metadata = metadata.model_dump()
    state.has_eeg = eeg_bytes is not None
    state.conversation_history.append({"role": "user", "content": message})

    result = await orchestrator.run(state, eeg_bytes)
    return result
