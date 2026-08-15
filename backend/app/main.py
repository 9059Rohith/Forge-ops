from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.observability import configure_logging, request_context_middleware
from app.routers import health, jobs, repairs, tasks, webhooks
from billing import router as billing_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings().validate_runtime()
    await init_db()
    yield


settings = get_settings()
configure_logging(settings.log_level)
app = FastAPI(
    title="ForgeGuard API",
    version="1.0.0",
    description="Evidence-driven governance for autonomous code changes.",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Request-ID", "webhook-id", "webhook-signature", "webhook-timestamp", "X-Hub-Signature-256", "X-GitHub-Event"],
)
app.middleware("http")(request_context_middleware)
app.include_router(health.router, prefix="/api")
app.include_router(health.root_router)
app.include_router(tasks.router, prefix="/api/tasks")
app.include_router(repairs.router, prefix="/api/repairs")
app.include_router(billing_router.router, prefix="/api/billing")
app.include_router(jobs.router, prefix="/api/jobs")
app.include_router(webhooks.router, prefix="/api/webhooks")
