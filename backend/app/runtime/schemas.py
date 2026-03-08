from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CapabilityRole = Literal['lite', 'reasoner', 'vision']
RuntimeOperation = Literal['next_hint', 'semantic_judgement', 'validate_answer']


class ReferencedClueContext(BaseModel):
    clueId: str
    clue: str
    enumeration: str | None = None
    answer: str | None = None


class MechanicalResult(BaseModel):
    result: Literal['confirmed', 'plausible', 'conflict']
    reason: str
    confidence: float | None = None


class SemanticJudgementContext(BaseModel):
    clueId: str
    clue: str
    enumeration: str | None = None
    length: int
    proposedAnswer: str
    definitionText: str
    definitionSide: str
    clueType: str
    indicator: str | None = None
    fodderText: str | None = None
    solverCandidates: list[str]
    linkedEntries: list[str] = Field(default_factory=list)
    referencedClues: list[ReferencedClueContext] = Field(default_factory=list)
    solverJustification: str | None = None
    mechanicalResult: MechanicalResult


class NextHintContext(BaseModel):
    clueId: str
    clue: str
    enumeration: str | None = None
    pattern: str
    hintLevelAlreadyShown: int
    clueType: str
    definitionText: str
    definitionSide: str
    indicator: str | None = None
    fodderText: str | None = None
    solverCandidates: list[str]
    linkedEntries: list[str] = Field(default_factory=list)
    referencedClues: list[ReferencedClueContext] = Field(default_factory=list)


class RuntimeRequest(BaseModel):
    skill: str
    operation: RuntimeOperation
    capability: CapabilityRole
    response_format: Literal['json'] = 'json'
    context: dict[str, object]


class SemanticJudgementRequest(BaseModel):
    skill: str
    operation: Literal['semantic_judgement'] = 'semantic_judgement'
    capability: CapabilityRole = 'lite'
    response_format: Literal['json'] = 'json'
    context: SemanticJudgementContext


class NextHintRequest(BaseModel):
    skill: str
    operation: Literal['next_hint'] = 'next_hint'
    capability: CapabilityRole = 'reasoner'
    response_format: Literal['json'] = 'json'
    context: NextHintContext


class SemanticJudgementResponse(BaseModel):
    result: Literal['confirmed', 'plausible', 'conflict']
    reason: str
    confidence: float | None = None


class NextHintResponse(BaseModel):
    clueId: str
    hintLevel: int
    kind: Literal['clue_type', 'structure', 'wordplay_focus', 'candidate_space', 'answer_reveal']
    text: str
    confidence: float | None = None
