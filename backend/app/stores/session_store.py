from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from app.models.session import SessionState


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _cutoff_from_hours(ttl_hours: int) -> datetime:
    return _utc_now() - timedelta(hours=ttl_hours)


class SessionStore(Protocol):
    def create(self, puzzle_id: str, clue_states: dict[str, object]) -> SessionState: ...

    def load(self, session_id: str) -> SessionState: ...

    def save(self, session: SessionState) -> None: ...

    def cleanup_expired(self, ttl_hours: int) -> int: ...


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
        now = _utc_now()
        if session.version == 0 and session.created_at > now:
            session.created_at = now
        session.updated_at = now
        session.version += 1
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(session.model_dump_json(indent=2), encoding="utf-8")

    def cleanup_expired(self, ttl_hours: int) -> int:
        cutoff = _cutoff_from_hours(ttl_hours)
        removed = 0
        if not self.base_dir.exists():
            return removed
        for session_dir in self.base_dir.iterdir():
            session_path = session_dir / 'session.json'
            if not session_path.exists():
                continue
            try:
                session = SessionState.model_validate(json.loads(session_path.read_text(encoding='utf-8')))
            except Exception:
                continue
            if session.updated_at < cutoff:
                for child in session_dir.iterdir():
                    child.unlink(missing_ok=True)
                session_dir.rmdir()
                removed += 1
        return removed

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
        now = _utc_now()
        if session.version == 0 and session.created_at > now:
            session.created_at = now
        session.updated_at = now
        session.version += 1
        payload_json = session.model_dump_json(indent=2)
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT INTO sessions (session_id, puzzle_id, payload_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    puzzle_id = excluded.puzzle_id,
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (session.session_id, session.puzzle_id, payload_json, session.updated_at.isoformat()),
            )
            connection.commit()

    def cleanup_expired(self, ttl_hours: int) -> int:
        cutoff = _cutoff_from_hours(ttl_hours).isoformat()
        with closing(sqlite3.connect(self.db_path)) as connection:
            cursor = connection.execute('DELETE FROM sessions WHERE updated_at < ?', (cutoff,))
            connection.commit()
            return cursor.rowcount or 0

    def _initialize(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    puzzle_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(sessions)").fetchall()
            }
            if 'updated_at' not in columns:
                connection.execute("ALTER TABLE sessions ADD COLUMN updated_at TEXT")
                connection.execute("UPDATE sessions SET updated_at = ? WHERE updated_at IS NULL", (_utc_now().isoformat(),))
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
