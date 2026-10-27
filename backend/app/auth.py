from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Depends, Header, HTTPException, status
from pymongo.database import Database

from .db import get_db

PBKDF2_ITERATIONS = 210_000
SESSION_HOURS = 12


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("La contraseña no puede estar vacía")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_session(db: Database, account: dict) -> str:
    token = secrets.token_urlsafe(40)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(UTC)
    db.sessions.insert_one(
        {
            "token_hash": token_hash,
            "account_username": account["username"],
            "role": account["role"],
            "student_code": account.get("student_code"),
            "created_at": now,
            "expires_at": now + timedelta(hours=SESSION_HOURS),
        }
    )
    return token


def revoke_session(db: Database, token: str) -> None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    db.sessions.delete_one({"token_hash": token_hash})


def _extract_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión requerida")
    return authorization.split(" ", 1)[1].strip()


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Database = Depends(get_db),
) -> dict:
    token = _extract_token(authorization)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    session = db.sessions.find_one({"token_hash": token_hash})
    if not session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida")

    expires_at = session.get("expires_at")
    now = datetime.now(UTC)
    if expires_at:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= now:
            db.sessions.delete_one({"_id": session["_id"]})
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "La sesión expiró")

    account = db.accounts.find_one({"username": session["account_username"]})
    if not account or account.get("status") != "ACTIVE":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Cuenta inactiva o inexistente")
    return account


def require_role(*roles: str):
    normalized = {role.upper() for role in roles}

    def dependency(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role", "").upper() not in normalized:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para esta operación")
        return user

    return dependency
