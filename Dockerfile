# syntax=docker/dockerfile:1

# ── Stage 1: Build the React frontend ──────────────────────────────────────
FROM node:22-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# vite.config.js outputs to ../app/static (relative to frontend/) → /app/static
RUN npm run build

# ── Stage 2: Python runtime (FastAPI + yt-dlp + Playwright) ────────────────
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PIP_NO_CACHE_DIR=1     PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# ffmpeg: required by yt-dlp to merge chunked formats (-0/-1 splits)
RUN apt-get update     && apt-get install -y --no-install-recommends ffmpeg     && rm -rf /var/lib/apt/lists/*

# Python deps + Playwright Chromium (with its system libraries)
COPY requirements.txt ./
RUN pip install -r requirements.txt     && playwright install --with-deps chromium     && rm -rf /root/.cache/pip

# Backend app + prebuilt frontend assets
COPY app/ ./app/
COPY --from=frontend-build /app/static ./app/static

# Persisted state: queue DB + downloaded files, and TikTok cookie file
VOLUME ["/tmp/tiktok_queue", "/app/data"]

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
