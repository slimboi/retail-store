import os, json, asyncio, logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, Text, create_engine, text as sql_text
from sqlalchemy.orm import declarative_base, sessionmaker
import httpx

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("products")

DB_PATH = os.getenv("PRODUCTS_DB_PATH", "/data/products.db")
SEED_FROM_FAKESTORE = os.getenv("SEED_FROM_FAKESTORE", "1") == "1"

Base = declarative_base()
class ProductORM(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(128))
    price = Column(Float)
    image = Column(String(512))

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class Product(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    price: float
    image: Optional[str] = None

    class Config:
        from_attributes = True

app = FastAPI(title="CloudPros Products")

def init_db():
    # Robust table creation (avoids race on multi-start)
    with engine.begin() as conn:
        conn.execute(sql_text(
            "CREATE TABLE IF NOT EXISTS products ("
            "id INTEGER PRIMARY KEY, "
            "title VARCHAR(255) NOT NULL, "
            "description TEXT, "
            "category VARCHAR(128), "
            "price FLOAT, "
            "image VARCHAR(512))"
        ))
    log.info("DB initialized at %s", DB_PATH)

async def seed_from_fakestore_if_empty():
    if not SEED_FROM_FAKESTORE:
        return
    with SessionLocal() as s:
        count = s.query(ProductORM).count()
        if count > 0:
            log.info("Products table already has %s rows. Skipping seed.", count)
            return

    log.info("Seeding products DB from FakeStore API...")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get("https://fakestoreapi.com/products")
            r.raise_for_status()
            items = r.json()
    except Exception as e:
        log.exception("Failed to fetch from FakeStore: %s", e)
        return

    mapped = []
    for it in items:
        mapped.append(ProductORM(
            id=int(it.get("id")),
            title=it.get("title")[:255],
            description=it.get("description"),
            category=it.get("category"),
            price=float(it.get("price")),
            image=it.get("image"),
        ))
    with SessionLocal() as s:
        s.add_all(mapped)
        s.commit()
    log.info("Seeded %d products from FakeStore", len(mapped))

@app.on_event("startup")
def startup_event():
    init_db()
    # schedule seed without blocking startup
    if SEED_FROM_FAKESTORE:
        loop = asyncio.get_event_loop()
        loop.create_task(seed_from_fakestore_if_empty())

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/products", response_model=List[Product])
def list_products(q: Optional[str] = Query(None)):
    with SessionLocal() as s:
        qry = s.query(ProductORM)
        if q:
            like = f"%{q.lower()}%"
            qry = qry.filter(
                (ProductORM.title.ilike(like)) | (ProductORM.description.ilike(like))
            )
        return [Product.model_validate(p) for p in qry.limit(200).all()]

@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: int):
    with SessionLocal() as s:
        p = s.get(ProductORM, product_id)
        if not p:
            raise HTTPException(status_code=404, detail="Product not found")
        return Product.model_validate(p)
