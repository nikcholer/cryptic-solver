from __future__ import annotations

import re
from typing import Any

from app.models.puzzle import PuzzleClue, PuzzleDefinition
from app.models.session import SessionState
from app.runtime.schemas import (
    MechanicalResult,
    NextHintContext,
    NextHintRequest,
    ReferencedClueContext,
    SemanticJudgementContext,
    SemanticJudgementRequest,
    SymbolicAnalysis,
)

SKILL_NAME = 'cryptic-crossword-solver'
REFERENCE_RE = re.compile(r"\b(\d+)\s*(Across|Down)\b", re.IGNORECASE)


def build_semantic_judgement_request(
    puzzle: PuzzleDefinition,
    session: SessionState,
    clue: PuzzleClue,
    analysis: Any,
    answer: str,
    mechanical_result: dict[str, object],
    solver_justification: str | None = None,
) -> SemanticJudgementRequest:
    linked_entries, referenced_clues = build_reference_context(puzzle, session, clue)
    return SemanticJudgementRequest(
        skill=SKILL_NAME,
        context=SemanticJudgementContext(
            clueId=clue.id,
            clue=clue.clue,
            enumeration=clue.enum,
            length=clue.answer_length,
            proposedAnswer=answer,
            definitionText=analysis.definition_text,
            definitionSide=analysis.definition_side,
            clueType=analysis.clue_type,
            indicator=analysis.indicator,
            fodderText=analysis.fodder_text,
            solverCandidates=analysis.solver_candidates,
            symbolicAnalysis=build_symbolic_analysis(analysis),
            linkedEntries=linked_entries,
            referencedClues=referenced_clues,
            solverJustification=solver_justification or None,
            mechanicalResult=MechanicalResult(
                result=_enum_value(mechanical_result.get('result')),
                reason=str(mechanical_result.get('reason', '')),
                confidence=_optional_float(mechanical_result.get('confidence')),
            ),
        ),
    )


def build_next_hint_request(
    puzzle: PuzzleDefinition,
    session: SessionState,
    clue: PuzzleClue,
    pattern: str,
    hint_level_already_shown: int,
    analysis: Any,
) -> NextHintRequest:
    linked_entries, referenced_clues = build_reference_context(puzzle, session, clue)
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
            symbolicAnalysis=build_symbolic_analysis(analysis),
            linkedEntries=linked_entries,
            referencedClues=referenced_clues,
        ),
    )


def build_reference_context(
    puzzle: PuzzleDefinition,
    session: SessionState,
    clue: PuzzleClue,
) -> tuple[list[str], list[ReferencedClueContext]]:
    linked_entries = list(clue.linked_entries or [])
    referenced: list[ReferencedClueContext] = []
    seen: set[str] = set()
    for number, direction in REFERENCE_RE.findall(clue.clue):
        clue_id = f"{int(number)}{'A' if direction.lower() == 'across' else 'D'}"
        if clue_id in seen or clue_id == clue.id:
            continue
        seen.add(clue_id)
        if clue_id not in puzzle.clues:
            continue
        referenced_clue = puzzle.clues[clue_id]
        entry = session.entries.get(clue_id)
        referenced.append(
            ReferencedClueContext(
                clueId=clue_id,
                clue=referenced_clue.clue,
                enumeration=referenced_clue.enum,
                answer=entry.answer if entry else None,
            )
        )
    return linked_entries, referenced


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, 'value') else str(value)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def build_symbolic_analysis(analysis: Any) -> SymbolicAnalysis:
    notes: list[str] = []
    if analysis.indicator:
        notes.append(f"Indicator candidate: {analysis.indicator}")
    if analysis.fodder_text:
        notes.append(f"Fodder candidate: {analysis.fodder_text}")
    if analysis.solver_candidates:
        notes.append(f"Local candidates: {', '.join(analysis.solver_candidates[:3])}")
    confidence = 0.35
    if analysis.clue_type in {'anagram', 'hidden', 'reversal'}:
        confidence = 0.8
    elif analysis.clue_type in {'container', 'charade', 'double_definition'}:
        confidence = 0.6
    return SymbolicAnalysis(
        clueType=analysis.clue_type,
        definitionText=analysis.definition_text,
        definitionSide=analysis.definition_side,
        indicator=analysis.indicator,
        fodderText=analysis.fodder_text,
        solverCandidates=list(analysis.solver_candidates),
        confidence=confidence,
        notes=notes,
    )
