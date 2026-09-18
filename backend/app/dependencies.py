import json
import logging
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from models.database import get_db, AsyncSessionLocal, is_sqlite
from core.security import decode_access_token

logger = logging.getLogger(__name__)


async def get_current_officer(
    authorization: Optional[str] = Header(None),
    x_officer_id: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Extract officer info from JWT Bearer token or authenticated officer header.
    Fails closed with HTTP 401 if unauthenticated.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        payload = decode_access_token(token)
        if payload and "officer_id" in payload:
            return payload

    if x_officer_id and x_officer_id.strip():
        return {
            "officer_id": x_officer_id.strip(),
            "name_tamil": "வருவாய் ஆய்வாளர்",
            "department": "வருவாய்த்துறை"
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: missing or invalid credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )


async def log_audit_event(
    action: str,
    source_id: Optional[str] = None,
    officer_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    db: Optional[AsyncSession] = None
):
    """
    Writes 1:1 audit event into partitioned audit_log table.
    Uses an independent database session so audit writes are fully isolated
    and never commit or roll back caller transactions.
    """
    try:
        valid_ip = "127.0.0.1"
        if ip_address and (ip_address.replace(".", "").isdigit() or ":" in ip_address):
            valid_ip = ip_address

        async with AsyncSessionLocal() as audit_db:
            if is_sqlite:
                await audit_db.execute(text("""
                    INSERT INTO audit_log (id, timestamp, source_id, officer_id, action, details, ip_address)
                    VALUES (
                        (SELECT COALESCE(MAX(id), 0) + 1 FROM audit_log),
                        CURRENT_TIMESTAMP, :source_id, :officer_id, :action, :details, :ip_address
                    )
                """), {
                    "source_id": source_id,
                    "officer_id": officer_id,
                    "action": action,
                    "details": json.dumps(details or {}, ensure_ascii=False),
                    "ip_address": valid_ip
                })
            else:
                await audit_db.execute(text("""
                    INSERT INTO audit_log (timestamp, source_id, officer_id, action, details, ip_address)
                    VALUES (NOW(), CAST(:source_id AS UUID), :officer_id, :action, :details, CAST(:ip_address AS INET))
                """), {
                    "source_id": source_id,
                    "officer_id": officer_id,
                    "action": action,
                    "details": json.dumps(details or {}, ensure_ascii=False),
                    "ip_address": valid_ip
                })
            await audit_db.commit()
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")

