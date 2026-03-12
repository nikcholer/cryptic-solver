from __future__ import annotations

from pydantic import BaseModel, Field

from .common import HintKind, ValidationResult
from .puzzle import PuzzleDefinition
from .session import ClueState, EntryRecord, RuntimeUsageRecord, ValidationRecord


class CreateSessionRequest(BaseModel):
    puzzle_id: str = Field(alias="puzzleId")


class SelectClueRequest(BaseModel):
    clue_id: str = Field(alias="clueId")


class SubmitEntryRequest(BaseModel):
    clue_id: str = Field(alias="clueId")
    answer: str
    justification: str | None = None


class CheckAnswerRequest(BaseModel):
    answer: str
    justification: str | None = None


class AcceptEntryRequest(BaseModel):
    answer: str
    justification: str | None = None


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
    runtime_usage: RuntimeUsageRecord = Field(alias="runtimeUsage")


class PuzzleSummary(BaseModel):
    puzzle_id: str = Field(alias="puzzleId")


class PuzzleListResponse(BaseModel):
    puzzles: list[PuzzleSummary]


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


class ClearEntryResponse(BaseModel):
    clue_id: str = Field(alias="clueId")
    session_delta: SessionDelta = Field(alias="sessionDelta")


class AcceptEntryResponse(BaseModel):
    clue_id: str = Field(alias="clueId")
    validation: ValidationRecord
    session_delta: SessionDelta = Field(alias="sessionDelta")


class CheckAnswerResponse(BaseModel):
    clue_id: str = Field(alias="clueId")
    result: ValidationResult
    reason: str
    symbolic_followup: str | None = Field(default=None, alias="symbolicFollowup")


class NextHintResponse(BaseModel):
    clue_id: str = Field(alias="clueId")
    hint_level: int = Field(alias="hintLevel")
    kind: HintKind
    text: str
    source: str = "agent"
    updated_hint_history: list[dict[str, int | str]] = Field(alias="updatedHintHistory")


class ReanalyzedClueUpdate(BaseModel):
    clue_id: str = Field(alias="clueId")
    current_pattern: str = Field(alias="currentPattern")
    hint_availability: int = Field(alias="hintAvailability")


class ReanalyzeAffectedResponse(BaseModel):
    clue_updates: list[ReanalyzedClueUpdate] = Field(alias="clueUpdates")

class ThesaurusCandidate(BaseModel):
    word: str
    pos: str | None = None
    length: int


class ThesaurusLookupResponse(BaseModel):
    term: str
    length: int | None = None
    candidates: list[ThesaurusCandidate]

