from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from app.stores.puzzle_store import PuzzleStore


class PuzzleImportService:
    def __init__(self, repo_root: Path, store: PuzzleStore) -> None:
        self.repo_root = repo_root
        self.store = store
        self.python_executable = sys.executable
        self.clue_extractor = repo_root / "cryptic_skills" / "extract_clues_from_pdf_text.py"
        self.grid_extractor = repo_root / "cryptic_skills" / "extract_grid_state_from_pdf_vector.py"

    def import_pdf(self, filename: str, content: bytes, page: int = 1) -> str:
        puzzle_id, puzzle_dir = self.store.allocate_import_dir(Path(filename or "uploaded-puzzle.pdf").stem)
        pdf_path = puzzle_dir / f"{puzzle_id}.pdf"
        clues_path = puzzle_dir / "clues.yaml"
        grid_path = puzzle_dir / "grid_state.json"
        try:
            pdf_path.write_bytes(content)
            self._run([self.python_executable, str(self.clue_extractor), "--pdf", str(pdf_path), "--out", str(clues_path), "--page", str(page)])
            self._run([self.python_executable, str(self.grid_extractor), "--pdf", str(pdf_path), "--out", str(grid_path), "--page", str(page)])
        except Exception:
            self.store.cleanup_import_dir(puzzle_id)
            raise
        return puzzle_id

    def _run(self, command: list[str]) -> None:
        completed = subprocess.run(command, cwd=self.repo_root, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            stdout = completed.stdout.strip()
            detail = stderr or stdout or "import command failed"
            raise RuntimeError(detail)
