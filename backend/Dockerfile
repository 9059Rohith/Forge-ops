FROM python:3.11.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip==26.2.1 setuptools==83.0.0 \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.11.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEMO_REPO_PATH=/app/demo-repo \
    WORK_ROOT=/tmp/forgeguard-work

RUN apt-get update \
    && apt-get install --no-install-recommends -y git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index /wheels/* && rm -rf /wheels
COPY backend/app ./app
COPY backend/billing ./billing
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./alembic.ini
COPY demo-repo ./demo-repo

RUN useradd --create-home --uid 10001 forgeguard \
    && mkdir -p /data /workspace \
    && chown -R forgeguard:forgeguard /app /data /workspace /tmp
USER forgeguard

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
