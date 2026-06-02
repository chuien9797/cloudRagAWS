# services/rag_api/app/routers/upload.py

import os
import uuid
import logging
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from services.rag_api.app.auth_context import get_current_user_id
from services.rag_api.app.db import get_db
from services.rag_api.app.services.rag_service import add_document
from services.rag_api.app.services.file_parser import parse_file
from services.rag_api.app.services.document_classifier import (
    classify_document,
    get_format_label,
)

logger = logging.getLogger(__name__)
router = APIRouter()

SUPPORTED_TYPES = {"pdf", "docx", "txt", "csv", "log"}
MAX_FILE_BYTES  = 10 * 1024 * 1024
S3_BUCKET       = os.getenv("S3_BUCKET", "cloudrag-uploads")
LOCAL_UPLOAD_DIR = Path(os.getenv("LOCAL_UPLOAD_DIR", "/app/uploads"))

def _upload_to_s3(content: bytes, filename: str, doc_id: str, content_type: str) -> str | None:
    if os.getenv("ENV", "development") != "production":
        logger.info("Skipping S3 upload (ENV is not production)")
        return None

    safe_filename = filename.replace(" ", "_")
    s3_key = f"uploads/{doc_id}/{safe_filename}"

    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=content,
            ContentType=content_type or "application/octet-stream",
            Tagging="source=cloudrag-api",
        )
        uri = f"s3://{S3_BUCKET}/{s3_key}"
        logger.info("Uploaded %s to %s", filename, uri)
        return uri
    except (BotoCoreError, ClientError) as exc:
        logger.error("S3 upload failed for doc_id=%s: %s", doc_id, exc)
        raise HTTPException(
            status_code=502,
            detail=f"File indexed successfully but S3 upload failed: {exc}",
        )


def _save_local_upload(content: bytes, filename: str, doc_id: str) -> str:
    safe_filename = Path(filename).name.replace(" ", "_")
    doc_dir = LOCAL_UPLOAD_DIR / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    path = doc_dir / safe_filename
    path.write_bytes(content)
    return str(path)


def _document_uri(local_path: str, s3_uri: str | None) -> str:
    return s3_uri or f"file://{local_path}"


async def _save_document_to_db(
    db: AsyncSession,
    doc_id: str,
    filename: str,
    doc_type: str,
    s3_uri: str | None,
    characters_extracted: int,
    total_chunks: int,
    user_id: str,
    is_public: bool,
    status: str = "indexed",
) -> None:
    await db.execute(
        text("""
            INSERT INTO documents (
                id, user_id, filename, s3_uri, chroma_doc_id,
                doc_type, status, is_public,
                characters_extracted, total_chunks
            ) VALUES (
                :id, :user_id, :filename, :s3_uri, :chroma_doc_id,
                :doc_type, :status, :is_public,
                :characters_extracted, :total_chunks
            )
        """),
        {
            "id":                   doc_id,
            "user_id":              user_id,
            "filename":             filename,
            "s3_uri":               s3_uri,
            "chroma_doc_id":        doc_id,
            "doc_type":             doc_type,
            "status":               status,
            "is_public":            is_public,
            "characters_extracted": characters_extracted,
            "total_chunks":         total_chunks,
        }
    )
    await db.commit()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    is_public: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
   
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    ext = file.filename.lower().split(".")[-1]
    if ext not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{ext}. Supported: {SUPPORTED_TYPES}",
        )

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File too large: {len(content) / 1024 / 1024:.1f} MB. "
                f"Maximum allowed size is {MAX_FILE_BYTES // 1024 // 1024} MB."
            ),
        )

    # Parse — returns list[{"text": str, "page_number": int|None}] 
    try:
        pages = parse_file(file.filename, content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Parsing failed: {exc}")

    if not pages:
        raise HTTPException(status_code=400, detail="No readable text extracted from file")

    # Combine all page text for classification and character count
    full_text = " ".join(p["text"] for p in pages if p.get("text"))

    if not full_text.strip():
        raise HTTPException(status_code=400, detail="No readable text extracted from file")

    # Classify + ID 
    doc_type = classify_document(full_text)
    doc_id   = str(uuid.uuid4())

    try:
        total_chunks = add_document(
            doc_id=doc_id,
            pages=pages,
            metadata={
                "filename":     file.filename,
                "content_type": file.content_type or "unknown",
                "doc_type":     doc_type,
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to index document: {exc}")

    local_path = _save_local_upload(content, file.filename, doc_id)

    # S3
    s3_uri = _upload_to_s3(
        content=content,
        filename=file.filename,
        doc_id=doc_id,
        content_type=file.content_type or "application/octet-stream",
    )

    # PostgreSQL
    try:
        await _save_document_to_db(
            db=db,
            doc_id=doc_id,
            filename=file.filename,
            doc_type=doc_type,
            s3_uri=_document_uri(local_path, s3_uri),
            characters_extracted=len(full_text),
            total_chunks=total_chunks,
            user_id=user_id,
            is_public=is_public,
            status="indexed",
        )
    except Exception as exc:
        logger.error("Failed to save document to PostgreSQL: %s", exc)

    return {
        "message":              "File uploaded and indexed successfully",
        "doc_id":               doc_id,
        "filename":             file.filename,
        "detected_type":        get_format_label(doc_type),
        "characters_extracted": len(full_text),
        "total_chunks":         total_chunks,
        "s3_uri":               _document_uri(local_path, s3_uri),
        "is_public":            is_public,
    }
