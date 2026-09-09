FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt .

# 🔑 पहले requirements, फिर ntgcalls को फोर्स अपग्रेड करें ताकि पुराना wheel न रह जाए
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -U ntgcalls

COPY . .

CMD ["python", "main.py"]
