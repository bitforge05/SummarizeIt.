"""
auth.py — Username/password auth with bcrypt hashing + JWT tokens.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import bcrypt
from dotenv import load_dotenv
from fastapi import HTTPException, Header

from database import get_db

load_dotenv()

JWT_SECRET    = os.getenv("JWT_SECRET", "supersecretchangeme123")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 30


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except ValueError:
        return False


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_token(user_id: str, username: str) -> str:
    payload = {
        "sub":      user_id,
        "username": username,
        "exp":      datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session token. Please log in again.")


# ── FastAPI dependency ────────────────────────────────────────────────────────

def get_current_user(authorization: str = Header(default=None)) -> dict:
    """
    Extract and validate the Bearer JWT from the Authorization header.
    Returns the decoded payload dict { sub, username, exp }.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required. Please log in.")
    token = authorization.split(" ", 1)[1]
    return decode_token(token)


# ── Auth operations ───────────────────────────────────────────────────────────

def register_user(username: str, password: str) -> dict:
    username = username.strip()
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    db = get_db()
    existing = db.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()
    if existing:
        db.close()
        raise HTTPException(
            status_code=409,
            detail="Username already taken. Did you mean to log in?"
        )

    user_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
        (user_id, username, hash_password(password)),
    )
    db.commit()
    db.close()

    return {
        "token":    create_token(user_id, username),
        "username": username,
        "user_id":  user_id,
    }


def login_user(username: str, password: str) -> dict:
    username = username.strip()
    db = get_db()
    row = db.execute(
        "SELECT id, password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    db.close()

    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password.")

    return {
        "token":    create_token(row["id"], username),
        "username": username,
        "user_id":  row["id"],
    }
