import os
import hashlib
import hmac
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from models.database import AdminAsyncSessionLocal, UserAsyncSessionLocal, get_admin_db

router = APIRouter(
    prefix="/api/auth",
    tags=["Auth"]
)

class LoginRequest(BaseModel):
    username: str
    password: str

def _verify_password(raw_password: str, stored_hash: Optional[str]) -> bool:
    if not stored_hash or not raw_password:
        return False
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            _, salt, hash_hex = stored_hash.split("$")
            dk = hashlib.pbkdf2_hmac('sha256', raw_password.encode('utf-8'), salt.encode('utf-8'), 100000)
            return hmac.compare_digest(dk.hex(), hash_hex)
        except Exception:
            return False
    legacy_salt = "DRO_SECURE_SALT_2026"
    legacy_hash = hashlib.sha256(f"{legacy_salt}:{raw_password}".encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy_hash, stored_hash)

@router.post("/login")
async def login(credentials: LoginRequest):
    username = credentials.username.strip().lower()
    raw_user = credentials.username.strip()

    # 1. Lookup in Admin DB (admin_users)
    user = None
    try:
        async with AdminAsyncSessionLocal() as admin_db:
            res = await admin_db.execute(
                text("SELECT * FROM admin_users WHERE LOWER(email) = :email OR id = :id LIMIT 1"),
                {"email": username, "id": raw_user}
            )
            user = res.mappings().one_or_none()
    except Exception:
        pass

    # 2. Fallback lookup in User DB (officers)
    if not user:
        try:
            async with UserAsyncSessionLocal() as u_db:
                u_res = await u_db.execute(
                    text("SELECT * FROM officers WHERE LOWER(email) = :email OR officer_id = :id LIMIT 1"),
                    {"email": username, "id": raw_user}
                )
                user = u_res.mappings().one_or_none()
        except Exception:
            pass

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Account not found in database."
        )

    user_status = user.get("status") or "Active"
    if str(user_status).lower() in ["suspended", "disabled", "deactivated", "blocked"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is currently suspended. Please contact District Administrator."
        )

    stored_hash = user.get("password_hash")
    # If no password hash is set on official account, default fallback hash is Govt@2024
    if not stored_hash:
        salt = "DRO_OFFICIAL_DEFAULT_SALT"
        dk = hashlib.pbkdf2_hmac('sha256', b"Govt@2024", salt.encode('utf-8'), 100000)
        stored_hash = f"pbkdf2_sha256${salt}${dk.hex()}"

    if not _verify_password(credentials.password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )

    is_admin = bool(user.get("is_admin")) or user.get("role") in ("DISTRICT_ADMIN", "ADMIN")
    return {
        "success": True,
        "access_token": f"gdp_session_token_{user.get('id') or user.get('officer_id')}",
        "token_type": "bearer",
        "user": {
            "username": user.get("email") or user.get("name") or raw_user,
            "name": user.get("name") or user.get("username"),
            "role": "DISTRICT_ADMIN" if is_admin else "DRO_OFFICER",
            "department": user.get("department")
        }
    }

@router.get("/me")
async def get_current_user():
    return {
        "username": "officer",
        "role": "DRO_OFFICER",
        "authenticated": True
    }

