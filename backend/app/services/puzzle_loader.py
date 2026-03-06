from __future__ import annotations

import json
from pathlib import Path

import yaml

from app.models.puzzle import PuzzleClue, PuzzleDefinition, PuzzleGrid


class PuzzleLoader:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.samples_dir = repo_root / "samples"

    def load_puzzle(self, puzzle_id: str) -> PuzzleDefinition:
        puzzle_dir = self.samples_dir / puzzle_id
        if not puzzle_dir.exists():
            raise FileNotFoundError(f"Unknown puzzle_id: {puzzle_id}")

        grid_data = json.loads((puzzle_dir / "grid_state.json").read_text(encoding="utf-8"))
        clue_data = yaml.safe_load((puzzle_dir / "clues.yaml").read_text(encoding="utf-8"))

        grid = PuzzleGrid(width=grid_data["width"], height=grid_data["height"], clues=grid_data["clues"])
        clues: dict[str, PuzzleClue] = {}
        for group in ("across", "down"):
            for clue_id, raw in clue_data[group].items():
                meta = grid_data["clues"][clue_id]
                clues[clue_id] = PuzzleClue(
                    id=clue_id,
                    direction=meta["direction"],
                    clue=raw["clue"],
                    enum=raw["enum"],
                    length=meta["length"],
                    x=meta["x"],
                    y=meta["y"],
                    uncertain=meta.get("uncertain", False),
                )
        return PuzzleDefinition(puzzle_id=puzzle_id, grid=grid, clues=clues)