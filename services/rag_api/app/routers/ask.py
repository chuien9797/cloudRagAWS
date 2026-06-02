import uuid
import logging
from typing import Optional
import re
from nltk.tokenize import sent_tokenize

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import httpx

from services.rag_api.app.auth_context import get_current_user_id
from services.rag_api.app.db import get_db
from services.rag_api.app.services.rag_service import hybrid_retrieve, reranker
from services.rag_api.app.services.prompt_templates import build_prompt, is_factual_question
from services.rag_api.app.services.document_classifier import get_format_label
from services.rag_api.app.config import (
    ASK_ANALYTICAL_NUM_PREDICT,
    ASK_FACTUAL_NUM_PREDICT,
    ASK_GROUND_CITATIONS,
    ASK_MAX_CONTEXT_WORDS,
    ASK_MAX_QUERY_VARIANTS,
    ASK_TOP_K,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_THREAD,
    OLLAMA_URL,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Swagger default placeholders that should be treated as "no session"
_INVALID_SESSION_IDS = {"", "string", "null", "none", "undefined"}



def _source_label(meta: dict, index: int) -> str:
    page = meta.get("page_number")
    paragraph = meta.get("paragraph_number")
    chunk_id = meta.get("chunk_id")
    parts = [f"Source [{index}]"]
    if page is not None:
        parts.append(f"page {page}")
    if paragraph is not None:
        parts.append(f"paragraph {paragraph}")
    elif chunk_id is not None:
        parts.append(f"chunk {chunk_id}")
    return " - ".join(parts)


def trim_context(docs: list[str], metas: list[dict], max_words: int = ASK_MAX_CONTEXT_WORDS) -> str:
    out, total = [], 0
    for i, (doc, meta) in enumerate(zip(docs, metas), start=1):
        source_block = f"{_source_label(meta, i)}\n{doc}"
        words = len(source_block.split())
        if total + words > max_words:
            break
        out.append(source_block)
        total += words
    if not out and docs:
        out.append(f"{_source_label(metas[0] if metas else {}, 1)}\n{docs[0]}")
    return "\n\n---\n\n".join(out)


def _query_variants(question: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"[?\n]+", question) if part.strip()]
    variants = []
    seen = set()

    for candidate in [question.strip(), *parts]:
        normalized = candidate.lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            variants.append(candidate)

    return variants[:ASK_MAX_QUERY_VARIANTS]


def _merge_retrieval_results(results: list[tuple[list[str], list[dict], list[float]]]) -> tuple[list[str], list[dict], list[float]]:
    merged = {}

    for docs, metas, scores in results:
        for doc, meta, score in zip(docs, metas, scores):
            key = (
                meta.get("doc_id"),
                meta.get("chunk_id"),
                meta.get("page_number"),
            )
            existing = merged.get(key)
            if existing is None or score > existing["score"]:
                merged[key] = {
                    "doc": doc,
                    "meta": meta,
                    "score": float(score),
                }

    ranked = sorted(merged.values(), key=lambda item: item["score"], reverse=True)
    return (
        [item["doc"] for item in ranked],
        [item["meta"] for item in ranked],
        [item["score"] for item in ranked],
    )


def _answer_has_citations(answer: str) -> bool:
    return bool(re.search(r"\[\d+(?:\s*,\s*\d+)*\]", answer))


def _inject_fallback_citations(answer: str, citations: list[dict]) -> str:
    if not answer or not citations or _answer_has_citations(answer):
        return answer

    fallback = f"[{citations[0]['citation_id']}]"
    pieces = re.split(r"(\n+)", answer)
    updated = []
    for piece in pieces:
        if not piece or piece.startswith("\n") or piece.isspace():
            updated.append(piece)
            continue
        stripped = piece.rstrip()
        updated.append(f"{stripped} {fallback}{piece[len(stripped):]}")
    return "".join(updated)


def _ground_answer_with_citations(answer: str, citations: list[dict]) -> str:
    if not answer or not citations:
        return answer

    citation_texts = [c.get("highlight_text") or c.get("chunk_text") or c.get("chunk") or "" for c in citations]
    lines = answer.splitlines()
    grounded_lines = []

    for line in lines:
        if not line.strip():
            grounded_lines.append(line)
            continue

        prefix = ""
        stripped_line = line.lstrip()
        if stripped_line.startswith(("- ", "* ")):
            prefix = stripped_line[:2]
            stripped_line = stripped_line[2:].strip()

        try:
            sentences = sent_tokenize(stripped_line)
        except Exception:
            sentences = [stripped_line]

        grounded_sentences = []
        for sentence in sentences:
            clean_sentence = re.sub(r"\s*\[\d+(?:\s*,\s*\d+)*\]", "", sentence).strip()
            if not clean_sentence:
                continue
            scores = reranker.predict([[clean_sentence, text] for text in citation_texts])
            best_index = max(range(len(scores)), key=lambda idx: scores[idx])
            citation_token = f"[{citations[best_index]['citation_id']}]"
            grounded_sentences.append(f"{clean_sentence} {citation_token}")

        rebuilt = " ".join(grounded_sentences).strip()
        grounded_lines.append(f"{prefix}{rebuilt}" if prefix else rebuilt)

    return "\n".join(grounded_lines)



# REQUEST MODEL
class QuestionRequest(BaseModel):
    question: str
    doc_id: Optional[str] = None
    session_id: Optional[str] = None    # optional — auto-created if not provided



# OLLAMA CALL
async def call_ollama(payload: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Ollama timed out. Try again — model may still be warming up."
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot reach Ollama. Check the ollama container is running."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")



# DB HELPERS
def _is_valid_session_id(session_id: str | None) -> bool:
    """
    Returns False for None, empty string, or Swagger placeholder values.
    Prevents 'string' or 'null' typed in Swagger from being used as real IDs.
    """
    if not session_id:
        return False
    return session_id.strip().lower() not in _INVALID_SESSION_IDS


async def _ensure_session(
    db: AsyncSession,
    session_id: str | None,
    question: str,
    user_id: str,
) -> str:
    """
    If a valid session_id is provided and exists in DB, return it.
    Otherwise create a new session and return its ID.
    Title defaults to the first 60 chars of the question.
    """
    if _is_valid_session_id(session_id):
        row = await db.execute(
            text("SELECT id FROM chat_sessions WHERE id = :id AND user_id = :user_id"),
            {"id": session_id, "user_id": user_id}
        )
        if row.fetchone():
            return session_id

    # Create a new session
    new_id = str(uuid.uuid4())
    title  = question[:60] + ("..." if len(question) > 60 else "")
    await db.execute(
        text("""
            INSERT INTO chat_sessions (id, user_id, title)
            VALUES (:id, :user_id, :title)
        """),
        {"id": new_id, "user_id": user_id, "title": title}
    )
    await db.commit()
    return new_id


async def _save_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    prompt_tokens: int = None,
    completion_tokens: int = None,
    total_tokens: int = None,
) -> str:
    """Insert a chat message row, return its ID."""
    msg_id = str(uuid.uuid4())
    await db.execute(
        text("""
            INSERT INTO chat_messages (
                id, session_id, role, content,
                prompt_tokens, completion_tokens, total_tokens
            ) VALUES (
                :id, :session_id, :role, :content,
                :prompt_tokens, :completion_tokens, :total_tokens
            )
        """),
        {
            "id":                msg_id,
            "session_id":        session_id,
            "role":              role,
            "content":           content,
            "prompt_tokens":     prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens":      total_tokens,
        }
    )
    await db.commit()
    return msg_id


async def _save_citations(
    db: AsyncSession,
    message_id: str,
    docs: list[str],
    metas: list[dict],
    scores: list[float],
) -> None:
    """Insert one citation row per source chunk."""
    # Some retrieved chunks can reference stale vector entries whose doc_id
    # no longer exists in PostgreSQL. Filter them to avoid FK violations.
    seen_ids = {
        meta.get("doc_id")
        for meta in metas
        if meta.get("doc_id")
    }
    valid_doc_ids = set()
    for document_id in seen_ids:
        row = await db.execute(
            text("SELECT 1 FROM documents WHERE id = :id"),
            {"id": document_id}
        )
        if row.fetchone():
            valid_doc_ids.add(document_id)

    for i, (chunk, meta, score) in enumerate(zip(docs, metas, scores)):
        document_id = meta.get("doc_id")
        if not document_id:
            continue
        if document_id not in valid_doc_ids:
            continue

        await db.execute(
            text("""
                INSERT INTO message_citations (
                    id, message_id, document_id,
                    chunk_text, page_number, chunk_index, relevance_score
                ) VALUES (
                    :id, :message_id, :document_id,
                    :chunk_text, :page_number, :chunk_index, :relevance_score
                )
            """),
            {
                "id":              str(uuid.uuid4()),
                "message_id":      message_id,
                "document_id":     document_id,
                "chunk_text":      chunk,
                "page_number":     meta.get("page_number"),
                "chunk_index":     meta.get("chunk_id", i),
                "relevance_score": float(score),
            }
        )
    await db.commit()


async def _can_access_document(db: AsyncSession, doc_id: str, user_id: str) -> bool:
    result = await db.execute(
        text("""
            SELECT 1 FROM documents
            WHERE id = :id
              AND status != 'deleted'
              AND (user_id = :user_id OR is_public = TRUE)
        """),
        {"id": doc_id, "user_id": user_id}
    )
    return result.fetchone() is not None


async def _filter_accessible_sources(
    db: AsyncSession,
    docs: list[str],
    metas: list[dict],
    scores: list[float],
    user_id: str,
) -> tuple[list[str], list[dict], list[float]]:
    doc_ids = sorted({meta.get("doc_id") for meta in metas if meta.get("doc_id")})
    if not doc_ids:
        return [], [], []

    allowed = set()
    for doc_id in doc_ids:
        if await _can_access_document(db, doc_id, user_id):
            allowed.add(doc_id)

    filtered = [
        (doc, meta, score)
        for doc, meta, score in zip(docs, metas, scores)
        if meta.get("doc_id") in allowed
    ]
    if not filtered:
        return [], [], []
    return [item[0] for item in filtered], [item[1] for item in filtered], [item[2] for item in filtered]



# MAIN ENDPOINT
@router.post("/ask/with-sources")
async def ask_with_sources(
    request: QuestionRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    if request.doc_id and not await _can_access_document(db, request.doc_id, user_id):
        raise HTTPException(status_code=404, detail="Document not found")

    retrieval_results = [
        hybrid_retrieve(
            query=query_text,
            top_k=ASK_TOP_K,
            doc_id=request.doc_id
        )
        for query_text in _query_variants(request.question)
    ]
    docs, metas, scores = _merge_retrieval_results(retrieval_results)
    docs, metas, scores = await _filter_accessible_sources(db, docs, metas, scores, user_id)
    docs, metas, scores = docs[:ASK_TOP_K], metas[:ASK_TOP_K], scores[:ASK_TOP_K]

    if not docs:
        return {
            "answer":     "No relevant information found in the document.",
            "sources":    [],
            "session_id": None,
        }

    context    = trim_context(docs, metas)
    first_meta = metas[0] if metas else {}
    filename   = first_meta.get("filename", "the document")
    doc_type   = first_meta.get("doc_type",  "general")

    prompt = build_prompt(
        context=context,
        question=request.question,
        filename=filename,
        doc_type=doc_type
    )

    num_predict = ASK_FACTUAL_NUM_PREDICT if is_factual_question(request.question) else ASK_ANALYTICAL_NUM_PREDICT

    data = await call_ollama({
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": {
            "num_predict": num_predict,
            "temperature": 0.1,
            "top_p":       0.9,
            "num_thread":  OLLAMA_NUM_THREAD,
            "num_ctx":     OLLAMA_NUM_CTX,
        }
    })

    answer = data.get("response", "").strip()
    if not answer:
        raise HTTPException(status_code=500, detail="Model returned empty response")

    # Token usage 
    prompt_tokens     = data.get("prompt_eval_count")
    completion_tokens = data.get("eval_count")
    total_tokens      = (
        (prompt_tokens or 0) + (completion_tokens or 0)
    ) or None

    # Placeholder scores — same order as docs from hybrid_retrieve
    session_id = None
    try:
        session_id = await _ensure_session(db, request.session_id, request.question, user_id)

        await _save_message(
            db=db,
            session_id=session_id,
            role="user",
            content=request.question,
        )

        assistant_msg_id = await _save_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content=answer,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        await _save_citations(
            db=db,
            message_id=assistant_msg_id,
            docs=docs,
            metas=metas,
            scores=scores,
        )

    except Exception as exc:
        logger.error("Failed to save chat to PostgreSQL: %s", exc)

    
    citations = [
        {
            "citation_id": i + 1,
            "doc_id":      meta.get("doc_id"),
            "document_id": meta.get("doc_id"),
            "chunk":       doc,
            "chunk_text":  doc,
            "filename":    meta.get("filename", "unknown"),
            "chunk_id":    meta.get("chunk_id", -1),
            "chunk_index": meta.get("chunk_id", -1),
            "page_number": meta.get("page_number"),
            "paragraph_number": meta.get("paragraph_number"),
            "paragraph_index": meta.get("paragraph_number"),
            "line_start": None,
            "line_end": None,
            "highlight_text": doc,
            "similarity_score": scores[i] if i < len(scores) else None,
            "relevance_score": scores[i] if i < len(scores) else None,
            "citation": f"[{i + 1}]",
            "location": _source_label(meta, i + 1),
        }
        for i, (doc, meta) in enumerate(zip(docs, metas))
    ]
    answer = _inject_fallback_citations(answer, citations)
    if ASK_GROUND_CITATIONS:
        answer = _ground_answer_with_citations(answer, citations)

    return {
        "answer":        answer,
        "detected_type": get_format_label(doc_type),
        "sources":       citations,
        "citations":     citations,
        "session_id":    session_id,
        "token_usage": {
            "prompt_tokens":     prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens":      total_tokens,
        }
    }
