"""
Name Retention API with JWT Authentication
-------------------------------------------

Docs: http://127.0.0.1:27017/docs
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import bcrypt
from pydantic import BaseModel

# ── Config ───────────────────────────────────────────────
SECRET_KEY = "change-me-to-a-real-secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# ── App ──────────────────────────────────────────────────
app = FastAPI(title="Name Retention API")

bearer_scheme = HTTPBearer()

# ── In-memory stores (swap with a real DB later) ─────────
fake_users_db: dict[str, dict] = {}   # username -> {username, hashed_pw}
names_db: dict[str, list[dict]] = {}  # username -> [{id, name}]
_id_counter = 0


def next_id():
    global _id_counter
    _id_counter += 1
    return _id_counter


# ── Schemas ──────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class NameIn(BaseModel):
    name: str


class NameOut(BaseModel):
    id: int
    name: str


# ── Health check ─────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "uptime": True,
        "users_count": len(fake_users_db),
        "names_count": sum(len(v) for v in names_db.values()),
    }


# ── Auth helpers ─────────────────────────────────────────
def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    token = creds.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None or username not in fake_users_db:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Auth routes ──────────────────────────────────────────
@app.post("/auth/register", response_model=Token)
def register(body: UserCreate):
    if body.username in fake_users_db:
        raise HTTPException(status_code=400, detail="Username taken")
    fake_users_db[body.username] = {
        "username": body.username,
        "hashed_pw": bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode(),
    }
    names_db[body.username] = []
    return Token(access_token=create_token(body.username))


@app.post("/auth/login", response_model=Token)
def login(body: UserCreate):
    user = fake_users_db.get(body.username)
    if not user or not bcrypt.checkpw(body.password.encode(), user["hashed_pw"].encode()):
        raise HTTPException(status_code=401, detail="Bad credentials")
    return Token(access_token=create_token(body.username))


# ── Name CRUD routes (protected) ─────────────────────────
@app.get("/names", response_model=list[NameOut])
def list_names(user: str = Depends(get_current_user)):
    return names_db.get(user, [])


@app.post("/names", response_model=NameOut, status_code=201)
def add_name(body: NameIn, user: str = Depends(get_current_user)):
    entry = {"id": next_id(), "name": body.name}
    names_db.setdefault(user, []).append(entry)
    return entry


@app.get("/names/{name_id}", response_model=NameOut)
def get_name(name_id: int, user: str = Depends(get_current_user)):
    for n in names_db.get(user, []):
        if n["id"] == name_id:
            return n
    raise HTTPException(status_code=404, detail="Name not found")


@app.put("/names/{name_id}", response_model=NameOut)
def update_name(name_id: int, body: NameIn, user: str = Depends(get_current_user)):
    for n in names_db.get(user, []):
        if n["id"] == name_id:
            n["name"] = body.name
            return n
    raise HTTPException(status_code=404, detail="Name not found")


@app.delete("/names/{name_id}")
def delete_name(name_id: int, user: str = Depends(get_current_user)):
    user_names = names_db.get(user, [])
    for i, n in enumerate(user_names):
        if n["id"] == name_id:
            user_names.pop(i)
            return {"detail": "Deleted"}
    raise HTTPException(status_code=404, detail="Name not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=27017)