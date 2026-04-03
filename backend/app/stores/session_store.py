from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from app.models.session import SessionState


class SessionStore(Protocol):
    def create(self, puzzle_id: str, clue_states: dict[str, object]) -> SessionState: ...

    def load(self, session_id: str) -> SessionState: ...

    def save(self, session: SessionState) -> None: ...


class FileSessionStore:
    def __init__(self, repo_root: Path) -> None:
        self.base_dir = repo_root / "backend_data" / "sessions"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create(self, puzzle_id: str, clue_states: dict[str, object]) -> SessionState:
        session_id = f"sess_{uuid4().hex[:12]}"
        session = SessionState(session_id=session_id, puzzle_id=puzzle_id, clue_states=clue_states)
        self.save(session)
        return session

    def load(self, session_id: str) -> SessionState:
        path = self._path(session_id)
        if not path.exists():
            raise FileNotFoundError(session_id)
        return SessionState.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save(self, session: SessionState) -> None:
        path = self._path(session.session_id)
        session.version += 1
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(session.model_dump_json(indent=2), encoding="utf-8")

    def _path(self, session_id: str) -> Path:
        return self.base_dir / session_id / "session.json"


def build_session_store(repo_root: Path) -> SessionStore:
    store_kind = os.environ.get('CROSSWORD_SESSION_STORE', 'filesystem').strip().lower()
    if store_kind in {'filesystem', 'file'}:
        return FileSessionStore(repo_root)
    raise ValueError(f'Unsupported session store: {store_kind}')
