from __future__ import annotations

from pydantic import BaseModel, Field

from .common import HintKind, ValidationResult
from .puzzle import PuzzleDefinition
from .session import ClueState, EntryRecord, ValidationRecord


class CreateSessionRequest(BaseModel):
    puzzle_id: str = Field(alias="puzzleId")


class SelectClueRequest(BaseModel):
    clue_id: str = Field(alias="clueId")


class SubmitEntryRequest(BaseModel):
    clue_id: str = Field(alias="clueId")
    answer: str


class CheckAnswerRequest(BaseModel):
    answer: str


class NextHintRequest(BaseModel):
    mode: str = "incremental"


class ReanalyzeAffectedRequest(BaseModel):
    clue_ids: list[str] = Field(alias="clueIds")


class SessionSnapshot(BaseModel):
    selected_clue_id: str | None = Field(default=None, alias="selectedClueId")
    version: int
    cells: dict[str, str]
    entries: dict[str, EntryRecord]
    clue_states: dict[str, ClueState] = Field(alias="clueStates")


class PuzzleResponse(BaseModel):
    puzzle: PuzzleDefinition


class CreateSessionResponse(BaseModel):
    session_id: str = Field(alias="sessionId")
    puzzle: PuzzleDefinition
    session_state: SessionSnapshot = Field(alias="sessionState")


class SessionResponse(BaseModel):
    session_id: str = Field(alias="sessionId")
    puzzle: PuzzleDefinition
    session_state: SessionSnapshot = Field(alias="sessionState")


class SelectClueResponse(BaseModel):
    selected_clue_id: str = Field(alias="selectedClueId")


class SessionDelta(BaseModel):
    updated_cells: dict[str, str] = Field(alias="updatedCells")
    updated_patterns: dict[str, str] = Field(alias="updatedPatterns")
    affected_clues: list[str] = Field(alias="affectedClues")


class SubmitEntryResponse(BaseModel):
    clue_id: str = Field(alias="clueId")
    validation: ValidationRecord
    session_delta: SessionDelta = Field(alias="sessionDelta")


class CheckAnswerResponse(BaseModel):
    clue_id: str = Field(alias="clueId")
    result: ValidationResult
    reason: str


class NextHintResponse(BaseModel):
    clue_id: str = Field(alias="clueId")
    hint_level: int = Field(alias="hintLevel")
    kind: HintKind
    text: str
    updated_hint_history: list[dict[str, int | str]] = Field(alias="updatedHintHistory")


class ReanalyzedClueUpdate(BaseModel):
    clue_id: str = Field(alias="clueId")
    current_pattern: str = Field(alias="currentPattern")
    hint_availability: int = Field(alias="hintAvailability")


class ReanalyzeAffectedResponse(BaseModel):
    clue_updates: list[ReanalyzedClueUpdate] = Field(alias="clueUpdates")