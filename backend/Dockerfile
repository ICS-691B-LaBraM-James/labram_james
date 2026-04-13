FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    libhdf5-dev \
    libgl1 \
    git \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install torch torchvision torchaudio
RUN pip install braindecode
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
