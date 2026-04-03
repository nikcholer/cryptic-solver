from __future__ import annotations

import json
import os
import re
import shutil
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


def build_puzzle_store(repo_root: Path) -> PuzzleStore:
    store_kind = os.environ.get('CROSSWORD_PUZZLE_STORE', 'filesystem').strip().lower()
    if store_kind in {'filesystem', 'file'}:
        base_dir = os.environ.get('CROSSWORD_PUZZLE_FILESYSTEM_ROOT', '').strip()
        return FilePuzzleStore(repo_root, Path(base_dir) if base_dir else None)
    raise ValueError(f'Unsupported puzzle store: {store_kind}')
