from __future__ import annotations

from pydantic import BaseModel, Field

from .common import Direction


class PuzzleClueMetadata(BaseModel):
    direction: Direction
    length: int
    uncertain: bool = False
    x: int
    y: int


class PuzzleClue(BaseModel):
    id: str
    direction: Direction
    clue: str
    enum: str | None = Field(default=None, alias="enum")
    length: int
    answer_length: int = Field(alias="answerLength")
    x: int
    y: int
    uncertain: bool = False
    linked_entries: list[str] | None = None


class PuzzleGrid(BaseModel):
    width: int
    height: int
    clues: dict[str, PuzzleClueMetadata]


class PuzzleDefinition(BaseModel):
    puzzle_id: str
    grid: PuzzleGrid
    clues: dict[str, PuzzleClue]
