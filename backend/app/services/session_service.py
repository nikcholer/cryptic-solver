from __future__ import annotations

from app.models.api import SessionSnapshot
from app.models.common import ClueStatus, ValidationResult
from app.models.puzzle import PuzzleDefinition
from app.models.session import HintRecord, SessionState
from app.runtime.adapter import RuntimeAdapter
from app.services.grid_engine import GridEngine
from app.stores.session_store import SessionStore


class SessionService:
    def __init__(self, store: SessionStore, grid_engine: GridEngine, runtime: RuntimeAdapter) -> None:
        self.store = store
        self.grid_engine = grid_engine
        self.runtime = runtime

    def create_session(self, puzzle: PuzzleDefinition) -> SessionState:
        clue_states = self.grid_engine.build_empty_clue_states(puzzle)
        session = self.store.create(puzzle.puzzle_id, clue_states)
        self.grid_engine.update_session_from_cells(puzzle, session, {})
        self.store.save(session)
        return session

    def get_session(self, session_id: str) -> SessionState:
        return self.store.load(session_id)

    def select_clue(self, session_id: str, clue_id: str) -> SessionState:
        session = self.store.load(session_id)
        if clue_id not in session.clue_states:
            raise KeyError(clue_id)
        session.selected_clue_id = clue_id
        self.store.save(session)
        return session

    def _effective_justification(self, session: SessionState, clue_id: str, justification: str | None) -> str | None:
        if justification and justification.strip():
            return justification.strip()
        clue_state = session.clue_states.get(clue_id)
        if not clue_state:
            return None
        reveal_hint = next(
            (
                hint.text.strip()
                for hint in clue_state.hints
                if hint.level == 5 and hint.kind.value == 'answer_reveal' and hint.text.strip()
            ),
            None,
        )
        if reveal_hint:
            return reveal_hint
        return None

    def _answer_was_revealed(self, session: SessionState, clue_id: str, answer: str) -> bool:
        clue_state = session.clue_states.get(clue_id)
        if not clue_state:
            return False
        normalized = self.grid_engine.normalize_answer(answer)
        for hint in clue_state.hints:
            if hint.level == 5 and hint.kind.value == 'answer_reveal':
                if normalized and normalized in self.grid_engine.normalize_answer(hint.text):
                    return True
        return False

    def _accumulate_runtime_usage(self, session: SessionState, result: dict[str, object]) -> None:
        usage = result.get('_usage')
        if not isinstance(usage, dict):
            return
        session.runtime_usage.input_tokens += int(usage.get('input_tokens', 0) or 0)
        session.runtime_usage.output_tokens += int(usage.get('output_tokens', 0) or 0)
        session.runtime_usage.cached_input_tokens += int(usage.get('cached_input_tokens', 0) or 0)
        session.runtime_usage.requests += 1

    def _propagate_linked_status(
        self,
        puzzle: PuzzleDefinition,
        session: SessionState,
        clue_id: str,
        result: ValidationResult,
        reason: str,
        confidence: float | None,
    ) -> None:
        clue = puzzle.clues[clue_id]
        linked_entries = clue.linked_entries or []
        if len(linked_entries) <= 1:
            return
        for linked_id in linked_entries[1:]:
            if linked_id not in session.clue_states:
                continue
            self.grid_engine.attach_validation(session, linked_id, result, reason, confidence)

    def submit_entry(self, puzzle: PuzzleDefinition, session_id: str, clue_id: str, answer: str, justification: str | None = None):
        session = self.store.load(session_id)
        if clue_id not in puzzle.clues:
            raise KeyError(clue_id)
        clue = puzzle.clues[clue_id]
        pattern_before = session.clue_states[clue_id].current_pattern
        effective_justification = self._effective_justification(session, clue_id, justification)
        result = self.runtime.validate_answer(clue, answer, pattern_before, puzzle, session, effective_justification)
        self._accumulate_runtime_usage(session, result)
        if result['result'].value == 'conflict' and self._answer_was_revealed(session, clue_id, answer):
            result = {
                'clueId': clue_id,
                'result': ValidationResult.PLAUSIBLE,
                'reason': 'This answer was already revealed in the hint ladder, so it remains plausible even though the final definition check is unconvinced.',
                'confidence': result.get('confidence'),
            }
        self.grid_engine.attach_validation(session, clue_id, result['result'], result['reason'], result.get('confidence'))
        if result['result'].value == 'conflict':
            self.store.save(session)
            return session, [], {clue_id: session.clue_states[clue_id].current_pattern}, {}

        normalized = self.grid_engine.normalize_answer(answer)
        session.entries[clue_id] = self.grid_engine.make_entry_record(normalized, result['result'])
        updated_cells, affected_clues, changed_cells = self.grid_engine.apply_entry(puzzle, session, clue_id, normalized)
        patterns = self.grid_engine.update_session_from_cells(puzzle, session, updated_cells)
        self._propagate_linked_status(puzzle, session, clue_id, result['result'], result['reason'], result.get('confidence'))
        self.store.save(session)
        return session, affected_clues, patterns, changed_cells

    def accept_entry(self, puzzle: PuzzleDefinition, session_id: str, clue_id: str, answer: str, justification: str | None = None):
        session = self.store.load(session_id)
        if clue_id not in puzzle.clues:
            raise KeyError(clue_id)
        clue = puzzle.clues[clue_id]
        normalized = self.grid_engine.normalize_answer(answer)
        if len(normalized) != clue.answer_length:
            raise ValueError('answer_length_mismatch')
        session.entries[clue_id] = self.grid_engine.make_entry_record(normalized, ValidationResult.PLAUSIBLE, source='user_override')
        updated_cells, affected_clues, changed_cells = self.grid_engine.apply_entry(puzzle, session, clue_id, normalized)
        patterns = self.grid_engine.update_session_from_cells(puzzle, session, updated_cells)
        reason = 'Accepted by user override.'
        if justification and justification.strip():
            reason = f'Accepted by user override: {justification.strip()}'
        self.grid_engine.attach_validation(session, clue_id, ValidationResult.PLAUSIBLE, reason, None)
        session.clue_states[clue_id].status = ClueStatus.FORCED
        clue = puzzle.clues[clue_id]
        for linked_id in clue.linked_entries or []:
            if linked_id != clue_id and linked_id in session.clue_states:
                session.clue_states[linked_id].status = ClueStatus.FORCED
                session.clue_states[linked_id].validation = session.clue_states[clue_id].validation
        self.store.save(session)
        return session, affected_clues, patterns, changed_cells

    def clear_entry(self, puzzle: PuzzleDefinition, session_id: str, clue_id: str):
        session = self.store.load(session_id)
        if clue_id not in puzzle.clues:
            raise KeyError(clue_id)
        if clue_id in session.entries:
            session.entries.pop(clue_id, None)
        clue_state = session.clue_states[clue_id]
        clue_state.validation = None
        previous_cells = dict(session.cells)
        rebuilt_cells = self.grid_engine.rebuild_cells_from_entries(puzzle, session)
        changed_cells = self.grid_engine.changed_cells(previous_cells, rebuilt_cells)
        patterns = self.grid_engine.update_session_from_cells(puzzle, session, rebuilt_cells)
        affected_clues = sorted({clue_id, *self.grid_engine.find_crossing_clues_for_clue(puzzle, clue_id)})
        self.store.save(session)
        return session, affected_clues, patterns, changed_cells

    def check_answer(self, puzzle: PuzzleDefinition, session_id: str, clue_id: str, answer: str, justification: str | None = None):
        session = self.store.load(session_id)
        if clue_id not in puzzle.clues:
            raise KeyError(clue_id)
        clue = puzzle.clues[clue_id]
        pattern_before = session.clue_states[clue_id].current_pattern
        effective_justification = self._effective_justification(session, clue_id, justification)
        result = self.runtime.validate_answer(clue, answer, pattern_before, puzzle, session, effective_justification)
        self._accumulate_runtime_usage(session, result)
        if result['result'].value == 'conflict' and self._answer_was_revealed(session, clue_id, answer):
            result = {
                'clueId': clue_id,
                'result': ValidationResult.PLAUSIBLE,
                'reason': 'This answer was already revealed in the hint ladder, so it remains plausible even though the final definition check is unconvinced.',
                'confidence': result.get('confidence'),
            }
        self.store.save(session)
        return result

    def next_hint(self, puzzle: PuzzleDefinition, session_id: str, clue_id: str):
        session = self.store.load(session_id)
        if clue_id not in puzzle.clues:
            raise KeyError(clue_id)
        clue = puzzle.clues[clue_id]
        clue_state = session.clue_states[clue_id]
        if clue_state.hint_level_shown >= 5 and clue_state.hints:
            last_hint = clue_state.hints[-1]
            return session, {
                'clueId': clue.id,
                'hintLevel': last_hint.level,
                'kind': last_hint.kind,
                'text': last_hint.text,
                'confidence': clue_state.validation.confidence if clue_state.validation else None,
            }

        next_level = min(clue_state.hint_level_shown + 1, 5)
        if len(clue_state.hint_plan) < 5:
            plan_result = self.runtime.next_hint(clue, clue_state.current_pattern, next_level, puzzle, session)
            self._accumulate_runtime_usage(session, plan_result)
            clue_state.hint_plan = [HintRecord(level=hint['level'], kind=hint['kind'], text=hint['text']) for hint in plan_result['hints']]
        clue_state.hint_level_shown = next_level
        revealed = [hint for hint in clue_state.hint_plan if hint.level <= next_level]
        clue_state.hints = revealed
        current_hint = next((hint for hint in revealed if hint.level == next_level), clue_state.hints[-1])
        result = {
            'clueId': clue.id,
            'hintLevel': current_hint.level,
            'kind': current_hint.kind,
            'text': current_hint.text,
            'confidence': None,
        }
        self.store.save(session)
        return session, result

    def reanalyze_affected(self, puzzle: PuzzleDefinition, session_id: str, clue_ids: list[str]):
        session = self.store.load(session_id)
        updates = []
        for clue_id in clue_ids:
            if clue_id not in session.clue_states:
                continue
            clue_state = session.clue_states[clue_id]
            hint_availability = 5 if clue_state.hint_level_shown < 5 else clue_state.hint_level_shown
            updates.append(
                {
                    'clueId': clue_id,
                    'currentPattern': clue_state.current_pattern,
                    'hintAvailability': hint_availability,
                }
            )
        return updates

    def snapshot(self, session: SessionState) -> SessionSnapshot:
        return SessionSnapshot(
            selectedClueId=session.selected_clue_id,
            version=session.version,
            cells=session.cells,
            entries=session.entries,
            clueStates=session.clue_states,
            runtimeUsage=session.runtime_usage,
        )
