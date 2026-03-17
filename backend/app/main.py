from __future__ import annotations

import os
import logging
from pathlib import Path

from fastapi import FastAPI

from dotenv import load_dotenv

# Configure logging to show setup status
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env from repo root explicitly
repo_root = Path(__file__).resolve().parents[2]
dotenv_path = repo_root / '.env'
loaded = load_dotenv(dotenv_path=dotenv_path)

runtime_cmd = os.environ.get('CROSSWORD_RUNTIME_COMMAND', 'NOT_SET')
logger.info(f"Backend starting. Repo root: {repo_root}")
logger.info(f"Loading .env from {dotenv_path}: {'Success' if loaded else 'Failed or Not Found'}")
logger.info(f"Active CROSSWORD_RUNTIME_COMMAND: {runtime_cmd}")

from app.api.clues import router as clues_router
from app.api.imports import router as imports_router
from app.api.puzzles import router as puzzles_router
from app.api.sessions import router as sessions_router
from app.api.thesaurus import router as thesaurus_router

app = FastAPI(title="Cryptic Tutor Backend", version="0.1.0")
app.include_router(puzzles_router)
app.include_router(sessions_router)
app.include_router(clues_router)
app.include_router(imports_router)
app.include_router(thesaurus_router)


@app.get('/health')
def healthcheck():
    return {"status": "ok"}