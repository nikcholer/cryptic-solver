from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.runtime.adapter import build_runtime_adapter
from app.services.grid_engine import GridEngine
from app.services.puzzle_import_service import PuzzleImportService
from app.services.puzzle_loader import PuzzleLoader
from app.services.session_service import SessionService
from app.services.thesaurus_service import ThesaurusService
from app.stores.session_store import SessionStore


@lru_cache(maxsize=1)
def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def get_puzzle_loader() -> PuzzleLoader:
    return PuzzleLoader(get_repo_root())


@lru_cache(maxsize=1)
def get_session_service() -> SessionService:
    repo_root = get_repo_root()
    return SessionService(SessionStore(repo_root), GridEngine(), build_runtime_adapter(repo_root))


@lru_cache(maxsize=1)
def get_puzzle_import_service() -> PuzzleImportService:
    return PuzzleImportService(get_repo_root())


@lru_cache(maxsize=1)
def get_thesaurus_service() -> ThesaurusService:
    return ThesaurusService(get_repo_root())
