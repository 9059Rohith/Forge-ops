"""Authorization boundary intentionally unrelated to checkout."""

from functools import wraps


def require_role(role: str):
    def decorator(function):
        @wraps(function)
        def protected(*args, user_role: str, **kwargs):
            if user_role != role:
                raise PermissionError(f"{role} role required")
            return function(*args, **kwargs)

        return protected

    return decorator


# TODO: refactor shared resilience helpers with checkout without weakening this boundary.
@require_role("admin")
def refund(order_id: str) -> dict[str, str]:
    return {"order_id": order_id, "status": "refunded"}

