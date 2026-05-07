FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libhdf5-dev \
    libgl1 \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install edfio
RUN pip install torch torchvision torchaudio
RUN pip install braindecode
COPY . .
EXPOSE 8000
# No --reload: volume-mounted ./backend triggers restarts that drop in-flight WebSockets.
# --ws-max-size: binary EDF upload; uvicorn default 16MiB closes the socket (code 1009) on larger files.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--ws-max-size", "536870912"]
