import hashlib
import secrets
from typing import Optional

from .db import get_conn

ROLES = {"customer", "worker", "admin"}


def _hash_password(password: str, salt: str) -> str:
    pwd = password.encode("utf-8")
    salt_bytes = salt.encode("utf-8")
    digest = hashlib.pbkdf2_hmac("sha256", pwd, salt_bytes, 100_000)
    return digest.hex()


def create_user(username: str, role: str, password: str) -> int:
    salt = secrets.token_hex(16)
    password_hash = _hash_password(password, salt)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, role, password_hash, salt) VALUES (?, ?, ?, ?)",
            (username, role, password_hash, salt),
        )
        return int(cur.lastrowid)


def authenticate(username: str, password: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, username, role, password_hash, salt FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if not row:
        return None
    candidate = _hash_password(password, row["salt"])
    if candidate != row["password_hash"]:
        return None
    return {"id": row["id"], "username": row["username"], "role": row["role"]}


def get_user_name(request) -> Optional[str]:
    return request.session.get("user_name")


def get_user_role(request) -> Optional[str]:
    return request.session.get("user_role")


def set_user_session(request, user_id: int, name: str, role: str) -> None:
    request.session["user_id"] = user_id
    request.session["user_name"] = name
    request.session["user_role"] = role


def clear_user_session(request) -> None:
    request.session.clear()
