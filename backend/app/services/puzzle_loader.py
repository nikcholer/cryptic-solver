from __future__ import annotations

import json
import re
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
                    enum=raw.get("enum"),
                    length=meta["length"],
                    answerLength=self._answer_length(raw.get("enum"), meta["length"]),
                    x=meta["x"],
                    y=meta["y"],
                    uncertain=meta.get("uncertain", False),
                    linked_entries=raw.get("linked_entries"),
                )
        return PuzzleDefinition(puzzle_id=puzzle_id, grid=grid, clues=clues)


    def list_puzzles(self) -> list[str]:
        if not self.samples_dir.exists():
            return []
        puzzle_ids: list[str] = []
        for child in sorted(self.samples_dir.iterdir(), key=lambda item: item.name):
            if not child.is_dir():
                continue
            if (child / "grid_state.json").exists() and (child / "clues.yaml").exists():
                puzzle_ids.append(child.name)
        return puzzle_ids

    def _answer_length(self, enum: str | None, fallback: int) -> int:
        if not enum:
            return fallback
        numbers = [int(value) for value in re.findall(r"\d+", enum)]
        return sum(numbers) if numbers else fallback
