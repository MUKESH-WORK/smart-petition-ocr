import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/auth",
    tags=["Auth"]
)

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(credentials: LoginRequest):
    valid_user = os.getenv("ADMIN_USERNAME", "admin")
    valid_pass = os.getenv("ADMIN_PASSWORD", "gdp2026admin")

    if credentials.username == valid_user and credentials.password == valid_pass:
        return {
            "success": True,
            "access_token": "gdp_session_token_authenticated",
            "token_type": "bearer",
            "user": {
                "username": credentials.username,
                "role": "DRO_OFFICER"
            }
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")

@router.get("/me")
async def get_current_user():
    return {
        "username": "officer",
        "role": "DRO_OFFICER",
        "authenticated": True
    }
