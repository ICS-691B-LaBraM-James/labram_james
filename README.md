# EEG Interpreter

An agentic EEG interpretation system that processes raw EEG recordings and produces clinical-grade neurological reports through a multi-stage AI pipeline.

> **Status:** All agents are currently stubs returning mock data. No API keys or model weights are needed to run the full UI pipeline end to end.

## Pipeline Stages

| Stage | Description |
|---|---|
| **EEG Cleaner** | Preprocesses raw EEG files — bandpass/notch filtering, bad channel interpolation, ICA artifact removal, and epoch extraction using MNE-Python and AutoReject. |
| **LaBraM Encoder + Heads** | Encodes cleaned EEG epochs into embeddings via the LaBraM pretrained backbone, then routes them through two fine-tuned classification heads: one for cognitive/emotional state and one for neurological pattern detection (AD risk, seizure risk, band power). |
| **Report Generator** | Takes structured EEG findings and patient metadata and generates a formal clinical interpretation report using a medical LLM (Med-LLaMA, provider TBD). |
| **Orchestrator** | Coordinates the full pipeline, manages conversation state, and streams responses to the frontend via WebSocket. Powered by a general-purpose LLM (provider TBD). |

## Tech Stack

- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Backend:** Python + FastAPI + WebSockets
- **Containers:** Docker + Docker Compose

## Getting Started

```bash
# Copy env template (fill in keys when models are ready)
cp .env.example .env

# Build and start
docker compose up --build
```

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Agent Integration Checklist

When each real model is ready, replace the stub in the corresponding file:

| Agent | File to edit | What to replace |
|---|---|---|
| Orchestrator LLM | `backend/orchestrator/orchestrator.py` | `self.model_client = None` and `_build_stub_response` |
| EEG Cleaner | `backend/agents/eeg_cleaner/cleaner.py` | Body of `clean_eeg` |
| LaBraM Backbone | `backend/agents/labram/encoder.py` | Body of `encode_eeg` |
| Cognitive Head | `backend/agents/labram/head_cognitive.py` | Body of `classify_cognitive_state` |
| Neurological Head | `backend/agents/labram/head_neurological.py` | Body of `detect_neurological_patterns` |
| Report Generator | `backend/agents/report_generator/generator.py` | Body of `generate_report` |

No other files need to change when swapping in real models.
