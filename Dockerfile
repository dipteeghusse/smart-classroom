# ── Backend — FastAPI + all agents ───────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# System deps needed by reportlab, qrcode, chromadb, geopy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cached unless pyproject.toml changes)
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Copy application source
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Cloud Run sets PORT env var — default 8080
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 2"]
