# Lucid API — runtime image that actually runs the FastAPI app with Uvicorn.
# Root-cause fix applied: this image starts the app (no more /bin/sh -lc "set -e" no-op).

FROM python:3.12-slim

# --- Base runtime hygiene
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8081

# OS deps needed for healthchecks & common libs
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl \
    && rm -rf /var/lib/apt/lists/*

# Workdir for the app
WORKDIR /app

# Copy the whole API context (keeps this Dockerfile robust to current repo layout)
# If you later want faster builds, you can switch to copying only requirements first.
COPY . /app

# Install Python deps:
# - Prefer requirements.txt if present
# - Fallback to a minimal, known-good set for this project (FastAPI + Uvicorn + Mongo clients)
RUN python -m pip install --upgrade pip && \
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt ; \
    elif [ -f requirements/dev.txt ]; then \
        pip install -r requirements/dev.txt ; \
    elif [ -f pyproject.toml ]; then \
        pip install "uvicorn[standard]" fastapi "pymongo>=4" "motor>=3" pydantic ; \
    else \
        pip install "uvicorn[standard]" fastapi "pymongo>=4" "motor>=3" pydantic ; \
    fi

# Entrypoint script: honour $PORT and always launch the API
RUN printf '%s\n' \
  '#!/bin/sh' \
  'set -e' \
  'PORT="${PORT:-8081}"' \
  'HOST="${HOST:-0.0.0.0}"' \
  'APP_IMPORT="${APP_IMPORT:-app.main:app}"' \
  'exec python -m uvicorn "$APP_IMPORT" --host "$HOST" --port "$PORT"' \
  > /usr/local/bin/run-api.sh && chmod +x /usr/local/bin/run-api.sh

# Healthcheck hits the app’s /health endpoint
HEALTHCHECK --interval=10s --timeout=3s --retries=10 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/health" || exit 1

EXPOSE 8081
ENTRYPOINT ["/usr/local/bin/run-api.sh"]
