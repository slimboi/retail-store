from datetime import datetime, timedelta
import os
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from jose import jwt, JWTError

from sqlalchemy import create_engine, Integer, String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from argon2 import PasswordHasher

# --------------------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://app:app@postgres:5432/cloudpros"
)
JWT_SECRET = os.getenv("JWT_SECRET", "devsecret")
JWT_ALGO = "HS256"
JWT_TTL_HOURS = int(os.getenv("JWT_TTL_HOURS", "24"))

# --------------------------------------------------------------------------------------
# DB
# --------------------------------------------------------------------------------------
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --------------------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

pwd = PasswordHasher()
auth_scheme = HTTPBearer()

@app.on_event("startup")
def on_startup():
    # Idempotent: creates table if not exists (works even if init SQL already ran)
    Base.metadata.create_all(engine)

@app.get("/health")
def health():
    return {"ok": True}

# --------------------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------------------
from pydantic import BaseModel, Field

class SignUpBody(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=3, max_length=256)
    email: Optional[str] = None
    avatar_url: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class MeOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime

# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(hours=JWT_TTL_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def require_user_id(token=Depends(auth_scheme)) -> int:
    try:
        payload = jwt.decode(token.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="invalid token")

# --------------------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------------------
# SIGNUP – supports JSON body *and* query params (for your existing UI)
@app.post("/signup", status_code=201)
def signup(
    body: Optional[SignUpBody] = Body(default=None),
    username: Optional[str] = None,
    password: Optional[str] = None,
    email: Optional[str] = None,
    avatar_url: Optional[str] = None,
    db: Session = Depends(get_db),
):
    # accept either JSON or query params
    if body:
        username = body.username
        password = body.password
        email = body.email
        avatar_url = body.avatar_url

    if not username or not password:
        raise HTTPException(400, "username and password required")

    try:
        u = User(
            username=username.strip(),
            email=(email or None),
            avatar_url=(avatar_url or None),
            password_hash=pwd.hash(password),
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        return {"id": u.id, "username": u.username, "email": u.email, "avatar_url": u.avatar_url}
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "username already exists")

# LOGIN – supports form (application/x-www-form-urlencoded) and JSON
@app.post("/login", response_model=Token)
def login(
    db: Session = Depends(get_db),
    # form style
    f_username: Optional[str] = Form(default=None, alias="username"),
    f_password: Optional[str] = Form(default=None, alias="password"),
    # json style
    j: Optional[SignUpBody] = Body(default=None),
):
    username = f_username or (j.username if j else None)
    password = f_password or (j.password if j else None)
    if not username or not password:
        raise HTTPException(400, "username and password required")

    u: Optional[User] = db.query(User).filter(User.username == username).one_or_none()
    if not u:
        # match your UI’s expectation: 401 if not found
        raise HTTPException(401, "invalid credentials")

    try:
        pwd.verify(u.password_hash, password)
    except Exception:
        raise HTTPException(401, "invalid credentials")

    return Token(access_token=create_token(u.id))

@app.get("/me", response_model=MeOut)
def me(user_id: int = Depends(require_user_id), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "user not found")
    return MeOut(id=u.id, username=u.username, email=u.email, avatar_url=u.avatar_url, created_at=u.created_at)
