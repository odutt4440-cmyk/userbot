FROM python:3.11

# System dependencies for compiling C++ libraries (tgcalls)
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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Core tools upgrade taaki building me error na aaye
RUN pip install --no-cache-dir --upgrade pip setuptools wheel Cython

# Install all requirements
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
