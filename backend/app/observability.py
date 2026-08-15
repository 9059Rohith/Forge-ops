from __future__ import annotations

import json
import logging
import re
import time
import uuid

from fastapi import Request, Response

JOB_PATH = re.compile(r"/api/(?:tasks|jobs|repairs)/([^/]+)")


def configure_logging(level: str) -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format="%(message)s")


async def request_context_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    match = JOB_PATH.search(request.url.path)
    logging.getLogger("forgeguard.access").info(
        json.dumps(
            {
                "event": "http_request",
                "request_id": request_id,
                "job_id": match.group(1) if match else None,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": elapsed_ms,
            },
            separators=(",", ":"),
        )
    )
    response.headers["X-Request-ID"] = request_id
    return response
