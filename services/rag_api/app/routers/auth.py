from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.rag_api.app.auth_context import get_current_user
from services.rag_api.app.db import get_db
from services.rag_api.app.services.auth_service import (
    create_access_token,
    require_credentials_present,
    verify_password,
)


router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/auth/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    email, password = require_credentials_present(payload.email, payload.password)
    result = await db.execute(
        text(
            """
            SELECT id, email, password_hash, full_name
            FROM users
            WHERE lower(email) = :email
            """
        ),
        {"email": email},
    )
    row = result.mappings().first()
    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    await db.execute(
        text("UPDATE users SET last_login = NOW() WHERE id = :id"),
        {"id": row["id"]},
    )
    await db.commit()

    user = {
        "id": str(row["id"]),
        "email": row["email"],
        "full_name": row["full_name"] or row["email"],
    }
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": user,
    }


@router.get("/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}


@router.post("/auth/logout")
async def logout():
    return {"status": "ok"}
