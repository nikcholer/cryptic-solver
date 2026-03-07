from __future__ import annotations

from typing import Any

from app.models.puzzle import PuzzleClue
from app.runtime.schemas import (
    MechanicalResult,
    NextHintContext,
    NextHintRequest,
    SemanticJudgementContext,
    SemanticJudgementRequest,
)

SKILL_NAME = 'cryptic-crossword-solver'


def build_semantic_judgement_request(
    clue: PuzzleClue,
    analysis: Any,
    answer: str,
    mechanical_result: dict[str, object],
) -> SemanticJudgementRequest:
    return SemanticJudgementRequest(
        skill=SKILL_NAME,
        context=SemanticJudgementContext(
            clueId=clue.id,
            clue=clue.clue,
            enumeration=clue.enum,
            length=clue.length,
            proposedAnswer=answer,
            definitionText=analysis.definition_text,
            definitionSide=analysis.definition_side,
            clueType=analysis.clue_type,
            indicator=analysis.indicator,
            fodderText=analysis.fodder_text,
            solverCandidates=analysis.solver_candidates,
            mechanicalResult=MechanicalResult(
                result=_enum_value(mechanical_result.get('result')),
                reason=str(mechanical_result.get('reason', '')),
                confidence=_optional_float(mechanical_result.get('confidence')),
            ),
        ),
    )


def build_next_hint_request(
    clue: PuzzleClue,
    pattern: str,
    hint_level_already_shown: int,
    analysis: Any,
) -> NextHintRequest:
    return NextHintRequest(
        skill=SKILL_NAME,
        context=NextHintContext(
            clueId=clue.id,
            clue=clue.clue,
            enumeration=clue.enum,
            pattern=pattern,
            hintLevelAlreadyShown=hint_level_already_shown,
            clueType=analysis.clue_type,
            definitionText=analysis.definition_text,
            definitionSide=analysis.definition_side,
            indicator=analysis.indicator,
            fodderText=analysis.fodder_text,
            solverCandidates=analysis.solver_candidates,
        ),
    )


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, 'value') else str(value)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)