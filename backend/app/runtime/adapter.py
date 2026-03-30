from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Protocol

from app.models.common import HintKind, ValidationResult
from app.models.puzzle import PuzzleClue, PuzzleDefinition
from app.models.session import SessionState
from app.runtime.payloads import build_next_hint_request, build_semantic_judgement_request
from app.runtime.schemas import HintPlanEntry, NextHintResponse, SemanticJudgementResponse

_WORD_RE = re.compile(r"[A-Za-z']+")

ANAGRAM_INDICATORS = [
    'adjusted',
    'arranged',
    'badly',
    'broken',
    'confused',
    'crazy',
    'drunk',
    'mixed',
    'rearranged',
    'revolutionary',
    'scrambled',
    'shattered',
    'wobbly',
    'wild',
]
HIDDEN_INDICATORS = [
    'buried in',
    'concealed in',
    'contained in',
    'found in',
    'held by',
    'hidden in',
    'inside',
    'within',
]
REVERSAL_INDICATORS = [
    'back',
    'reflected',
    'returning',
    'reversed',
]
CONTAINER_INDICATORS = [
    'about',
    'around',
    'boarding',
    'clutching',
    'defending',
    'holding',
    'in',
    'inside',
    'swallowing',
    'within',
]
CHARADE_LINKERS = ['with', 'after', 'before', 'beside', 'next to']
INITIALS_INDICATORS = [
    'for starters',
    'at first',
    'first off',
    'initially',
    'to start',
]


class RuntimeAdapter(Protocol):
    def next_hint(
        self,
        clue: PuzzleClue,
        pattern: str,
        next_level: int,
        puzzle: PuzzleDefinition | None = None,
        session: SessionState | None = None,
    ) -> dict[str, object]: ...

    def validate_answer(
        self,
        clue: PuzzleClue,
        proposed_answer: str,
        pattern_before: str,
        puzzle: PuzzleDefinition | None = None,
        session: SessionState | None = None,
        solver_justification: str | None = None,
    ) -> dict[str, object]: ...


class RuntimeGateway(Protocol):
    def invoke(self, payload: object) -> dict[str, object] | None: ...


class SemanticAdjudicator(Protocol):
    def adjudicate(
        self,
        puzzle: PuzzleDefinition,
        session: SessionState,
        clue: PuzzleClue,
        analysis: 'Analysis',
        answer: str,
        mechanical_result: dict[str, object],
        solver_justification: str | None = None,
    ) -> dict[str, object] | None: ...


@dataclass
class Analysis:
    clue_type: str
    indicator: str | None
    indicator_index: int | None
    definition_side: str
    definition_text: str
    fodder_text: str | None
    solver_candidates: list[str]


class CommandRuntimeGateway:
    def __init__(self, command: list[str], repo_root: Path) -> None:
        self.command = command
        self.repo_root = repo_root

    def invoke(self, payload: object) -> dict[str, object] | None:
        completed = subprocess.run(
            self.command,
            input=self._dump_payload(payload),
            capture_output=True,
            text=True,
            cwd=self.repo_root,
            check=False,
        )
        if completed.returncode != 0:
            logging.error(f"Runtime command failed with exit code {completed.returncode}:\nSTDERR: {completed.stderr}\nSTDOUT: {completed.stdout}")
            return None
        try:
            decoded = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            logging.error(f"Failed to parse runtime output as JSON. Error: {exc}\nOutput starts with: {completed.stdout[:200]}")
            return None
        if not isinstance(decoded, dict):
            logging.error(f"Runtime command returned JSON but not a dict: type {type(decoded)}")
            return None
        return decoded

    def _dump_payload(self, payload: object) -> str:
        if hasattr(payload, 'model_dump_json'):
            return payload.model_dump_json()
        return json.dumps(payload)


class GatewaySemanticAdjudicator:
    def __init__(self, gateway: RuntimeGateway) -> None:
        self.gateway = gateway

    def adjudicate(
        self,
        puzzle: PuzzleDefinition,
        session: SessionState,
        clue: PuzzleClue,
        analysis: Analysis,
        answer: str,
        mechanical_result: dict[str, object],
        solver_justification: str | None = None,
    ) -> dict[str, object] | None:
        payload = build_semantic_judgement_request(puzzle, session, clue, analysis, answer, mechanical_result, solver_justification)
        decoded = self.gateway.invoke(payload)
        if decoded is None:
            return None
        usage = _extract_usage(decoded)
        try:
            parsed = SemanticJudgementResponse.model_validate(decoded)
        except Exception:
            return None
        result = {
            'clueId': clue.id,
            'result': ValidationResult(parsed.result),
            'reason': parsed.reason,
            'confidence': parsed.confidence,
            'symbolicFollowup': parsed.symbolicFollowup,
        }
        if usage is not None:
            result['_usage'] = usage
        return result


class StubRuntimeAdapter:
    def next_hint(self, clue: PuzzleClue, pattern: str, next_level: int, puzzle: PuzzleDefinition | None = None, session: SessionState | None = None) -> dict[str, object]:
        hint_map = {
            1: (HintKind.CLUE_TYPE, 'This looks like a cryptic clue with standard wordplay.'),
            2: (HintKind.STRUCTURE, 'The definition is likely at one end of the clue.'),
            3: (HintKind.WORDPLAY_FOCUS, 'Look for indicator words and possible fodder.'),
            4: (HintKind.CANDIDATE_SPACE, f'Use the current pattern {pattern} to narrow candidates.'),
            5: (HintKind.ANSWER_REVEAL, 'Answer reveal is not available in the stub runtime.'),
        }
        return {
            'clueId': clue.id,
            'hints': [
                {'level': level, 'kind': kind, 'text': text}
                for level, (kind, text) in hint_map.items()
            ],
            'confidence': 0.25,
        }

    def validate_answer(
        self,
        clue: PuzzleClue,
        proposed_answer: str,
        pattern_before: str,
        puzzle: PuzzleDefinition | None = None,
        session: SessionState | None = None,
        solver_justification: str | None = None,
    ) -> dict[str, object]:
        answer = _normalize_answer(proposed_answer)
        if not answer:
            return _result(clue.id, ValidationResult.CONFLICT, 'Empty answer.', 0.0)
        if len(answer) != clue.answer_length:
            return _result(clue.id, ValidationResult.CONFLICT, f'Answer must be {clue.answer_length} letters long.', 0.95)
        if '.' in pattern_before and not _matches_pattern(answer, pattern_before):
            return _result(clue.id, ValidationResult.CONFLICT, 'Submitted answer conflicts with current checking letters.', 0.9)
        return _result(clue.id, ValidationResult.PLAUSIBLE, 'Fits length and current checking letters. Semantic validation is stubbed.', 0.35)


class HeuristicRuntimeAdapter:
    def __init__(
        self,
        repo_root: Path,
        semantic_adjudicator: SemanticAdjudicator | None = None,
        runtime_gateway: RuntimeGateway | None = None,
    ) -> None:
        self.repo_root = repo_root
        self.skills_dir = repo_root / 'cryptic_skills'
        self.words_path = self.skills_dir / 'words.txt'
        self.python_executable = Path(sys.executable)
        self.wordlist = self._load_wordlist(self.words_path)
        self.semantic_adjudicator = semantic_adjudicator
        self.runtime_gateway = runtime_gateway

    def next_hint(self, clue: PuzzleClue, pattern: str, next_level: int, puzzle: PuzzleDefinition | None = None, session: SessionState | None = None) -> dict[str, object]:
        analysis = self._analyze_clue(clue, pattern)
        runtime_result = self._runtime_next_hint(clue, pattern, next_level, analysis, puzzle, session)
        if runtime_result is not None:
            return runtime_result
        hints = []
        for level in range(1, 6):
            kind, text = self._hint_for_level(clue, pattern, analysis, level)
            hints.append({'level': level, 'kind': kind, 'text': text, 'source': 'heuristic'})
        return {
            'clueId': clue.id,
            'hints': hints,
            'confidence': self._confidence_for_hint(analysis, 2),
        }

    def validate_answer(
        self,
        clue: PuzzleClue,
        proposed_answer: str,
        pattern_before: str,
        puzzle: PuzzleDefinition | None = None,
        session: SessionState | None = None,
        solver_justification: str | None = None,
    ) -> dict[str, object]:
        answer = _normalize_answer(proposed_answer)
        if not answer:
            return _result(clue.id, ValidationResult.CONFLICT, 'Empty answer.', 0.0)
        if len(answer) != clue.answer_length:
            return _result(clue.id, ValidationResult.CONFLICT, f'Answer must be {clue.answer_length} letters long.', 0.98)
        if not _matches_pattern(answer, pattern_before):
            return _result(clue.id, ValidationResult.CONFLICT, 'Submitted answer conflicts with current checking letters.', 0.94)

        analysis = self._analyze_clue(clue, answer)
        if answer in analysis.solver_candidates:
            result = _result(clue.id, ValidationResult.CONFIRMED, self._confirmed_reason(analysis, answer), 0.93)
            return self._apply_semantic_judgement(clue, analysis, answer, result, puzzle, session, solver_justification)
        if analysis.solver_candidates and analysis.clue_type in {'anagram', 'hidden', 'reversal', 'initials'}:
            candidates = ', '.join(candidate.upper() for candidate in analysis.solver_candidates[:3])
            return _result(clue.id, ValidationResult.CONFLICT, f'Current wordplay analysis points elsewhere: {candidates}.', 0.78)
        if answer.lower() in self.wordlist:
            result = _result(clue.id, ValidationResult.PLAUSIBLE, 'Fits length and checking letters, but no strong local parse is confirmed yet.', 0.55)
            return self._apply_semantic_judgement(clue, analysis, answer, result, puzzle, session, solver_justification)
        phrase_words = _phrase_words_for_entry(clue, proposed_answer, answer)
        if len(phrase_words) > 1 and all(word.lower() in self.wordlist for word in phrase_words):
            display = ' + '.join(word.upper() for word in phrase_words)
            result = _result(clue.id, ValidationResult.PLAUSIBLE, f'Fits the grid and segments cleanly as {display}.', 0.58)
            return self._apply_semantic_judgement(clue, analysis, answer, result, puzzle, session, solver_justification)
        if self.semantic_adjudicator is not None:
            result = _result(clue.id, ValidationResult.PLAUSIBLE, 'Fits the grid, but local lexical checks are inconclusive.', 0.41)
            adjudicated = self._apply_semantic_judgement(clue, analysis, answer, result, puzzle, session, solver_justification)
            if adjudicated.get('result') != ValidationResult.CONFLICT:
                return adjudicated
        if _looks_like_proper_noun_clue(clue.clue):
            result = _result(clue.id, ValidationResult.PLAUSIBLE, 'Fits the grid; this clue may point to a proper noun or place name not covered by the local word list.', 0.43)
            return self._apply_semantic_judgement(clue, analysis, answer, result, puzzle, session, solver_justification)
        return _result(clue.id, ValidationResult.CONFLICT, 'Fits the grid, but it is not in the local crossword word list.', 0.81)

    def _runtime_next_hint(self, clue: PuzzleClue, pattern: str, next_level: int, analysis: Analysis, puzzle: PuzzleDefinition | None, session: SessionState | None) -> dict[str, object] | None:
        if self.runtime_gateway is None:
            return None
        if puzzle is None or session is None:
            return None
        payload = build_next_hint_request(puzzle, session, clue, pattern, next_level - 1, analysis)
        decoded = self.runtime_gateway.invoke(payload)
        if decoded is None:
            return None
        usage = _extract_usage(decoded)
        try:
            parsed = NextHintResponse.model_validate(decoded)
        except Exception:
            return None
        result = {
            'clueId': parsed.clueId,
            'hints': [
                {
                    'level': hint.level,
                    'kind': HintKind(hint.kind),
                    'text': hint.text,
                    'source': 'agent',
                }
                for hint in parsed.hints
            ],
            'confidence': parsed.confidence,
        }
        if usage is not None:
            result['_usage'] = usage
        return result

    def _apply_semantic_judgement(
        self,
        clue: PuzzleClue,
        analysis: Analysis,
        answer: str,
        mechanical_result: dict[str, object],
        puzzle: PuzzleDefinition | None,
        session: SessionState | None,
        solver_justification: str | None = None,
    ) -> dict[str, object]:
        if self.semantic_adjudicator is None:
            return mechanical_result
        if puzzle is None or session is None:
            return mechanical_result
        semantic_result = self.semantic_adjudicator.adjudicate(puzzle, session, clue, analysis, answer, mechanical_result, solver_justification)
        if not semantic_result:
            return mechanical_result
        symbolic_followup = semantic_result.get('symbolicFollowup')
        if symbolic_followup and semantic_result.get('result') == ValidationResult.CONFLICT and not analysis.solver_candidates and not analysis.fodder_text:
            semantic_result = dict(semantic_result)
            semantic_result['result'] = ValidationResult.PLAUSIBLE
            semantic_result['reason'] = f"{semantic_result.get('reason', '')} Suggested symbolic follow-up: {symbolic_followup}".strip()
        return semantic_result

    def _analyze_clue(self, clue: PuzzleClue, pattern: str) -> Analysis:
        words = _WORD_RE.findall(clue.clue.strip())
        clue_type, indicator, indicator_index = self._detect_clue_type(clue.clue.lower())
        definition_side = 'unknown'
        if indicator_index is not None:
            midpoint = max(len(words) - 1, 1) / 2
            definition_side = 'start' if indicator_index >= midpoint else 'end'
        definition_text = self._definition_text(words, definition_side)
        fodder_words = self._fodder_words(words, clue_type, indicator, indicator_index, definition_side)
        fodder_text = ' '.join(fodder_words).strip() or None
        solver_candidates = self._solver_candidates(clue, clue_type, pattern, fodder_words, indicator_index, words)
        return Analysis(clue_type, indicator, indicator_index, definition_side, definition_text, fodder_text, solver_candidates)

    def _detect_clue_type(self, clue_lower: str) -> tuple[str, str | None, int | None]:
        words = _WORD_RE.findall(clue_lower)
        multiword_positions = self._find_multiword_indicator_positions(words)
        for phrase in HIDDEN_INDICATORS:
            if phrase in multiword_positions:
                return 'hidden', phrase, multiword_positions[phrase]
        for phrase in INITIALS_INDICATORS:
            if phrase in multiword_positions:
                return 'initials', phrase, multiword_positions[phrase]
        for index, word in enumerate(words):
            if word in ANAGRAM_INDICATORS:
                return 'anagram', word, index
            if word in REVERSAL_INDICATORS:
                return 'reversal', word, index
            if word in CONTAINER_INDICATORS and len(words) <= 6:
                return 'container', word, index
        for phrase in CHARADE_LINKERS:
            if phrase in multiword_positions:
                return 'charade', phrase, multiword_positions[phrase]
        if len(words) <= 4:
            return 'double_definition', None, None
        return 'cryptic', None, None

    def _find_multiword_indicator_positions(self, words: list[str]) -> dict[str, int]:
        lowered_words = [word.lower() for word in words]
        positions: dict[str, int] = {}
        for phrase in HIDDEN_INDICATORS + CHARADE_LINKERS + INITIALS_INDICATORS:
            phrase_words = phrase.split()
            for index in range(len(lowered_words) - len(phrase_words) + 1):
                if lowered_words[index:index + len(phrase_words)] == phrase_words:
                    positions[phrase] = index
                    break
        return positions

    def _definition_text(self, words: list[str], definition_side: str) -> str:
        if not words:
            return ''
        if definition_side == 'start':
            return words[0]
        if definition_side == 'end':
            return words[-1]
        return f'{words[0]} / {words[-1]}'

    def _fodder_words(self, words: list[str], clue_type: str, indicator: str | None, indicator_index: int | None, definition_side: str) -> list[str]:
        if not words:
            return []
        if clue_type == 'anagram' and indicator_index is not None:
            if definition_side == 'start':
                return words[1:indicator_index]
            if definition_side == 'end':
                return words[indicator_index + 1:-1]
            return words[max(0, indicator_index - 2):indicator_index]
        if clue_type == 'reversal' and indicator_index is not None:
            if indicator_index > 0:
                return [words[indicator_index - 1]]
            if indicator_index + 1 < len(words):
                return [words[indicator_index + 1]]
        if clue_type == 'hidden' and indicator is not None:
            phrase_words = indicator.split()
            start = (indicator_index or 0) + len(phrase_words)
            if definition_side == 'start':
                return words[start:]
            if definition_side == 'end':
                return words[: indicator_index or 0]
            return words[start:]
        if clue_type == 'initials' and indicator is not None and indicator_index is not None:
            phrase_words = indicator.split()
            if definition_side == 'start':
                return words[2:indicator_index]
            if definition_side == 'end':
                return words[indicator_index + len(phrase_words):-1]
            return words[:indicator_index]
        return []

    def _solver_candidates(self, clue: PuzzleClue, clue_type: str, pattern: str, fodder_words: list[str], indicator_index: int | None, words: list[str]) -> list[str]:
        clean_pattern = _normalize_pattern(pattern, clue.answer_length)
        if clue_type == 'anagram' and fodder_words:
            fodder = ''.join(_normalize_answer(word) for word in fodder_words)
            if len(fodder) == clue.answer_length:
                result = self._run_solver('anagram.py', ['--fodder', fodder, '--pattern', clean_pattern])
                return [candidate.upper() for candidate in result.get('candidates', [])]
        if clue_type == 'hidden' and fodder_words:
            result = self._run_solver('hidden.py', ['--fodder', ' '.join(fodder_words), '--length', str(clue.answer_length), '--pattern', clean_pattern])
            return [candidate.upper() for candidate in result.get('candidates', [])]
        if clue_type == 'reversal' and fodder_words:
            fodder = ''.join(_normalize_answer(word) for word in fodder_words)
            if len(fodder) == clue.answer_length:
                result = self._run_solver('reversal.py', ['--fodder', fodder, '--pattern', clean_pattern])
                return [candidate.upper() for candidate in result.get('candidates', [])]
        if clue_type == 'container' and indicator_index is not None and 0 < indicator_index < len(words) - 1:
            outer = words[indicator_index - 1]
            inner = words[indicator_index + 1]
            result = self._run_solver('insertion.py', ['--outer', outer, '--fodder', inner, '--pattern', clean_pattern])
            return [candidate['candidate'].upper() for candidate in result.get('candidates', [])]
        if clue_type == 'initials':
            return self._initials_candidates(words, clean_pattern)
        if clue_type == 'charade' and len(words) >= 2:
            result = self._run_solver('charade.py', ['--components', words[0], words[-1], '--pattern', clean_pattern])
            return [candidate['candidate'].upper() for candidate in result.get('candidates', [])]
        return []

    def _initials_candidates(self, words: list[str], pattern: str) -> list[str]:
        target_length = len(pattern)
        candidates: list[str] = []
        for start in range(len(words)):
            for end in range(start + target_length, len(words) + 1):
                window = words[start:end]
                if len(window) != target_length:
                    continue
                initials = ''.join(word[0].upper() for word in window if word)
                if len(initials) != target_length:
                    continue
                if _matches_pattern(initials, pattern) and initials not in candidates:
                    candidates.append(initials)
        return candidates

    def _run_solver(self, script_name: str, args: list[str]) -> dict[str, object]:
        script_path = self.skills_dir / script_name
        completed = subprocess.run([str(self.python_executable), str(script_path), *args], capture_output=True, text=True, cwd=self.repo_root, check=False)
        if completed.returncode != 0:
            return {}
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError:
            return {}

    def _hint_for_level(self, clue: PuzzleClue, pattern: str, analysis: Analysis, level: int) -> tuple[HintKind, str]:
        if level == 1:
            return HintKind.CLUE_TYPE, self._clue_type_hint(analysis)
        if level == 2:
            return HintKind.STRUCTURE, self._structure_hint(analysis)
        if level == 3:
            return HintKind.WORDPLAY_FOCUS, self._wordplay_hint(analysis)
        if level == 4:
            return HintKind.CANDIDATE_SPACE, self._candidate_hint(pattern, analysis)
        return HintKind.ANSWER_REVEAL, self._reveal_hint(analysis)

    def _clue_type_hint(self, analysis: Analysis) -> str:
        if analysis.clue_type == 'anagram':
            return 'This looks like an anagram clue.'
        if analysis.clue_type == 'hidden':
            return 'This looks like a hidden-word clue.'
        if analysis.clue_type == 'reversal':
            return 'This looks like a reversal clue.'
        if analysis.clue_type == 'initials':
            return 'This looks like an initial-letters clue.'
        if analysis.clue_type == 'container':
            return 'This looks like a container or insertion clue.'
        if analysis.clue_type == 'double_definition':
            return 'This may be a double definition.'
        return 'This looks like a standard cryptic clue, but the wordplay type is not yet pinned down.'

    def _structure_hint(self, analysis: Analysis) -> str:
        if analysis.indicator and analysis.definition_side in {'start', 'end'}:
            edge = 'start' if analysis.definition_side == 'start' else 'end'
            return f"The definition is probably at the {edge}, and '{analysis.indicator}' looks like the indicator."
        if analysis.definition_side == 'unknown':
            return 'Try treating one end of the clue as the definition and the middle as wordplay.'
        return f"The definition is probably at the {analysis.definition_side} of the clue."

    def _wordplay_hint(self, analysis: Analysis) -> str:
        if analysis.clue_type == 'anagram' and analysis.fodder_text:
            return f"The fodder looks like '{analysis.fodder_text}', to be rearranged."
        if analysis.clue_type == 'hidden' and analysis.fodder_text:
            return f"Look for a contiguous {analysis.fodder_text!r} substring that matches the answer length."
        if analysis.clue_type == 'reversal' and analysis.fodder_text:
            return f"A short piece of fodder near the indicator may need reversing: '{analysis.fodder_text}'."
        if analysis.clue_type == 'initials' and analysis.fodder_text:
            return f"Try taking the initial letters of '{analysis.fodder_text}'."
        if analysis.clue_type == 'container':
            return 'Try placing one short element inside another rather than reading the clue straight through.'
        return 'Focus on possible indicator words, abbreviations, and where the definition begins or ends.'

    def _candidate_hint(self, pattern: str, analysis: Analysis) -> str:
        if analysis.solver_candidates:
            return f"Using the current pattern {pattern}, the strongest local candidates are: {', '.join(analysis.solver_candidates[:3])}."
        return f'No strong local candidates yet; use the current pattern {pattern} to narrow the field.'

    def _reveal_hint(self, analysis: Analysis) -> str:
        if len(analysis.solver_candidates) == 1:
            return f"The strongest answer here is {analysis.solver_candidates[0]}."
        if analysis.solver_candidates:
            return f"There are still multiple local candidates: {', '.join(analysis.solver_candidates[:3])}."
        return 'No confident answer reveal is available yet from the local tooling.'

    def _confidence_for_hint(self, analysis: Analysis, level: int) -> float:
        if analysis.clue_type in {'anagram', 'hidden', 'reversal', 'initials'}:
            return 0.85 if level >= 2 else 0.78
        if analysis.clue_type in {'container', 'charade', 'double_definition'}:
            return 0.6
        return 0.45

    def _confirmed_reason(self, analysis: Analysis, answer: str) -> str:
        if analysis.clue_type == 'anagram' and analysis.fodder_text and analysis.indicator:
            return f"Matches a strong anagram parse: '{analysis.fodder_text}' signalled by '{analysis.indicator}'."
        if analysis.clue_type == 'hidden' and analysis.fodder_text:
            return f"Can be read directly from the hidden-letter fodder '{analysis.fodder_text}'."
        if analysis.clue_type == 'reversal' and analysis.fodder_text:
            return f"Matches a reversal parse built from '{analysis.fodder_text}'."
        if analysis.clue_type == 'initials' and analysis.fodder_text and analysis.indicator:
            return f"Matches an initial-letters parse from '{analysis.fodder_text}', signalled by '{analysis.indicator}'."
        return f'{answer} fits the strongest local wordplay analysis for this clue.'

    def _load_wordlist(self, path: Path) -> set[str]:
        try:
            with path.open('r', encoding='utf-8') as handle:
                return {line.strip().lower() for line in handle if line.strip()}
        except FileNotFoundError:
            return set()


def build_runtime_adapter(repo_root: Path) -> RuntimeAdapter:
    mode = os.environ.get('CROSSWORD_RUNTIME_MODE', 'heuristic').strip().lower()
    if mode == 'stub':
        return StubRuntimeAdapter()
    runtime_gateway = build_runtime_gateway(repo_root)
    semantic_adjudicator = build_semantic_adjudicator(repo_root, runtime_gateway)
    return HeuristicRuntimeAdapter(repo_root, semantic_adjudicator=semantic_adjudicator, runtime_gateway=runtime_gateway)


def build_runtime_gateway(repo_root: Path) -> RuntimeGateway | None:
    command = os.environ.get('CROSSWORD_RUNTIME_COMMAND', '').strip()
    if not command:
        return None
    return CommandRuntimeGateway(shlex.split(command, posix=False), repo_root)


def build_semantic_adjudicator(repo_root: Path, runtime_gateway: RuntimeGateway | None) -> SemanticAdjudicator | None:
    command = os.environ.get('CROSSWORD_SEMANTIC_COMMAND', '').strip()
    if command:
        return GatewaySemanticAdjudicator(CommandRuntimeGateway(shlex.split(command, posix=False), repo_root))
    if runtime_gateway is not None:
        return GatewaySemanticAdjudicator(runtime_gateway)
    return None


def _looks_like_proper_noun_clue(clue_text: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", clue_text)
    capitalized = [word for word in words if word[:1].isupper()]
    return ',' in clue_text or len(capitalized) >= 3


def _phrase_words_for_entry(clue: PuzzleClue, raw_answer: str, normalized_answer: str) -> list[str]:
    explicit_words = [word for word in re.split(r"[^A-Za-z]+", raw_answer.upper()) if word]
    if len(explicit_words) > 1 and ''.join(explicit_words) == normalized_answer:
        return explicit_words
    segments = [int(value) for value in re.findall(r"\d+", clue.enum or '')]
    if len(segments) <= 1 or sum(segments) != len(normalized_answer):
        return []
    words: list[str] = []
    index = 0
    for length in segments:
        words.append(normalized_answer[index:index + length])
        index += length
    return words


def _normalize_answer(answer: str) -> str:
    return ''.join(char for char in answer.upper() if char.isalpha())


def _normalize_pattern(pattern: str, clue_length: int) -> str:
    cleaned = ''.join(char if char.isalpha() or char == '.' else '.' for char in pattern.upper())
    cleaned = cleaned[:clue_length]
    if len(cleaned) < clue_length:
        cleaned += '.' * (clue_length - len(cleaned))
    return cleaned


def _matches_pattern(answer: str, pattern: str) -> bool:
    if len(answer) < len(pattern):
        return False
    return all(expected == '.' or expected == actual for actual, expected in zip(answer, pattern))


def _result(clue_id: str, result: ValidationResult, reason: str, confidence: float | None) -> dict[str, object]:
    return {'clueId': clue_id, 'result': result, 'reason': reason, 'confidence': confidence}

def _extract_usage(decoded: dict[str, object]) -> dict[str, int] | None:
    usage = decoded.pop('_usage', None)
    if not isinstance(usage, dict):
        return None
    return {
        'input_tokens': int(usage.get('input_tokens', 0) or 0),
        'cached_input_tokens': int(usage.get('cached_input_tokens', 0) or 0),
        'output_tokens': int(usage.get('output_tokens', 0) or 0),
    }
