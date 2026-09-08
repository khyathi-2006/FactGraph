"""Runtime configuration read from environment variables."""

import os
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Vercel filesystem is read-only except /tmp.
if os.environ.get("VERCEL"):
    RUNTIME_DIR = Path(tempfile.gettempdir()) / "factgraph"
else:
    RUNTIME_DIR = PROJECT_ROOT

RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = Path(os.environ.get("FACTLAYER_DB", str(RUNTIME_DIR / "factlayer.db")))
UPLOAD_DIR = Path(os.environ.get("FACTLAYER_UPLOADS", str(RUNTIME_DIR / "uploads")))

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
LLM_API_KEY_ENV_VARS = ("OPENAI_API_KEY", "GROQ_API_KEY", "AI_API_KEY")
EXTRACTION_MODEL = os.environ.get("FACTLAYER_EXTRACTION_MODEL", "gpt-4o-mini")
CLASSIFICATION_MODEL = os.environ.get("FACTLAYER_CLASSIFICATION_MODEL", "gpt-4o-mini")

MAX_CHUNK_CHARS = int(os.environ.get("FACTLAYER_MAX_CHUNK_CHARS", "6000"))
CHUNK_OVERLAP_CHARS = int(os.environ.get("FACTLAYER_CHUNK_OVERLAP_CHARS", "400"))
LOW_YIELD_PAGE_CHAR_THRESHOLD = int(os.environ.get("FACTLAYER_LOW_YIELD_CHARS", "120"))
MAX_CANDIDATE_PAIRS_PER_FACT = int(os.environ.get("FACTLAYER_MAX_PAIRS_PER_FACT", "6"))
MIN_CANDIDATE_SIMILARITY = float(os.environ.get("FACTLAYER_MIN_SIMILARITY", "0.28"))

def resolve_api_key() -> str:
    for name in LLM_API_KEY_ENV_VARS:
        value = os.environ.get(name)
        if value:
            return value
    raise RuntimeError("No LLM API key found. Set OPENAI_API_KEY, GROQ_API_KEY, or AI_API_KEY.")
