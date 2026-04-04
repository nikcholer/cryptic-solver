from __future__ import annotations

from pathlib import Path

from app.stores.puzzle_store import PuzzleStore
from cryptic_skills.extract_clues_from_pdf_text import extract_clues_from_pdf, write_clues_yaml
from cryptic_skills.extract_grid_state_from_pdf_vector import extract_grid_state_from_pdf, write_grid_state_json


class PuzzleImportService:
    def __init__(self, repo_root: Path, store: PuzzleStore) -> None:
        self.repo_root = repo_root
        self.store = store

    def import_pdf(self, filename: str, content: bytes, page: int = 1) -> str:
        puzzle_id, puzzle_dir = self.store.allocate_import_dir(Path(filename or "uploaded-puzzle.pdf").stem)
        pdf_path = puzzle_dir / f"{puzzle_id}.pdf"
        clues_path = puzzle_dir / "clues.yaml"
        grid_path = puzzle_dir / "grid_state.json"
        try:
            pdf_path.write_bytes(content)
            clues_payload = extract_clues_from_pdf(pdf_path, page)
            write_clues_yaml(clues_payload, clues_path)
            grid_payload = extract_grid_state_from_pdf(pdf_path, page)
            write_grid_state_json(grid_payload, grid_path)
            self.store.finalize_import_dir(puzzle_id, puzzle_dir)
        except Exception:
            self.store.cleanup_import_dir(puzzle_id)
            raise
        return puzzle_id
