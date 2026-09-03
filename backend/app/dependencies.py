import json
import logging
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from models.database import get_db
from core.security import decode_access_token

logger = logging.getLogger(__name__)


async def get_current_officer(
    authorization: Optional[str] = Header(None),
    x_officer_id: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Extract officer info from JWT Bearer token or development header
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        payload = decode_access_token(token)
        if payload and "officer_id" in payload:
            return payload
    
    if x_officer_id:
        return {"officer_id": x_officer_id, "name_tamil": "வருவாய் ஆய்வாளர்", "department": "வருவாய்த்துறை"}

    # Default fallback officer for testing & direct submissions
    return {"officer_id": "DRO_OFFICER_DEFAULT", "name_tamil": "மாவட்ட வருவாய் அலுவலர்", "department": "வருவாய்த்துறை"}


async def log_audit_event(
    db: AsyncSession,
    action: str,
    source_id: Optional[str] = None,
    officer_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
):
    """
    Writes 1:1 audit event into partitioned audit_log table.
    """
    try:
        valid_ip = "127.0.0.1"
        if ip_address and (ip_address.replace(".", "").isdigit() or ":" in ip_address):
            valid_ip = ip_address
        
        await db.execute(text("""
            INSERT INTO audit_log (timestamp, source_id, officer_id, action, details, ip_address)
            VALUES (NOW(), CAST(:source_id AS UUID), :officer_id, :action, :details, CAST(:ip_address AS INET))
        """), {
            "source_id": source_id,
            "officer_id": officer_id,
            "action": action,
            "details": json.dumps(details or {}, ensure_ascii=False),
            "ip_address": valid_ip
        })
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")
