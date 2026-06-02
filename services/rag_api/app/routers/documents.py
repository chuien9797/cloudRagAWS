import logging
import mimetypes
import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pathlib import Path
from pydantic import BaseModel
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from services.rag_api.app.auth_context import get_current_user_id
from services.rag_api.app.db import get_db

logger = logging.getLogger(__name__)
router = APIRouter()
S3_BUCKET = os.getenv("S3_BUCKET", "cloudrag-uploads")


class VisibilityRequest(BaseModel):
    is_public: bool


async def _get_accessible_document(
    db: AsyncSession,
    doc_id: str,
    user_id: str,
):
    result = await db.execute(
        text("""
            SELECT id, user_id, filename, s3_uri, is_public
            FROM documents
            WHERE id = :id
              AND status != 'deleted'
              AND (user_id = :user_id OR is_public = TRUE)
        """),
        {"id": doc_id, "user_id": user_id}
    )
    return result.fetchone()


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    without_scheme = uri.replace("s3://", "", 1)
    bucket, _, key = without_scheme.partition("/")
    return bucket, key


@router.get("/documents")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        result = await db.execute(
            text("""
                SELECT id, user_id, filename, doc_type, status, is_public,
                       characters_extracted, total_chunks, uploaded_at
                FROM documents
                WHERE status != 'deleted'
                  AND (user_id = :user_id OR is_public = TRUE)
                ORDER BY uploaded_at DESC
            """),
            {"user_id": user_id}
        )
        rows = result.fetchall()
        return [
            {
                "id":                   str(row.id),
                "owner_user_id":        str(row.user_id),
                "filename":             row.filename,
                "doc_type":             row.doc_type,
                "status":               row.status,
                "is_public":            row.is_public,
                "characters_extracted": row.characters_extracted,
                "total_chunks":         row.total_chunks,
                "uploaded_at":          row.uploaded_at.isoformat() if row.uploaded_at else None,
            }
            for row in rows
        ]
    except Exception as exc:
        logger.error("Failed to fetch documents: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch documents")


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        result = await db.execute(
            text("SELECT id FROM documents WHERE id = :id AND user_id = :user_id"),
            {"id": doc_id, "user_id": user_id}
        )
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Document not found")

        await db.execute(
            text("UPDATE documents SET status = 'deleted' WHERE id = :id"),
            {"id": doc_id}
        )
        await db.commit()
        return {"message": "Document deleted", "doc_id": doc_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to delete document: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.patch("/documents/{doc_id}/visibility")
async def update_document_visibility(
    doc_id: str,
    request: VisibilityRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        result = await db.execute(
            text("SELECT id FROM documents WHERE id = :id AND user_id = :user_id AND status != 'deleted'"),
            {"id": doc_id, "user_id": user_id}
        )
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Document not found")

        await db.execute(
            text("UPDATE documents SET is_public = :is_public WHERE id = :id"),
            {"id": doc_id, "is_public": request.is_public}
        )
        await db.commit()
        return {"doc_id": doc_id, "is_public": request.is_public}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update document visibility: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update document visibility")


@router.get("/documents/{doc_id}/file")
async def get_document_file(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    row = await _get_accessible_document(db, doc_id, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    if not row.s3_uri:
        raise HTTPException(status_code=404, detail="Original file is not available")

    media_type = mimetypes.guess_type(row.filename)[0] or "application/octet-stream"

    if row.s3_uri.startswith("s3://"):
        bucket, key = _parse_s3_uri(row.s3_uri)
        bucket = bucket or S3_BUCKET
        try:
            s3 = boto3.client("s3")
            obj = s3.get_object(Bucket=bucket, Key=key)
            body = obj["Body"].read()
        except (BotoCoreError, ClientError) as exc:
            logger.error("Failed to fetch %s from S3: %s", row.s3_uri, exc)
            raise HTTPException(status_code=502, detail="Original file could not be fetched from object storage")

        return Response(
            content=body,
            media_type=media_type,
            headers={"Content-Disposition": f'inline; filename="{row.filename}"'},
        )

    if not row.s3_uri.startswith("file://"):
        raise HTTPException(status_code=404, detail="Original file location is not supported")

    path = Path(row.s3_uri.replace("file://", "", 1))
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Original file is missing from local storage")

    return FileResponse(path, filename=row.filename, media_type=media_type)


@router.get("/sessions")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        result = await db.execute(
            text("""
                SELECT id, title, created_at, updated_at
                FROM chat_sessions
                WHERE user_id = :user_id
                ORDER BY updated_at DESC
                LIMIT 50
            """),
            {"user_id": user_id}
        )
        rows = result.fetchall()
        return [
            {
                "id":         str(row.id),
                "title":      row.title,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]
    except Exception as exc:
        logger.error("Failed to fetch sessions: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch sessions")


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        result = await db.execute(
            text("""
                SELECT id, role, content, prompt_tokens,
                       completion_tokens, total_tokens, created_at
                FROM chat_messages
                WHERE session_id = :session_id
                  AND session_id IN (
                      SELECT id FROM chat_sessions WHERE user_id = :user_id
                  )
                ORDER BY created_at ASC
            """),
            {"session_id": session_id, "user_id": user_id}
        )
        rows = result.fetchall()
        return [
            {
                "id":                str(row.id),
                "role":              row.role,
                "content":           row.content,
                "prompt_tokens":     row.prompt_tokens,
                "completion_tokens": row.completion_tokens,
                "total_tokens":      row.total_tokens,
                "created_at":        row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    except Exception as exc:
        logger.error("Failed to fetch messages: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch messages")


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    try:
        result = await db.execute(
            text("SELECT id FROM chat_sessions WHERE id = :id AND user_id = :user_id"),
            {"id": session_id, "user_id": user_id}
        )
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Session not found")

        await db.execute(
            text("DELETE FROM chat_sessions WHERE id = :id AND user_id = :user_id"),
            {"id": session_id, "user_id": user_id}
        )
        await db.commit()
        return {"message": "Session deleted", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to delete session: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to delete session")
