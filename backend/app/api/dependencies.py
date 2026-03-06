from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.runtime.adapter import StubRuntimeAdapter
from app.services.grid_engine import GridEngine
from app.services.puzzle_loader import PuzzleLoader
from app.services.session_service import SessionService
from app.stores.session_store import SessionStore


@lru_cache(maxsize=1)
def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def get_puzzle_loader() -> PuzzleLoader:
    return PuzzleLoader(get_repo_root())


@lru_cache(maxsize=1)
def get_session_service() -> SessionService:
    return SessionService(SessionStore(get_repo_root()), GridEngine(), StubRuntimeAdapter())