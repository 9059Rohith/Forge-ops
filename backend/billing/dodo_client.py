from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

import httpx


class DodoError(RuntimeError):
    pass


class DodoClient:
    """Small REST wrapper around Dodo's current checkout/customer/subscription APIs."""

    def __init__(
        self,
        api_key: str | None,
        webhook_secret: str | None,
        base_url: str,
        timeout: float = 15.0,
    ) -> None:
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def _request(self, method: str, path: str, payload: dict[str, Any] | None = None):
        if not self.api_key:
            raise DodoError("DODO_API_KEY is required for Dodo API calls")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
        if response.is_error:
            raise DodoError(f"Dodo API returned HTTP {response.status_code}")
        return response.json()

    async def create_customer(self, email: str, name: str, user_id: str) -> dict[str, Any]:
        return await self._request(
            "POST", "/customers", {"email": email, "name": name, "metadata": {"user_id": user_id}}
        )

    async def create_checkout_session(
        self,
        *,
        user_id: str,
        plan: str,
        product_id: str,
        return_url: str,
        customer_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "product_cart": [{"product_id": product_id, "quantity": 1}],
            "return_url": return_url,
            "metadata": {"user_id": user_id, "plan": plan},
        }
        if customer_id:
            payload["customer"] = {"customer_id": customer_id}
        return await self._request("POST", "/checkouts", payload)

    async def fetch_subscription(self, subscription_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/subscriptions/{subscription_id}")

    def verify_webhook(self, raw_body: bytes, headers: dict[str, str]) -> dict[str, Any]:
        if not self.webhook_secret:
            raise DodoError("DODO_WEBHOOK_SECRET is required for webhook verification")
        webhook_id = headers.get("webhook-id", "")
        timestamp = headers.get("webhook-timestamp", "")
        supplied = headers.get("webhook-signature", "")
        if not webhook_id or not timestamp or not supplied:
            raise DodoError("missing Dodo webhook signature headers")
        try:
            if abs(time.time() - int(timestamp)) > 300:
                raise DodoError("stale Dodo webhook timestamp")
        except ValueError as exc:
            raise DodoError("invalid Dodo webhook timestamp") from exc

        encoded_secret = self.webhook_secret.removeprefix("whsec_")
        try:
            secret = base64.b64decode(encoded_secret, validate=True)
        except (ValueError, base64.binascii.Error):
            secret = encoded_secret.encode()
        message = b".".join((webhook_id.encode(), timestamp.encode(), raw_body))
        expected = base64.b64encode(hmac.new(secret, message, hashlib.sha256).digest()).decode()
        signatures = [part.split(",", 1)[-1] for part in supplied.split()]
        if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
            raise DodoError("invalid Dodo webhook signature")
        try:
            value = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise DodoError("invalid webhook JSON") from exc
        if not isinstance(value, dict):
            raise DodoError("invalid webhook payload")
        return value
