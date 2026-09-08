FROM python:3.11-slim

# Install system dependencies with git
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    python3-dev \
    cmake \
    pkg-config \
    libffi-dev \
    libssl-dev \
    libopus-dev \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    fonts-dejavu-core \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Step to ensure pip is ready and can handle pre-releases
RUN pip install --no-cache-dir --upgrade pip setuptools wheel Cython

COPY requirements.txt .

# 🔥 Change: Allow pre-release versions for tgcalls compatibility
RUN pip install --no-cache-dir --pre -r requirements.txt

COPY . .

CMD ["python", "main.py"]
