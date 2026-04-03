from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _cutoff_from_hours(ttl_hours: int) -> datetime:
    return _utc_now() - timedelta(hours=ttl_hours)


class PuzzleStore(Protocol):
    def list_puzzle_ids(self) -> list[str]: ...

    def get_puzzle_dir(self, puzzle_id: str) -> Path: ...

    def allocate_import_dir(self, stem: str) -> tuple[str, Path]: ...

    def finalize_import_dir(self, puzzle_id: str, puzzle_dir: Path) -> None: ...

    def cleanup_import_dir(self, puzzle_id: str) -> None: ...

    def cleanup_expired_imports(self, ttl_hours: int) -> int: ...


class FilePuzzleStore:
    def __init__(self, repo_root: Path, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or (repo_root / 'samples')

    def list_puzzle_ids(self) -> list[str]:
        if not self.base_dir.exists():
            return []
        puzzle_ids: list[str] = []
        for child in sorted(self.base_dir.iterdir(), key=lambda item: item.name):
            if not child.is_dir():
                continue
            if (child / 'grid_state.json').exists() and (child / 'clues.yaml').exists():
                puzzle_ids.append(child.name)
        return puzzle_ids

    def get_puzzle_dir(self, puzzle_id: str) -> Path:
        return self.base_dir / puzzle_id

    def allocate_import_dir(self, stem: str) -> tuple[str, Path]:
        puzzle_id = self._allocate_puzzle_id(stem)
        puzzle_dir = self.base_dir / puzzle_id
        puzzle_dir.mkdir(parents=True, exist_ok=False)
        metadata = {
            'kind': 'imported',
            'createdAt': _utc_now().isoformat(),
        }
        (puzzle_dir / '.cryptic-meta.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        return puzzle_id, puzzle_dir

    def finalize_import_dir(self, puzzle_id: str, puzzle_dir: Path) -> None:
        return None

    def cleanup_import_dir(self, puzzle_id: str) -> None:
        shutil.rmtree(self.get_puzzle_dir(puzzle_id), ignore_errors=True)

    def cleanup_expired_imports(self, ttl_hours: int) -> int:
        cutoff = _cutoff_from_hours(ttl_hours)
        removed = 0
        if not self.base_dir.exists():
            return removed
        for puzzle_dir in self.base_dir.iterdir():
            if not puzzle_dir.is_dir():
                continue
            metadata_path = puzzle_dir / '.cryptic-meta.json'
            if not metadata_path.exists():
                continue
            try:
                metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
                if metadata.get('kind') != 'imported':
                    continue
                created_at = datetime.fromisoformat(metadata['createdAt'])
            except Exception:
                continue
            if created_at < cutoff:
                shutil.rmtree(puzzle_dir, ignore_errors=True)
                removed += 1
        return removed

    def _allocate_puzzle_id(self, stem: str) -> str:
        base = re.sub(r'[^a-z0-9-]+', '-', stem.lower()).strip('-') or 'uploaded-puzzle'
        candidate = base
        suffix = 2
        while (self.base_dir / candidate).exists():
            candidate = f'{base}-{suffix}'
            suffix += 1
        return candidate


class SQLitePuzzleStore:
    def __init__(
        self,
        repo_root: Path,
        db_path: Path | None = None,
        bundled_dir: Path | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        self.repo_root = repo_root
        self.db_path = db_path or (repo_root / 'backend_data' / 'puzzles.sqlite3')
        self.bundled_dir = bundled_dir or (repo_root / 'samples')
        self.cache_dir = cache_dir or (repo_root / 'backend_data' / 'puzzle_cache')
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def list_puzzle_ids(self) -> list[str]:
        puzzle_ids = set()
        if self.bundled_dir.exists():
            for child in sorted(self.bundled_dir.iterdir(), key=lambda item: item.name):
                if not child.is_dir():
                    continue
                if (child / 'grid_state.json').exists() and (child / 'clues.yaml').exists():
                    puzzle_ids.add(child.name)
        with closing(sqlite3.connect(self.db_path)) as connection:
            rows = connection.execute('SELECT puzzle_id FROM imported_puzzles').fetchall()
        puzzle_ids.update(row[0] for row in rows)
        return sorted(puzzle_ids)

    def get_puzzle_dir(self, puzzle_id: str) -> Path:
        bundled_dir = self.bundled_dir / puzzle_id
        if bundled_dir.exists():
            return bundled_dir
        row = self._load_import_record(puzzle_id)
        if row is None:
            return bundled_dir
        puzzle_dir = self.cache_dir / puzzle_id
        puzzle_dir.mkdir(parents=True, exist_ok=True)
        (puzzle_dir / 'clues.yaml').write_text(row['clues_yaml'], encoding='utf-8')
        (puzzle_dir / 'grid_state.json').write_text(row['grid_state_json'], encoding='utf-8')
        if row['pdf_bytes'] is not None and row['source_filename']:
            (puzzle_dir / row['source_filename']).write_bytes(row['pdf_bytes'])
        metadata = {
            'kind': 'imported',
            'createdAt': row['created_at'],
        }
        (puzzle_dir / '.cryptic-meta.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        return puzzle_dir

    def allocate_import_dir(self, stem: str) -> tuple[str, Path]:
        puzzle_id = self._allocate_puzzle_id(stem)
        puzzle_dir = Path(tempfile.mkdtemp(prefix=f'{puzzle_id}-', dir=self.cache_dir))
        return puzzle_id, puzzle_dir

    def finalize_import_dir(self, puzzle_id: str, puzzle_dir: Path) -> None:
        clues_path = puzzle_dir / 'clues.yaml'
        grid_path = puzzle_dir / 'grid_state.json'
        if not clues_path.exists() or not grid_path.exists():
            raise FileNotFoundError('Imported puzzle artifacts are incomplete.')
        pdf_candidates = [path for path in puzzle_dir.glob('*.pdf')]
        pdf_bytes = pdf_candidates[0].read_bytes() if pdf_candidates else None
        source_filename = pdf_candidates[0].name if pdf_candidates else None
        created_at = _utc_now().isoformat()
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                '''
                INSERT INTO imported_puzzles (
                    puzzle_id,
                    created_at,
                    source_filename,
                    pdf_bytes,
                    clues_yaml,
                    grid_state_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    puzzle_id,
                    created_at,
                    source_filename,
                    pdf_bytes,
                    clues_path.read_bytes().decode('utf-8'),
                    grid_path.read_bytes().decode('utf-8'),
                ),
            )
            connection.commit()
        hydrated_dir = self.cache_dir / puzzle_id
        if hydrated_dir.exists():
            shutil.rmtree(hydrated_dir, ignore_errors=True)
        shutil.move(str(puzzle_dir), str(hydrated_dir))

    def cleanup_import_dir(self, puzzle_id: str) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute('DELETE FROM imported_puzzles WHERE puzzle_id = ?', (puzzle_id,))
            connection.commit()
        shutil.rmtree(self.cache_dir / puzzle_id, ignore_errors=True)
        for candidate in self.cache_dir.glob(f'{puzzle_id}-*'):
            if candidate.is_dir():
                shutil.rmtree(candidate, ignore_errors=True)

    def cleanup_expired_imports(self, ttl_hours: int) -> int:
        cutoff = _cutoff_from_hours(ttl_hours).isoformat()
        with closing(sqlite3.connect(self.db_path)) as connection:
            rows = connection.execute(
                'SELECT puzzle_id FROM imported_puzzles WHERE created_at < ?',
                (cutoff,),
            ).fetchall()
            if not rows:
                return 0
            connection.executemany(
                'DELETE FROM imported_puzzles WHERE puzzle_id = ?',
                rows,
            )
            connection.commit()
        for row in rows:
            puzzle_id = row[0]
            shutil.rmtree(self.cache_dir / puzzle_id, ignore_errors=True)
            for candidate in self.cache_dir.glob(f'{puzzle_id}-*'):
                if candidate.is_dir():
                    shutil.rmtree(candidate, ignore_errors=True)
        return len(rows)

    def _allocate_puzzle_id(self, stem: str) -> str:
        base = re.sub(r'[^a-z0-9-]+', '-', stem.lower()).strip('-') or 'uploaded-puzzle'
        existing = set(self.list_puzzle_ids())
        candidate = base
        suffix = 2
        while candidate in existing:
            candidate = f'{base}-{suffix}'
            suffix += 1
        return candidate

    def _initialize(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                '''
                CREATE TABLE IF NOT EXISTS imported_puzzles (
                    puzzle_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    source_filename TEXT,
                    pdf_bytes BLOB,
                    clues_yaml TEXT NOT NULL,
                    grid_state_json TEXT NOT NULL
                )
                '''
            )
            connection.commit()

    def _load_import_record(self, puzzle_id: str) -> sqlite3.Row | None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                '''
                SELECT puzzle_id, created_at, source_filename, pdf_bytes, clues_yaml, grid_state_json
                FROM imported_puzzles
                WHERE puzzle_id = ?
                ''',
                (puzzle_id,),
            ).fetchone()


def build_puzzle_store(repo_root: Path) -> PuzzleStore:
    store_kind = os.environ.get('CROSSWORD_PUZZLE_STORE', 'filesystem').strip().lower()
    if store_kind in {'filesystem', 'file'}:
        base_dir = os.environ.get('CROSSWORD_PUZZLE_FILESYSTEM_ROOT', '').strip()
        return FilePuzzleStore(repo_root, Path(base_dir) if base_dir else None)
    if store_kind in {'sqlite', 'sqlite3'}:
        db_path = os.environ.get('CROSSWORD_PUZZLE_SQLITE_PATH', '').strip()
        bundled_dir = os.environ.get('CROSSWORD_PUZZLE_FILESYSTEM_ROOT', '').strip()
        return SQLitePuzzleStore(
            repo_root,
            Path(db_path) if db_path else None,
            bundled_dir=Path(bundled_dir) if bundled_dir else None,
        )
    raise ValueError(f'Unsupported puzzle store: {store_kind}')
