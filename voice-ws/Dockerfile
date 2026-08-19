# voice-ws production image (Pipecat + FastAPI WebSocket)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY voice-ws/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Pipecat/Gemini Live uses NLTK sentence tokenization. Pre-install corpora at
# build time — the runtime user has no home dir and cannot download punkt_tab.
ENV NLTK_DATA=/app/nltk_data
RUN mkdir -p /app/nltk_data \
    && python -c "import nltk; nltk.download('punkt_tab', download_dir='/app/nltk_data')"

COPY shared/ /app/shared
COPY voice-ws/ /app

RUN addgroup --system --gid 1001 voicews \
    && adduser --system --uid 1001 --gid 1001 --no-create-home voicews \
    && chown -R voicews:voicews /app

USER voicews

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

CMD ["bash", "/app/entrypoint.prod.sh"]
