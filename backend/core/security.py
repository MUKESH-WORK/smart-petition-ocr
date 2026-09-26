import json
import base64
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from app.config import settings

try:
    import jwt
    HAS_JWT = True
except ImportError:
    jwt = None
    HAS_JWT = False


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')


def _b64_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data.encode('utf-8'))


_RUNTIME_SECRET_KEY = None

def _get_secret_key() -> str:
    global _RUNTIME_SECRET_KEY
    cfg_key = getattr(settings, "SECRET_KEY", None)
    if cfg_key and len(str(cfg_key).strip()) >= 16:
        return str(cfg_key).strip()
    if not _RUNTIME_SECRET_KEY:
        import secrets
        _RUNTIME_SECRET_KEY = secrets.token_hex(32)
    return _RUNTIME_SECRET_KEY


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT token with officer claims"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
    
    secret = _get_secret_key()
    algo = getattr(settings, "JWT_ALGORITHM", "HS256")

    if HAS_JWT and jwt is not None:
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, secret, algorithm=algo)

    # Built-in pure python HMAC-SHA256 fallback
    to_encode.update({"exp": int(expire.timestamp())})
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_b64 = _b64_encode(json.dumps(to_encode, separators=(',', ':'), default=str).encode('utf-8'))
    sig_raw = hmac.new(secret.encode('utf-8'), f"{header_b64}.{payload_b64}".encode('utf-8'), hashlib.sha256).digest()
    sig_b64 = _b64_encode(sig_raw)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token"""
    if not token or not isinstance(token, str):
        return None

    secret = _get_secret_key()
    algo = getattr(settings, "JWT_ALGORITHM", "HS256")

    if HAS_JWT and jwt is not None:
        try:
            return jwt.decode(token, secret, algorithms=[algo])
        except Exception:
            return None

    # Built-in pure python HMAC-SHA256 fallback
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        expected_sig = _b64_encode(hmac.new(secret.encode('utf-8'), f"{header_b64}.{payload_b64}".encode('utf-8'), hashlib.sha256).digest())
        if not hmac.compare_digest(sig_b64, expected_sig):
            return None
        payload = json.loads(_b64_decode(payload_b64).decode('utf-8'))
        exp = payload.get("exp")
        if exp and datetime.now(timezone.utc).timestamp() > exp:
            return None
        return payload
    except Exception:
        return None

