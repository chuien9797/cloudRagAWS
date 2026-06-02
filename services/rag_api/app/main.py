from contextlib import asynccontextmanager
import logging

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from services.rag_api.app.auth_context import ensure_bootstrap_admin
from services.rag_api.app.config import (
    OLLAMA_KEEP_ALIVE,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_THREAD,
    OLLAMA_URL,
)
from services.rag_api.app.db import AsyncSessionLocal
from services.rag_api.app.middleware.auth import APIKeyMiddleware
from services.rag_api.app.routers import ask, upload
from services.rag_api.app.routers.auth import router as auth_router
from services.rag_api.app.routers.documents import router as documents_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Warming up Ollama model: %s", OLLAMA_MODEL)
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            await client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": "hello",
                    "stream": False,
                    "keep_alive": OLLAMA_KEEP_ALIVE,
                    "options": {
                        "num_predict": 3,
                        "num_thread": OLLAMA_NUM_THREAD,
                        "num_ctx": OLLAMA_NUM_CTX,
                    },
                },
            )
        logger.info("Ollama warmup complete")
    except Exception as exc:
        logger.warning("Ollama warmup failed (non-fatal): %s", exc)

    async with AsyncSessionLocal() as session:
        await ensure_bootstrap_admin(session)
    yield


app = FastAPI(
    title="CloudRAG - Scalable AI Retrieval Platform",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(APIKeyMiddleware)

app.include_router(upload.router, prefix="/api")
app.include_router(ask.router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(documents_router, prefix="/api")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "CloudRAGToken",
        }
    }
    for path, methods in schema["paths"].items():
        for method in methods.values():
            if path == "/api/auth/login":
                method["security"] = []
            else:
                method["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi


@app.get("/")
def root():
    return {
        "status": "CloudRAG is running",
        "version": "1.0.0",
        "model": OLLAMA_MODEL,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "api"}


@app.get("/ready")
async def ready():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(OLLAMA_URL.replace("/api/generate", "/api/tags"))
            resp.raise_for_status()
    except Exception:
        raise HTTPException(status_code=503, detail="Ollama not reachable - pod not ready")
    return {"status": "ok", "service": "api", "ollama": "reachable"}
