# syntax=docker/dockerfile:1.6
#
# FieldPack AI — backend image
#
# Serves the FastAPI app on port 8000. The React frontend ships as a separate
# container (see docker-compose.yml / frontend/Dockerfile). The Knowledge Pack
# is baked into the image at /app/packs.

FROM python:3.11.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl \
      ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Non-root runtime user — minimises blast radius of any path-traversal or
# SSRF in upload / RAG code paths. UID matches the uploads volume owner.
RUN useradd -m -u 1001 appuser

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt

# Pre-download the sentence-transformers embedding model so the first chat
# request doesn't hang pulling ~90 MB from huggingface.co. Critical for judges
# running offline or behind firewalls. Cache to /opt/hf-cache so appuser can
# read it regardless of which HOME points where.
ENV HF_HOME=/opt/hf-cache \
    SENTENCE_TRANSFORMERS_HOME=/opt/hf-cache/sentence-transformers
RUN mkdir -p /opt/hf-cache && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" && \
    chown -R appuser:appuser /opt/hf-cache

COPY --chown=appuser:appuser backend/ /app/backend/
COPY --chown=appuser:appuser packs/ /app/packs/
COPY --chown=appuser:appuser NOTICE /app/NOTICE
COPY --chown=appuser:appuser LICENSE /app/LICENSE

# Pre-create writable runtime dirs owned by appuser. Each is a @property
# in config.py that calls .mkdir() eagerly on access, so they must exist
# and be writable before the app imports. If any already exists as a
# volume with root ownership from a previous run, run `docker volume rm`.
#   /app/uploads — user-uploaded plant photos (docker-compose volume)
#   /app/logs    — pipeline logs written by app.logger at import time
#   /app/data    — settings.data_path
# /app/packs is populated by COPY above and is not written at runtime for
# the DEMO flow; but mkdir(exist_ok=True) runs on any access, so it needs
# to be writable by appuser too.
RUN mkdir -p /app/uploads /app/logs /app/data && \
    chown -R appuser:appuser /app/uploads /app/logs /app/data /app/packs

USER appuser

WORKDIR /app/backend

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=5 \
  CMD curl -fsS http://localhost:8000/health || exit 1

ENV PYTHONPATH=/app/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
