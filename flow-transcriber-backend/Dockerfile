FROM python:3.11-slim

# ffmpeg para extracción de audio, curl para healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# openai-whisper requiere setuptools<70 (pkg_resources se rompe en versiones posteriores)
RUN pip install --no-cache-dir --upgrade pip wheel "setuptools<70"

# Instalar openai-whisper por separado antes del resto para controlar el entorno de build
RUN pip install --no-cache-dir --no-build-isolation openai-whisper==20240930

# Resto de dependencias
COPY requirements.txt .
RUN grep -v "openai-whisper" requirements.txt | pip install --no-cache-dir -r /dev/stdin

# Código fuente
COPY app/ app/

RUN mkdir -p out

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
