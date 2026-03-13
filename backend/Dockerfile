# ── Iris Backend — Dockerfile ───────────────────────────────────────────────
# Build context MUST be the repo root, not ./backend
# docker build -t iris-backend -f backend/Dockerfile .
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

LABEL maintainer="iris-team"
LABEL description="Iris AI Travel Companion Backend"

# Install curl for health check
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (security best practice per PRD §10.6)
RUN useradd -m -u 1000 appuser

WORKDIR /app

# ── Python dependencies (own layer for caching) ───────────────────────────────
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY backend/main.py             ./main.py
COPY backend/agent.py            ./agent.py
COPY backend/gemini_client.py    ./gemini_client.py
COPY backend/maps_client.py      ./maps_client.py
COPY backend/firestore_client.py ./firestore_client.py
COPY backend/models.py           ./models.py
COPY backend/prompts.py          ./prompts.py

# ── Frontend (served as /static/* by FastAPI) ─────────────────────────────────
COPY frontend/ ./frontend/

# ── Switch to non-root ────────────────────────────────────────────────────────
USER appuser

# Cloud Run injects PORT (default 8080)
ENV PORT=8080

# Health check — Cloud Run polls /health
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -sf http://localhost:${PORT}/health || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
