from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import httpx


class PayPalError(Exception):
    """A safe, user-facing description of a PayPal Sandbox failure."""


class PayPalClient:
    def __init__(self, *, client_id: str, client_secret: str, base_url: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url.rstrip("/")

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        response = await client.post(
            "/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret),
            headers={"Accept": "application/json", "Accept-Language": "en_US"},
        )
        if response.status_code >= 400:
            raise PayPalError("PayPal Sandbox could not authenticate ARC's server.")
        token = response.json().get("access_token")
        if not isinstance(token, str) or not token:
            raise PayPalError("PayPal Sandbox returned an invalid access token.")
        return token

    async def create_order(
        self,
        *,
        payment_id: UUID,
        product_name: str,
        amount: Decimal,
        currency: str,
        return_url: str,
        cancel_url: str,
    ) -> tuple[str, str]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=20.0) as client:
            token = await self._access_token(client)
            response = await client.post(
                "/v2/checkout/orders",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                    "PayPal-Request-Id": str(payment_id),
                },
                json={
                    "intent": "CAPTURE",
                    "purchase_units": [
                        {
                            "reference_id": str(payment_id),
                            "description": product_name[:127],
                            "amount": {"currency_code": currency, "value": f"{amount:.2f}"},
                        }
                    ],
                    "application_context": {
                        "return_url": return_url,
                        "cancel_url": cancel_url,
                        "user_action": "PAY_NOW",
                    },
                },
            )
        if response.status_code >= 400:
            raise PayPalError("PayPal Sandbox could not create the order. Please try again.")
        data = response.json()
        order_id = data.get("id")
        approval_url = next(
            (
                link.get("href")
                for link in data.get("links", [])
                if link.get("rel") == "approve"
            ),
            None,
        )
        if not isinstance(order_id, str) or not isinstance(approval_url, str):
            raise PayPalError("PayPal Sandbox returned an incomplete checkout order.")
        return order_id, approval_url

    async def capture_order(self, *, payment_id: UUID, paypal_order_id: str) -> tuple[str, str]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=20.0) as client:
            token = await self._access_token(client)
            response = await client.post(
                f"/v2/checkout/orders/{paypal_order_id}/capture",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                    "PayPal-Request-Id": str(payment_id),
                },
                json={},
            )
        if response.status_code >= 400:
            raise PayPalError(
                "PayPal Sandbox could not capture this order. It may have been cancelled."
            )
        data = response.json()
        capture = (
            data.get("purchase_units", [{}])[0]
            .get("payments", {})
            .get("captures", [{}])[0]
        )
        capture_id = capture.get("id")
        capture_status = capture.get("status")
        if not isinstance(capture_id, str) or capture_status != "COMPLETED":
            raise PayPalError("PayPal Sandbox did not confirm a completed capture.")
        return capture_id, capture_status
