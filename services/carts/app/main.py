import os, json, logging
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import redis
import httpx

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("carts")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
PRODUCTS_BASE = os.getenv("PRODUCTS_BASE", "http://products:8001")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

app = FastAPI(title="CloudPros Carts")

class CartItem(BaseModel):
    product_id: int
    qty: int = 1
    price: float
    title: str
    image: str | None = None

def cart_key(user_id: str) -> str:
    return f"cart:{user_id}"

def get_cart(user_id: str) -> Dict[str, Any]:
    data = r.hgetall(cart_key(user_id))
    items: List[CartItem] = []
    for k, v in data.items():
        try:
            items.append(CartItem.model_validate_json(v))
        except Exception:
            log.warning("Bad cart item for %s: %s", user_id, v)
    total = sum(i.price * i.qty for i in items)
    count = sum(i.qty for i in items)
    return {"items": [i.model_dump() for i in items], "total": round(total, 2), "count": count}

async def fetch_product(pid: int) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{PRODUCTS_BASE}/products/{pid}")
        if resp.status_code != 200:
            raise HTTPException(404, "Product not found")
        return resp.json()

@app.get("/health")
def health():
    try:
        r.ping()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/cart")
def read_cart(userId: str = Query(...)):
    return get_cart(userId)

@app.post("/cart/add")
async def add_to_cart(userId: str, product_id: int, qty: int = 1):
    prod = await fetch_product(product_id)
    item = CartItem(product_id=product_id, qty=max(1, qty),
                    price=float(prod["price"]), title=prod["title"], image=prod.get("image"))
    r.hset(cart_key(userId), str(product_id), item.model_dump_json())
    return get_cart(userId)

@app.post("/cart/remove")
def remove_from_cart(userId: str, product_id: int):
    r.hdel(cart_key(userId), str(product_id))
    return get_cart(userId)

@app.post("/cart/clear")
def clear_cart(userId: str):
    r.delete(cart_key(userId))
    return {"ok": True}

@app.post("/cart/merge")
def merge_cart(fromUserId: str, toUserId: str):
    src = r.hgetall(cart_key(fromUserId))
    if src:
        r.hset(cart_key(toUserId), mapping=src)
        r.delete(cart_key(fromUserId))
    return get_cart(toUserId)
