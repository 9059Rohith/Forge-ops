from fastapi import FastAPI

from auth import refund

app = FastAPI(title="ForgeGuard demo checkout")


@app.post("/admin/refund/{order_id}")
def admin_refund(order_id: str, role: str):
    return refund(order_id, user_role=role)

