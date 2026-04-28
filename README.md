# EEG Interpreter

An agentic EEG interpretation system that processes raw EEG recordings and produces clinical-grade neurological reports through a multi-stage AI pipeline.

## Pipeline Stages

| Stage | Status | Description |
|---|---|---|
| **EEG Cleaner** | Stub | Preprocesses raw EEG files — bandpass/notch filtering, bad channel interpolation, ICA artifact removal, and epoch extraction using MNE-Python and AutoReject. |
| **LaBraM Encoder + Heads** | Stub | Encodes cleaned EEG epochs into embeddings via the LaBraM pretrained backbone, then routes them through two fine-tuned classification heads: one for cognitive/emotional state and one for neurological pattern detection (AD risk, seizure risk, band power). |
| **Report Generator** | Live (llama3.1) | Takes structured EEG findings and patient metadata and generates a formal clinical interpretation report using llama3.1 via Ollama. |
| **Orchestrator** | Live (llama3.1) | Coordinates the full pipeline, manages conversation state, and streams responses to the frontend via WebSocket. Powered by llama3.1 via Ollama. |

## Tech Stack

- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Backend:** Python + FastAPI + WebSockets
- **LLM Inference:** Ollama (local) — llama3.1
- **Containers:** Docker + Docker Compose

## Prerequisites

1. **Ollama** must be installed and running on your machine ([ollama.com](https://ollama.com))
2. Pull the required models:

```bash
ollama pull llama3.1
```

3. Verify Ollama is running on port 11434:

```bash
curl http://localhost:11434/api/tags
```

## Getting Started

```bash
# Copy env template and review settings
cp .env.example .env

# Build and start
docker compose up --build
```

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Ollama:** http://localhost:11434

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama server URL (use `http://localhost:11434` when not using Docker) |
| `ORCHESTRATOR_MODEL` | `llama3.1` | Model for conversational orchestration |
| `REPORT_MODEL` | `llama3.1` | Model for clinical report generation |
| `HUGGINGFACE_TOKEN` | — | For loading LaBraM weights (future) |

## Agent Integration Checklist

Remaining stubs to replace when each real model is ready:

| Agent | File to edit | What to replace |
|---|---|---|
| EEG Cleaner | `backend/agents/eeg_cleaner/cleaner.py` | Body of `clean_eeg` |
| LaBraM Backbone | `backend/agents/labram/encoder.py` | Body of `encode_eeg` |
| Cognitive Head | `backend/agents/labram/head_cognitive.py` | Body of `classify_cognitive_state` |
| Neurological Head | `backend/agents/labram/head_neurological.py` | Body of `detect_neurological_patterns` |

No other files need to change when swapping in real models.
