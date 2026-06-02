import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.rag_api.app.config import AUTH_ADMIN_EMAIL, AUTH_ADMIN_NAME, AUTH_ADMIN_PASSWORD
from services.rag_api.app.db import get_db
from services.rag_api.app.services.auth_service import hash_password


SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000001"


def _valid_uuid(value: str | None) -> str:
    if not value:
        return SYSTEM_USER_ID
    try:
        return str(uuid.UUID(value))
    except (TypeError, ValueError):
        return SYSTEM_USER_ID


async def get_current_user_id(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> str:
    if getattr(request.state, "user_id", None):
        return request.state.user_id

    user_id = _valid_uuid(request.headers.get("X-User-Id"))
    await db.execute(
        text(
            """
            INSERT INTO users (id, email, password_hash, full_name)
            VALUES (:id, :email, :password_hash, :full_name)
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {
            "id": user_id,
            "email": f"{user_id}@local.cloudrag",
            "password_hash": "api-key-dev-user",
            "full_name": "CloudRAG User",
        },
    )
    await db.commit()
    return user_id


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    result = await db.execute(
        text(
            """
            SELECT id, email, full_name
            FROM users
            WHERE id = :id
            """
        ),
        {"id": user_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return {
        "id": str(row["id"]),
        "email": row["email"],
        "full_name": row["full_name"] or row["email"],
    }


async def ensure_bootstrap_admin(db: AsyncSession) -> None:
    await db.execute(
        text(
            """
            INSERT INTO users (email, password_hash, full_name, last_login)
            VALUES (:email, :password_hash, :full_name, NULL)
            ON CONFLICT (email) DO UPDATE
            SET password_hash = EXCLUDED.password_hash,
                full_name = EXCLUDED.full_name
            """
        ),
        {
            "email": AUTH_ADMIN_EMAIL,
            "password_hash": hash_password(AUTH_ADMIN_PASSWORD),
            "full_name": AUTH_ADMIN_NAME,
        },
    )
    await db.commit()
