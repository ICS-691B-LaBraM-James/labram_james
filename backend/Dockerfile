FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libhdf5-dev \
    libgl1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# CHANGED: Look in backend/ folder for requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install torch torchvision torchaudio braindecode

# Copy the backend source code
# CHANGED: Copy from backend/ into the current WORKDIR (/app)
COPY backend/ .

# We do NOT copy LEAD here; it is handled by the volume mount 
# in docker-compose.yml for development.

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
