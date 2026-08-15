from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from billing.dodo_client import DodoClient, DodoError
from billing.models import PLAN_CREDITS, RepairCredit, Subscription, User
from billing.service import ensure_demo_user, process_subscription_event

router = APIRouter(tags=["billing"])
_webhook_requests: dict[str, deque[float]] = defaultdict(deque)


class CheckoutRequest(BaseModel):
    user_id: str
    plan: str


def _client() -> DodoClient:
    settings = get_settings()
    return DodoClient(settings.dodo_api_key, settings.dodo_webhook_secret, settings.dodo_api_url)


@router.post("/checkout")
async def checkout(payload: CheckoutRequest, session: AsyncSession = Depends(get_db)):
    settings = get_settings()
    plan = payload.plan.lower()
    if plan not in PLAN_CREDITS or plan == "free":
        raise HTTPException(status_code=422, detail="Choose developer, pro, or team")
    user = (
        await session.scalar(select(User).where(User.github_username == "forgeguard-demo"))
        if payload.user_id == "demo"
        else await session.get(User, payload.user_id)
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    product_id = settings.product_id_for_plan(plan)
    if not product_id:
        raise HTTPException(status_code=503, detail=f"Dodo product for {plan} is not configured")
    try:
        result = await _client().create_checkout_session(
            user_id=user.id,
            plan=plan,
            product_id=product_id,
            customer_id=user.dodo_customer_id,
            return_url=f"{settings.frontend_url.rstrip('/')}/?billing=complete",
        )
    except DodoError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"checkout_url": result.get("checkout_url")}


@router.get("/status/{user_id}")
async def billing_status(user_id: str, session: AsyncSession = Depends(get_db)):
    user = (
        await ensure_demo_user(session)
        if user_id == "demo"
        else await session.get(User, user_id)
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    subscription = await session.scalar(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.current_period_end.desc())
    )
    credit = await session.scalar(
        select(RepairCredit)
        .where(RepairCredit.user_id == user.id)
        .order_by(RepairCredit.period_end.desc())
    )
    return {
        "user_id": user.id,
        "plan": subscription.plan if subscription else "free",
        "subscription_status": subscription.status if subscription else "active",
        "credits_remaining": credit.credits_remaining if credit else 0,
        "credits_used": credit.credits_used if credit else 0,
        "credits_total": (credit.credits_remaining + credit.credits_used) if credit else PLAN_CREDITS["free"],
        "period_end": credit.period_end.isoformat() if credit else None,
    }


@router.post("/webhook")
async def webhook(request: Request, session: AsyncSession = Depends(get_db)):
    source = request.client.host if request.client else "unknown"
    now = time.monotonic()
    recent = _webhook_requests[source]
    while recent and recent[0] < now - 60:
        recent.popleft()
    if len(recent) >= 60:
        raise HTTPException(status_code=429, detail="Webhook rate limit exceeded")
    recent.append(now)
    raw = await request.body()
    if len(raw) > 1_000_000:
        raise HTTPException(status_code=413, detail="Webhook payload too large")
    headers = {key.lower(): value for key, value in request.headers.items()}
    try:
        event = _client().verify_webhook(raw, headers)
    except DodoError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    await process_subscription_event(session, event)
    return {"received": True}
