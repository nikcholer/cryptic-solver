from __future__ import annotations

from app.models.common import ClueStatus, Direction, ValidationResult
from app.models.puzzle import PuzzleClue, PuzzleDefinition
from app.models.session import ClueState, EntryRecord, SessionState, ValidationRecord


class GridEngine:
    def build_empty_clue_states(self, puzzle: PuzzleDefinition) -> dict[str, ClueState]:
        return {
            clue_id: ClueState(current_pattern=self.pattern_for_cells(puzzle, puzzle.clues[clue_id], {}))
            for clue_id in puzzle.clues
        }

    def apply_entry(
        self,
        puzzle: PuzzleDefinition,
        session: SessionState,
        clue_id: str,
        answer: str,
    ) -> tuple[dict[str, str], list[str], dict[str, str]]:
        clue = puzzle.clues[clue_id]
        normalized = self.normalize_answer(answer)
        updated_cells = dict(session.cells)
        changed_cells: dict[str, str] = {}
        affected = {clue_id}
        for index, (x, y) in enumerate(self.iter_clue_cells(puzzle, clue)):
            char = normalized[index] if index < len(normalized) else ""
            if not char:
                continue
            key = self.key(x, y)
            updated_cells[key] = char
            changed_cells[key] = char
            affected.update(self.find_crossing_clues(puzzle, x, y))
        return updated_cells, sorted(affected), changed_cells

    def rebuild_cells_from_entries(self, puzzle: PuzzleDefinition, session: SessionState) -> dict[str, str]:
        cells: dict[str, str] = {}
        for clue_id, entry in session.entries.items():
            clue = puzzle.clues.get(clue_id)
            if clue is None:
                continue
            for index, (x, y) in enumerate(self.iter_clue_cells(puzzle, clue)):
                if index >= len(entry.answer):
                    break
                cells[self.key(x, y)] = entry.answer[index]
        return cells

    def changed_cells(self, previous: dict[str, str], current: dict[str, str]) -> dict[str, str]:
        changed: dict[str, str] = {}
        for key in set(previous) | set(current):
            before = previous.get(key, '')
            after = current.get(key, '')
            if before != after:
                changed[key] = after
        return changed

    def update_session_from_cells(self, puzzle: PuzzleDefinition, session: SessionState, cells: dict[str, str]) -> dict[str, str]:
        patterns: dict[str, str] = {}
        for clue_id, clue in puzzle.clues.items():
            pattern = self.pattern_for_cells(puzzle, clue, cells)
            patterns[clue_id] = pattern
            clue_state = session.clue_states.setdefault(clue_id, ClueState(current_pattern=pattern))
            previous_pattern = clue_state.current_pattern
            clue_state.current_pattern = pattern
            if clue_id not in session.entries and previous_pattern != pattern:
                self._reset_pattern_sensitive_hints(clue_state)
            if clue_id in session.entries:
                entry = session.entries[clue_id]
                if entry.source == 'user_override':
                    clue_state.status = ClueStatus.FORCED
                else:
                    result = entry.status
                    clue_state.status = {
                        ValidationResult.CONFIRMED: ClueStatus.CONFIRMED,
                        ValidationResult.PLAUSIBLE: ClueStatus.PLAUSIBLE,
                        ValidationResult.CONFLICT: ClueStatus.CONFLICT,
                    }[result]
            elif pattern.strip('.'):
                clue_state.status = ClueStatus.IN_PROGRESS
            else:
                clue_state.status = ClueStatus.UNTOUCHED
        session.cells = cells
        return patterns

    def _reset_pattern_sensitive_hints(self, clue_state: ClueState) -> None:
        if clue_state.hint_level_shown <= 2:
            clue_state.hint_plan = []
            return
        clue_state.hints = [hint for hint in clue_state.hints if hint.level <= 2]
        clue_state.hint_level_shown = 2 if clue_state.hints else 0
        clue_state.hint_plan = []

    def make_entry_record(self, answer: str, result: ValidationResult | str, source: str = 'user') -> EntryRecord:
        normalized_result = result if isinstance(result, ValidationResult) else ValidationResult(result)
        return EntryRecord(answer=self.normalize_answer(answer), status=normalized_result, source=source)

    def attach_validation(
        self,
        session: SessionState,
        clue_id: str,
        result: ValidationResult,
        reason: str,
        confidence: float | None = None,
    ) -> None:
        clue_state = session.clue_states[clue_id]
        clue_state.validation = ValidationRecord(result=result, reason=reason, confidence=confidence)
        clue_state.status = {
            ValidationResult.CONFIRMED: ClueStatus.CONFIRMED,
            ValidationResult.PLAUSIBLE: ClueStatus.PLAUSIBLE,
            ValidationResult.CONFLICT: ClueStatus.CONFLICT,
        }[result]

    def pattern_for_cells(self, puzzle: PuzzleDefinition, clue: PuzzleClue, cells: dict[str, str]) -> str:
        chars: list[str] = []
        for x, y in self.iter_clue_cells(puzzle, clue):
            chars.append(cells.get(self.key(x, y), '.'))
        return ''.join(chars)

    def iter_clue_cells(self, puzzle: PuzzleDefinition, clue: PuzzleClue):
        if clue.linked_entries:
            for linked_id in clue.linked_entries:
                segment = puzzle.clues[linked_id]
                yield from self.iter_slot_cells(segment)
            return
        yield from self.iter_slot_cells(clue)

    def iter_slot_cells(self, clue: PuzzleClue):
        x = clue.x
        y = clue.y
        for _ in range(clue.length):
            yield x, y
            if clue.direction == Direction.ACROSS:
                x += 1
            else:
                y += 1

    def find_crossing_clues_for_clue(self, puzzle: PuzzleDefinition, clue_id: str) -> list[str]:
        clue = puzzle.clues[clue_id]
        matches: set[str] = set()
        for x, y in self.iter_clue_cells(puzzle, clue):
            matches.update(self.find_crossing_clues(puzzle, x, y))
        matches.discard(clue_id)
        return sorted(matches)

    def find_crossing_clues(self, puzzle: PuzzleDefinition, x: int, y: int) -> list[str]:
        matches: list[str] = []
        for clue_id, clue in puzzle.clues.items():
            for cell_x, cell_y in self.iter_clue_cells(puzzle, clue):
                if cell_x == x and cell_y == y:
                    matches.append(clue_id)
                    break
        return matches

    def normalize_answer(self, answer: str) -> str:
        return ''.join(ch for ch in answer.upper() if ch.isalpha())

    def key(self, x: int, y: int) -> str:
        return f"{x},{y}"
