# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# optional utils for health/debug
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy project metadata + source (src layout)
COPY pyproject.toml README.md /app/
COPY src/ /app/src/

# Install runtime deps
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir "gunicorn" "uvicorn[standard]" \
 && pip install --no-cache-dir -e .

ENV PYTHONPATH=/app/src
EXPOSE 8000

# optional healthcheck if /health exists
HEALTHCHECK --interval=30s --timeout=3s CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:8000", "chronic_ai_api.server:app"]
