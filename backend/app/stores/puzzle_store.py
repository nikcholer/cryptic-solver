from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Protocol


class PuzzleStore(Protocol):
    def list_puzzle_ids(self) -> list[str]: ...

    def get_puzzle_dir(self, puzzle_id: str) -> Path: ...

    def allocate_import_dir(self, stem: str) -> tuple[str, Path]: ...

    def cleanup_import_dir(self, puzzle_id: str) -> None: ...


class FilePuzzleStore:
    def __init__(self, repo_root: Path) -> None:
        self.base_dir = repo_root / 'samples'

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
        return puzzle_id, puzzle_dir

    def cleanup_import_dir(self, puzzle_id: str) -> None:
        shutil.rmtree(self.get_puzzle_dir(puzzle_id), ignore_errors=True)

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
        return FilePuzzleStore(repo_root)
    raise ValueError(f'Unsupported puzzle store: {store_kind}')
