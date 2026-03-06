from __future__ import annotations

from app.models.api import SessionSnapshot
from app.models.puzzle import PuzzleDefinition
from app.models.session import HintRecord, SessionState
from app.runtime.adapter import StubRuntimeAdapter
from app.services.grid_engine import GridEngine
from app.stores.session_store import SessionStore


class SessionService:
    def __init__(self, store: SessionStore, grid_engine: GridEngine, runtime: StubRuntimeAdapter) -> None:
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

    def submit_entry(self, puzzle: PuzzleDefinition, session_id: str, clue_id: str, answer: str):
        session = self.store.load(session_id)
        if clue_id not in puzzle.clues:
            raise KeyError(clue_id)
        pattern_before = session.clue_states[clue_id].current_pattern
        result = self.runtime.validate_answer(clue_id, puzzle.clues[clue_id].clue, answer, pattern_before)
        normalized = self.grid_engine.normalize_answer(answer)
        session.entries[clue_id] = self.grid_engine.make_entry_record(normalized, result["result"])
        updated_cells, affected_clues, changed_cells = self.grid_engine.apply_entry(puzzle, session, clue_id, normalized)
        patterns = self.grid_engine.update_session_from_cells(puzzle, session, updated_cells)
        self.grid_engine.attach_validation(session, clue_id, result["result"], result["reason"], result.get("confidence"))
        self.store.save(session)
        return session, affected_clues, patterns, changed_cells

    def check_answer(self, puzzle: PuzzleDefinition, session_id: str, clue_id: str, answer: str):
        session = self.store.load(session_id)
        if clue_id not in puzzle.clues:
            raise KeyError(clue_id)
        pattern_before = session.clue_states[clue_id].current_pattern
        return self.runtime.validate_answer(clue_id, puzzle.clues[clue_id].clue, answer, pattern_before)

    def next_hint(self, puzzle: PuzzleDefinition, session_id: str, clue_id: str):
        session = self.store.load(session_id)
        if clue_id not in puzzle.clues:
            raise KeyError(clue_id)
        clue_state = session.clue_states[clue_id]
        next_level = min(clue_state.hint_level_shown + 1, 5)
        result = self.runtime.next_hint(clue_id, puzzle.clues[clue_id].clue, clue_state.current_pattern, next_level)
        clue_state.hint_level_shown = next_level
        clue_state.hints.append(HintRecord(level=next_level, kind=result["kind"], text=result["text"]))
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
                    "clueId": clue_id,
                    "currentPattern": clue_state.current_pattern,
                    "hintAvailability": hint_availability,
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
        )