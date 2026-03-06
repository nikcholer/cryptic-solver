from __future__ import annotations

from enum import Enum


class Direction(str, Enum):
    ACROSS = "Across"
    DOWN = "Down"


class ClueStatus(str, Enum):
    UNTOUCHED = "untouched"
    IN_PROGRESS = "in_progress"
    PLAUSIBLE = "plausible"
    CONFIRMED = "confirmed"
    CONFLICT = "conflict"


class ValidationResult(str, Enum):
    CONFIRMED = "confirmed"
    PLAUSIBLE = "plausible"
    CONFLICT = "conflict"


class HintKind(str, Enum):
    CLUE_TYPE = "clue_type"
    STRUCTURE = "structure"
    WORDPLAY_FOCUS = "wordplay_focus"
    CANDIDATE_SPACE = "candidate_space"
    ANSWER_REVEAL = "answer_reveal"