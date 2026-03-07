from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / 'backend'
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.runtime.adapter import (  # noqa: E402
    CommandRuntimeGateway,
    GatewaySemanticAdjudicator,
    HeuristicRuntimeAdapter,
)
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
            HeuristicRuntimeAdapter(REPO_ROOT),
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
        updated_session, result = self.service.next_hint(self.puzzle, session.session_id, '4D')
        self.assertEqual(result['hintLevel'], 1)
        self.assertEqual(result['kind'].value, 'clue_type')
        self.assertIn('anagram', result['text'].lower())
        self.assertEqual(updated_session.clue_states['4D'].hint_level_shown, 1)
        self.assertEqual(len(updated_session.clue_states['4D'].hints), 1)

    def test_check_answer_conflict(self) -> None:
        session = self.service.create_session(self.puzzle)
        self.service.submit_entry(self.puzzle, session.session_id, '1A', 'SUPPOSE')
        result = self.service.check_answer(self.puzzle, session.session_id, '1D', 'ZZZZZZZ')
        self.assertEqual(result['result'].value, 'conflict')

    def test_anagram_validation_can_confirm(self) -> None:
        session = self.service.create_session(self.puzzle)
        result = self.service.check_answer(self.puzzle, session.session_id, '4D', 'ESTABLISH')
        self.assertEqual(result['result'].value, 'confirmed')
        self.assertIn('anagram', result['reason'].lower())

    def test_runtime_gateway_can_supply_next_hint(self) -> None:
        runtime_script = self._write_runtime_script()
        gateway = CommandRuntimeGateway([sys.executable, str(runtime_script)], REPO_ROOT)
        service = SessionService(
            SessionStore(self.repo_root / 'runtime-hint'),
            GridEngine(),
            HeuristicRuntimeAdapter(REPO_ROOT, runtime_gateway=gateway),
        )
        session = service.create_session(self.puzzle)
        _, result = service.next_hint(self.puzzle, session.session_id, '4D')
        self.assertEqual(result['kind'].value, 'structure')
        self.assertIn('runtime', result['text'].lower())

    def test_runtime_gateway_can_override_mechanical_confirmation(self) -> None:
        runtime_script = self._write_runtime_script()
        gateway = CommandRuntimeGateway([sys.executable, str(runtime_script)], REPO_ROOT)
        adapter = HeuristicRuntimeAdapter(
            REPO_ROOT,
            semantic_adjudicator=GatewaySemanticAdjudicator(gateway),
            runtime_gateway=gateway,
        )
        service = SessionService(SessionStore(self.repo_root / 'runtime-semantic'), GridEngine(), adapter)
        session = service.create_session(self.puzzle)
        result = service.check_answer(self.puzzle, session.session_id, '4D', 'ESTABLISH')
        self.assertEqual(result['result'].value, 'plausible')
        self.assertIn('runtime semantic review', result['reason'].lower())

    def test_codex_wrapper_translates_jsonl_output(self) -> None:
        fake_bin = self.repo_root / 'bin'
        fake_bin.mkdir()
        fake_codex = fake_bin / 'codex'
        fake_codex.write_text(
            textwrap.dedent(
                '''
                #!/usr/bin/env python3
                import json
                import sys

                args = sys.argv[1:]
                prompt = args[1] if len(args) > 1 else ''
                model = None
                reasoning = None
                for index, value in enumerate(args):
                    if value == '-m' and index + 1 < len(args):
                        model = args[index + 1]
                    if value == '-c' and index + 1 < len(args) and 'model_reasoning_effort=' in args[index + 1]:
                        reasoning = args[index + 1].split('=', 1)[1].strip('\"')
                if 'semantic_judgement' in prompt or 'proposedAnswer' in prompt:
                    payload = {'result': 'plausible', 'reason': f'Wrapper semantic response via {model}/{reasoning}.', 'confidence': 0.5}
                else:
                    payload = {'clueId': '4D', 'hintLevel': 2, 'kind': 'structure', 'text': f'Wrapper next hint via {model}/{reasoning}.', 'confidence': 0.6}
                print(json.dumps({'msg': {'type': 'task_complete', 'last_agent_message': json.dumps(payload)}}))
                '''
            ).strip(),
            encoding='utf-8',
        )
        os.chmod(fake_codex, 0o755)

        env = os.environ.copy()
        env['CODEX_RUNTIME_EXECUTABLE'] = f'{sys.executable} {fake_codex}'
        env['CODEX_MODEL_REASONER'] = 'test-reasoner-model'
        env['CODEX_REASONING_EFFORT_REASONER'] = 'low'
        request = {
            'skill': 'cryptic-crossword-solver',
            'operation': 'next_hint',
            'capability': 'reasoner',
            'response_format': 'json',
            'context': {
                'clueId': '4D',
                'clue': "Prove his table's wobbly",
                'enumeration': '(9)',
                'pattern': '.........',
                'hintLevelAlreadyShown': 1,
                'clueType': 'anagram',
                'definitionText': 'Prove',
                'definitionSide': 'start',
                'indicator': 'wobbly',
                'fodderText': "his table's",
                'solverCandidates': ['ESTABLISH'],
            },
        }
        completed = subprocess.run(
            [sys.executable, str(REPO_ROOT / 'backend' / 'runtime_wrappers' / 'codex_runtime.py')],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            env=env,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        decoded = json.loads(completed.stdout)
        self.assertEqual(decoded['kind'], 'structure')
        self.assertEqual(decoded['hintLevel'], 2)
        self.assertIn('test-reasoner-model', decoded['text'])
        self.assertIn('/low', decoded['text'])

    def test_loader_exposes_puzzle_definition(self) -> None:
        self.assertEqual(self.puzzle.puzzle_id, 'cryptic-2026-03-03')
        self.assertIn('1A', self.puzzle.clues)

    def _write_runtime_script(self) -> Path:
        script_path = self.repo_root / 'fake_runtime.py'
        script_path.write_text(
            textwrap.dedent(
                '''
                import json
                import sys

                payload = json.load(sys.stdin)
                operation = payload['operation']
                if operation == 'next_hint':
                    context = payload['context']
                    print(json.dumps({
                        'clueId': context['clueId'],
                        'hintLevel': context['hintLevelAlreadyShown'] + 1,
                        'kind': 'structure',
                        'text': 'Runtime says the definition is at the start.',
                        'confidence': 0.66,
                    }))
                elif operation == 'semantic_judgement':
                    print(json.dumps({
                        'result': 'plausible',
                        'reason': 'Runtime semantic review says the mechanical parse is good but definition fit needs confirmation.',
                        'confidence': 0.42,
                    }))
                else:
                    print(json.dumps({'result': 'conflict', 'reason': 'unsupported operation'}))
                '''
            ).strip(),
            encoding='utf-8',
        )
        return script_path


if __name__ == '__main__':
    unittest.main()