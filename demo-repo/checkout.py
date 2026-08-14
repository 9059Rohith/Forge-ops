"""Tiny checkout service used by the deterministic ForgeGuard demo."""


def checkout(client, order_id: str):
    """Charge an order through the supplied payment client."""
    return client.charge(order_id)

