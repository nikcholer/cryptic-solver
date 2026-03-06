from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .common import ClueStatus, HintKind, ValidationResult


class HintRecord(BaseModel):
    level: int
    kind: HintKind
    text: str


class ValidationRecord(BaseModel):
    result: ValidationResult
    reason: str
    confidence: float | None = None


class ClueState(BaseModel):
    status: ClueStatus = ClueStatus.UNTOUCHED
    current_pattern: str
    hint_level_shown: int = 0
    hints: list[HintRecord] = Field(default_factory=list)
    validation: ValidationRecord | None = None


class EntryRecord(BaseModel):
    answer: str
    source: str = "user"
    status: ValidationResult
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionState(BaseModel):
    session_id: str
    puzzle_id: str
    selected_clue_id: str | None = None
    version: int = 0
    cells: dict[str, str] = Field(default_factory=dict)
    entries: dict[str, EntryRecord] = Field(default_factory=dict)
    clue_states: dict[str, ClueState] = Field(default_factory=dict)