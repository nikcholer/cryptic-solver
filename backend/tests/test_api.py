from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.runtime.adapter import StubRuntimeAdapter  # noqa: E402
from app.services.grid_engine import GridEngine  # noqa: E402
from app.services.puzzle_loader import PuzzleLoader  # noqa: E402
from app.services.session_service import SessionService  # noqa: E402
from app.stores.session_store import SessionStore  # noqa: E402


class BackendServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        self.loader = PuzzleLoader(REPO_ROOT)
        self.puzzle = self.loader.load_puzzle('cryptic-2026-03-03')
        self.service = SessionService(
            SessionStore(self.repo_root),
            GridEngine(),
            StubRuntimeAdapter(),
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_session(self) -> None:
        session = self.service.create_session(self.puzzle)
        self.assertTrue(session.session_id.startswith('sess_'))
        self.assertEqual(session.puzzle_id, 'cryptic-2026-03-03')
        self.assertIn('1A', session.clue_states)

    def test_select_clue(self) -> None:
        session = self.service.create_session(self.puzzle)
        updated = self.service.select_clue(session.session_id, '1A')
        self.assertEqual(updated.selected_clue_id, '1A')

    def test_submit_entry_updates_patterns(self) -> None:
        session = self.service.create_session(self.puzzle)
        updated_session, affected, patterns, changed = self.service.submit_entry(
            self.puzzle,
            session.session_id,
            '1A',
            'SUPPOSE',
        )
        self.assertEqual(updated_session.clue_states['1A'].validation.result.value, 'plausible')
        self.assertEqual(patterns['1A'], 'SUPPOSE')
        self.assertEqual(changed['0,0'], 'S')
        self.assertIn('1D', affected)
        self.assertEqual(patterns['1D'], 'S......')

    def test_next_hint_increments_history(self) -> None:
        session = self.service.create_session(self.puzzle)
        updated_session, result = self.service.next_hint(self.puzzle, session.session_id, '1A')
        self.assertEqual(result['hintLevel'], 1)
        self.assertEqual(result['kind'].value, 'clue_type')
        self.assertEqual(updated_session.clue_states['1A'].hint_level_shown, 1)
        self.assertEqual(len(updated_session.clue_states['1A'].hints), 1)

    def test_check_answer_conflict(self) -> None:
        session = self.service.create_session(self.puzzle)
        self.service.submit_entry(self.puzzle, session.session_id, '1A', 'SUPPOSE')
        result = self.service.check_answer(self.puzzle, session.session_id, '1D', 'ZZZZZZZ')
        self.assertEqual(result['result'].value, 'conflict')

    def test_loader_exposes_puzzle_definition(self) -> None:
        self.assertEqual(self.puzzle.puzzle_id, 'cryptic-2026-03-03')
        self.assertIn('1A', self.puzzle.clues)


if __name__ == '__main__':
    unittest.main()