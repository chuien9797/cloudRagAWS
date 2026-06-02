from dotenv import load_dotenv
import os

load_dotenv()

ENV = os.getenv("ENV", "development")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2:1.5b")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "45m")
OLLAMA_NUM_THREAD = int(os.getenv("OLLAMA_NUM_THREAD", "2"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "3072"))

ASK_TOP_K = int(os.getenv("ASK_TOP_K", "5"))
ASK_MAX_QUERY_VARIANTS = int(os.getenv("ASK_MAX_QUERY_VARIANTS", "3"))
ASK_MAX_CONTEXT_WORDS = int(os.getenv("ASK_MAX_CONTEXT_WORDS", "650"))
ASK_FACTUAL_NUM_PREDICT = int(os.getenv("ASK_FACTUAL_NUM_PREDICT", "120"))
ASK_ANALYTICAL_NUM_PREDICT = int(os.getenv("ASK_ANALYTICAL_NUM_PREDICT", "320"))
ASK_GROUND_CITATIONS = os.getenv("ASK_GROUND_CITATIONS", "true").strip().lower() in {"1", "true", "yes", "on"}

API_KEY = os.getenv("API_KEY", "")
AUTH_SECRET = os.getenv("AUTH_SECRET", API_KEY or "cloudrag-dev-auth-secret")
AUTH_TOKEN_TTL_HOURS = int(os.getenv("AUTH_TOKEN_TTL_HOURS", "12"))
AUTH_ADMIN_EMAIL = os.getenv("AUTH_ADMIN_EMAIL", "admin@cloudrag.local").strip().lower()
AUTH_ADMIN_PASSWORD = os.getenv("AUTH_ADMIN_PASSWORD", "ChangeMe123!")
AUTH_ADMIN_NAME = os.getenv("AUTH_ADMIN_NAME", "CloudRAG Admin").strip()
