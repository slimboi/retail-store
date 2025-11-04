import os, uuid, logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
import httpx

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("orders")

CARTS_BASE = os.getenv("CARTS_BASE", "http://carts:8002")

class CheckoutRequest(BaseModel):
    userId: str
    full_name: str
    email: str

    @field_validator('userId', mode='before')
    @classmethod
    def convert_user_id(cls, v):
        return str(v)

app = FastAPI(title="CloudPros Orders")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/checkout")
async def checkout(payload: CheckoutRequest):
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{CARTS_BASE}/cart", params={"userId": payload.userId})
        if r.status_code != 200:
            raise HTTPException(500, "Cart fetch failed")
        cart = r.json()
    if cart.get("count", 0) == 0:
        raise HTTPException(400, "Cart is empty")
    order_id = str(uuid.uuid4())
    # In a real system, persist order. Here we just clear the cart and return summary.
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(f"{CARTS_BASE}/cart/clear", params={"userId": payload.userId})
    return {"order_id": order_id, "total": cart["total"], "items": cart["items"]}
