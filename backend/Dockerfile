FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEMO_REPO_PATH=/app/demo-repo \
    WORK_ROOT=/tmp/forgeguard-work

RUN apt-get update \
    && apt-get install --no-install-recommends -y git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN python -m pip install --no-cache-dir --upgrade pip==26.2.1 setuptools==83.0.0
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY demo-repo ./demo-repo

RUN useradd --create-home --uid 10001 forgeguard \
    && chown -R forgeguard:forgeguard /app /tmp
USER forgeguard

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
