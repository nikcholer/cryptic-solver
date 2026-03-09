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


class SymbolicAnalysis(BaseModel):
    clueType: str
    definitionText: str
    definitionSide: str
    indicator: str | None = None
    fodderText: str | None = None
    solverCandidates: list[str] = Field(default_factory=list)
    confidence: float | None = None
    notes: list[str] = Field(default_factory=list)


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
    symbolicAnalysis: SymbolicAnalysis
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
    symbolicAnalysis: SymbolicAnalysis
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
    symbolicFollowup: str | None = None




class HintPlanEntry(BaseModel):
    level: int
    kind: Literal['clue_type', 'structure', 'wordplay_focus', 'candidate_space', 'answer_reveal']
    text: str


class NextHintResponse(BaseModel):
    clueId: str
    hints: list[HintPlanEntry]
    confidence: float | None = None
