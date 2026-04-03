from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from app.models.session import SessionState


class SessionStore(Protocol):
    def create(self, puzzle_id: str, clue_states: dict[str, object]) -> SessionState: ...

    def load(self, session_id: str) -> SessionState: ...

    def save(self, session: SessionState) -> None: ...


class FileSessionStore:
    def __init__(self, repo_root: Path, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or (repo_root / "backend_data" / "sessions")
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


class SQLiteSessionStore:
    def __init__(self, repo_root: Path, db_path: Path | None = None) -> None:
        self.db_path = db_path or (repo_root / 'backend_data' / 'sessions.sqlite3')
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def create(self, puzzle_id: str, clue_states: dict[str, object]) -> SessionState:
        session_id = f"sess_{uuid4().hex[:12]}"
        session = SessionState(session_id=session_id, puzzle_id=puzzle_id, clue_states=clue_states)
        self.save(session)
        return session

    def load(self, session_id: str) -> SessionState:
        with closing(sqlite3.connect(self.db_path)) as connection:
            row = connection.execute(
                'SELECT payload_json FROM sessions WHERE session_id = ?',
                (session_id,),
            ).fetchone()
        if row is None:
            raise FileNotFoundError(session_id)
        return SessionState.model_validate(json.loads(row[0]))

    def save(self, session: SessionState) -> None:
        session.version += 1
        payload_json = session.model_dump_json(indent=2)
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT INTO sessions (session_id, puzzle_id, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    puzzle_id = excluded.puzzle_id,
                    payload_json = excluded.payload_json
                """,
                (session.session_id, session.puzzle_id, payload_json),
            )
            connection.commit()

    def _initialize(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    puzzle_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.commit()


def build_session_store(repo_root: Path) -> SessionStore:
    store_kind = os.environ.get('CROSSWORD_SESSION_STORE', 'filesystem').strip().lower()
    if store_kind in {'filesystem', 'file'}:
        base_dir = os.environ.get('CROSSWORD_SESSION_FILESYSTEM_ROOT', '').strip()
        return FileSessionStore(repo_root, Path(base_dir) if base_dir else None)
    if store_kind in {'sqlite', 'sqlite3'}:
        db_path = os.environ.get('CROSSWORD_SESSION_SQLITE_PATH', '').strip()
        return SQLiteSessionStore(repo_root, Path(db_path) if db_path else None)
    raise ValueError(f'Unsupported session store: {store_kind}')
