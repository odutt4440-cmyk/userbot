FROM python:3.11

# System dependencies for building and streaming
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

# Core build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel Cython

COPY requirements.txt .

# 🔥 Install requirements (Allowing git links)
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
