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

from app.runtime.payloads import build_next_hint_request  # noqa: E402
from app.runtime.adapter import (  # noqa: E402
    CommandRuntimeGateway,
    GatewaySemanticAdjudicator,
    HeuristicRuntimeAdapter,
    StubRuntimeAdapter,
)
from app.services.grid_engine import GridEngine  # noqa: E402
from app.services.puzzle_loader import PuzzleLoader  # noqa: E402
from app.services.session_service import SessionService  # noqa: E402
from app.stores.session_store import FileSessionStore, build_session_store  # noqa: E402
from app.models.session import HintRecord  # noqa: E402
from app.models.common import ValidationResult  # noqa: E402
from app.services.thesaurus_service import ThesaurusService  # noqa: E402


class BackendServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        self.loader = PuzzleLoader(REPO_ROOT)
        self.puzzle = self.loader.load_puzzle('cryptic-2026-03-03')
        self.service = SessionService(
            FileSessionStore(self.repo_root),
            GridEngine(),
            HeuristicRuntimeAdapter(REPO_ROOT),
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_build_session_store_defaults_to_filesystem(self) -> None:
        store = build_session_store(self.repo_root)
        self.assertIsInstance(store, FileSessionStore)

    def test_build_session_store_rejects_unknown_backend(self) -> None:
        previous = os.environ.get('CROSSWORD_SESSION_STORE')
        os.environ['CROSSWORD_SESSION_STORE'] = 'redis'
        try:
            with self.assertRaises(ValueError):
                build_session_store(self.repo_root)
        finally:
            if previous is None:
                os.environ.pop('CROSSWORD_SESSION_STORE', None)
            else:
                os.environ['CROSSWORD_SESSION_STORE'] = previous

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

    def test_pattern_change_resets_hints_above_level_two_for_unsolved_clues(self) -> None:
        session = self.service.create_session(self.puzzle)
        for _ in range(4):
            session, _ = self.service.next_hint(self.puzzle, session.session_id, '1D')
        self.assertEqual(session.clue_states['1D'].hint_level_shown, 4)
        self.assertEqual(len(session.clue_states['1D'].hints), 4)

        updated_session, _, _, _ = self.service.submit_entry(
            self.puzzle,
            session.session_id,
            '1A',
            'SUPPOSE',
        )
        self.assertEqual(updated_session.clue_states['1D'].current_pattern, 'S......')
        self.assertEqual(updated_session.clue_states['1D'].hint_level_shown, 2)
        self.assertEqual([hint.level for hint in updated_session.clue_states['1D'].hints], [1, 2])

    def test_revealed_answer_is_not_rejected_as_conflict(self) -> None:
        class RejectingAdapter(StubRuntimeAdapter):
            def validate_answer(self, clue, proposed_answer, pattern_before, puzzle=None, session=None, solver_justification=None):
                return {
                    'clueId': clue.id,
                    'result': ValidationResult.CONFLICT,
                    'reason': 'semantic reject',
                    'confidence': 0.2,
                }

        service = SessionService(FileSessionStore(self.repo_root / 'revealed-answer'), GridEngine(), RejectingAdapter())
        session = service.create_session(self.puzzle)
        session.clue_states['4D'].hints.append(HintRecord(level=5, kind='answer_reveal', text="ESTABLISH. It comes from his table's wobbly."))
        session.clue_states['4D'].hint_level_shown = 5
        service.store.save(session)

        result = service.check_answer(self.puzzle, session.session_id, '4D', 'ESTABLISH')
        self.assertEqual(result['result'].value, 'plausible')
        self.assertIn('already revealed', result['reason'].lower())

    def test_level_five_hint_is_used_as_fallback_justification(self) -> None:
        captured: dict[str, str | None] = {}

        class CapturingAdapter(StubRuntimeAdapter):
            def validate_answer(self, clue, proposed_answer, pattern_before, puzzle=None, session=None, solver_justification=None):
                captured['justification'] = solver_justification
                return super().validate_answer(clue, proposed_answer, pattern_before, puzzle, session, solver_justification)

        service = SessionService(FileSessionStore(self.repo_root / 'fallback-justification'), GridEngine(), CapturingAdapter())
        session = service.create_session(self.puzzle)
        session.clue_states['4D'].hints.append(
            HintRecord(level=5, kind='answer_reveal', text="ESTABLISH. It comes from his table's wobbly.")
        )
        session.clue_states['4D'].hint_level_shown = 5
        service.store.save(session)

        service.check_answer(self.puzzle, session.session_id, '4D', 'ESTABLISH')
        self.assertIn('ESTABLISH', captured['justification'] or '')

    def test_level_five_hint_is_terminal(self) -> None:
        session = self.service.create_session(self.puzzle)
        for _ in range(5):
            session, result = self.service.next_hint(self.puzzle, session.session_id, '4D')
        self.assertEqual(result['hintLevel'], 5)
        self.assertEqual(len(session.clue_states['4D'].hints), 5)

        repeated_session, repeated_result = self.service.next_hint(self.puzzle, session.session_id, '4D')
        self.assertEqual(repeated_result['hintLevel'], 5)
        self.assertEqual(len(repeated_session.clue_states['4D'].hints), 5)
        self.assertEqual(repeated_result['text'], repeated_session.clue_states['4D'].hints[-1].text)

    def test_runtime_usage_accumulates_on_hint_and_check(self) -> None:
        runtime_script = self._write_runtime_script()
        gateway = CommandRuntimeGateway([sys.executable, str(runtime_script)], REPO_ROOT)
        service = SessionService(
            FileSessionStore(self.repo_root / 'runtime-usage'),
            GridEngine(),
            HeuristicRuntimeAdapter(REPO_ROOT, semantic_adjudicator=GatewaySemanticAdjudicator(gateway), runtime_gateway=gateway),
        )
        session = service.create_session(self.puzzle)
        session, _ = service.next_hint(self.puzzle, session.session_id, '4D')
        self.assertEqual(session.runtime_usage.input_tokens, 120)
        self.assertEqual(session.runtime_usage.cached_input_tokens, 30)
        self.assertEqual(session.runtime_usage.output_tokens, 12)
        self.assertEqual(session.runtime_usage.requests, 1)

        service.check_answer(self.puzzle, session.session_id, '4D', 'ESTABLISH')
        reloaded = service.get_session(session.session_id)
        self.assertEqual(reloaded.runtime_usage.input_tokens, 220)
        self.assertEqual(reloaded.runtime_usage.cached_input_tokens, 50)
        self.assertEqual(reloaded.runtime_usage.output_tokens, 20)
        self.assertEqual(reloaded.runtime_usage.requests, 2)

    def test_next_hint_increments_history(self) -> None:
        session = self.service.create_session(self.puzzle)
        updated_session, result = self.service.next_hint(self.puzzle, session.session_id, '4D')
        self.assertEqual(result['hintLevel'], 1)
        self.assertEqual(result['kind'].value, 'clue_type')
        self.assertIn('anagram', result['text'].lower())
        self.assertEqual(updated_session.clue_states['4D'].hint_level_shown, 1)
        self.assertEqual(len(updated_session.clue_states['4D'].hints), 1)

    def test_accept_entry_marks_clue_forced(self) -> None:
        session = self.service.create_session(self.puzzle)
        accepted_session, _, patterns, _ = self.service.accept_entry(
            self.puzzle,
            session.session_id,
            '1A',
            'SUPPOSE',
            'I want to keep this for now.',
        )
        self.assertEqual(accepted_session.clue_states['1A'].status.value, 'forced')
        self.assertEqual(accepted_session.clue_states['1A'].validation.reason, 'Accepted by user override: I want to keep this for now.')
        self.assertEqual(patterns['1A'], 'SUPPOSE')

    def test_clear_entry_rebuilds_grid_from_remaining_answers(self) -> None:
        session = self.service.create_session(self.puzzle)
        session, _, _, _ = self.service.submit_entry(self.puzzle, session.session_id, '1A', 'SUPPOSE')
        session, _, _, _ = self.service.submit_entry(self.puzzle, session.session_id, '1D', 'SANDALS')
        cleared_session, affected, patterns, changed = self.service.clear_entry(self.puzzle, session.session_id, '1A')
        self.assertNotIn('1A', cleared_session.entries)
        self.assertEqual(cleared_session.clue_states['1A'].validation, None)
        self.assertEqual(patterns['1A'], 'S......')
        self.assertEqual(patterns['1D'], 'SANDALS')
        self.assertIn('1D', affected)
        self.assertIn('1A', affected)
        self.assertEqual(changed['1,0'], '')

    def test_conflicting_submission_does_not_update_grid(self) -> None:
        session = self.service.create_session(self.puzzle)
        updated_session, _, patterns, _ = self.service.submit_entry(
            self.puzzle,
            session.session_id,
            '1A',
            'SUPPOSE',
        )
        self.assertEqual(patterns['1A'], 'SUPPOSE')
        conflicted_session, affected, patterns, changed = self.service.submit_entry(
            self.puzzle,
            updated_session.session_id,
            '1A',
            'ZZZZZZZ',
        )
        self.assertEqual(conflicted_session.clue_states['1A'].validation.result.value, 'conflict')
        self.assertEqual(conflicted_session.clue_states['1A'].current_pattern, 'SUPPOSE')
        self.assertEqual(conflicted_session.entries['1A'].answer, 'SUPPOSE')
        self.assertEqual(affected, [])
        self.assertEqual(changed, {})
        self.assertEqual(patterns['1A'], 'SUPPOSE')

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

    def test_initial_letters_clue_can_confirm(self) -> None:
        puzzle = self.loader.load_puzzle('prize-cryptic-85080')
        adapter = HeuristicRuntimeAdapter(REPO_ROOT)
        analysis = adapter._analyze_clue(puzzle.clues['25D'], 'WHEN')
        self.assertEqual(analysis.clue_type, 'initials')
        self.assertEqual(analysis.indicator, 'for starters')
        self.assertIn('WHEN', analysis.solver_candidates)
        result = adapter.validate_answer(puzzle.clues['25D'], 'WHEN', 'WHEN')
        self.assertEqual(result['result'].value, 'confirmed')
        self.assertIn('initial-letters parse', result['reason'])

    def test_indicator_lists_cover_recent_missed_cases(self) -> None:
        puzzle = self.loader.load_puzzle('prize-cryptic-85080')
        adapter = HeuristicRuntimeAdapter(REPO_ROOT)
        anagram = adapter._analyze_clue(puzzle.clues['17A'], '.' * puzzle.clues['17A'].answer_length)
        container = adapter._analyze_clue(puzzle.clues['19A'], '.' * puzzle.clues['19A'].answer_length)
        self.assertEqual(anagram.clue_type, 'anagram')
        self.assertEqual(anagram.indicator, 'revolutionary')
        self.assertEqual(container.clue_type, 'container')
        self.assertEqual(container.indicator, 'defending')


    def test_proper_noun_answer_can_be_plausible_without_wordlist_hit(self) -> None:
        puzzle = self.loader.load_puzzle('prize-cryptic-83730')
        clue = puzzle.clues['9D']
        adapter = HeuristicRuntimeAdapter(REPO_ROOT)
        result = adapter.validate_answer(clue, 'LUND', 'LUND')
        self.assertEqual(result['result'].value, 'plausible')
        self.assertIn('proper noun', result['reason'].lower())

    def test_multiword_enum_uses_segmented_word_check(self) -> None:
        puzzle = self.loader.load_puzzle('prize-cryptic-83730')
        clue = puzzle.clues['10A']
        adapter = HeuristicRuntimeAdapter(REPO_ROOT)
        joined = adapter.validate_answer(clue, 'REDGUARDS', '.' * clue.answer_length)
        spaced = adapter.validate_answer(clue, 'RED GUARDS', '.' * clue.answer_length)
        self.assertEqual(joined['result'].value, 'plausible')
        self.assertEqual(spaced['result'].value, 'plausible')
        self.assertIn('RED + GUARDS', joined['reason'])

    def test_composite_clue_propagates_status_to_linked_entries(self) -> None:
        puzzle = self.loader.load_puzzle('prize-cryptic-83730')
        service = SessionService(
            FileSessionStore(self.repo_root / 'composite-status'),
            GridEngine(),
            StubRuntimeAdapter(),
        )
        session = service.create_session(puzzle)
        updated_session, _, _, _ = service.submit_entry(
            puzzle,
            session.session_id,
            '26A',
            'ABCDEFGHIJKLMNOPQRST',
        )
        self.assertEqual(updated_session.clue_states['26A'].status.value, 'plausible')
        self.assertEqual(updated_session.clue_states['13A'].status.value, 'plausible')
        self.assertEqual(updated_session.clue_states['21D'].status.value, 'plausible')

    def test_composite_clue_spans_linked_entries(self) -> None:
        puzzle = self.loader.load_puzzle('prize-cryptic-83730')
        service = SessionService(
            FileSessionStore(self.repo_root / 'composite'),
            GridEngine(),
            StubRuntimeAdapter(),
        )
        session = service.create_session(puzzle)
        self.assertEqual(session.clue_states['26A'].current_pattern, '.' * 20)
        updated_session, _, patterns, changed = service.submit_entry(
            puzzle,
            session.session_id,
            '26A',
            'ABCDEFGHIJKLMNOPQRST',
        )
        self.assertEqual(patterns['26A'], 'ABCDEFGHIJKLMNOPQRST')
        self.assertEqual(patterns['13A'], 'FGHIJKLMN')
        self.assertEqual(patterns['21D'], 'OPQRST')
        self.assertEqual(changed['0,12'], 'A')
        self.assertEqual(changed['6,4'], 'F')
        self.assertEqual(changed['6,9'], 'O')
        self.assertEqual(updated_session.entries['26A'].answer, 'ABCDEFGHIJKLMNOPQRST')

    def test_runtime_gateway_can_supply_next_hint(self) -> None:
        runtime_script = self._write_runtime_script()
        gateway = CommandRuntimeGateway([sys.executable, str(runtime_script)], REPO_ROOT)
        service = SessionService(
            FileSessionStore(self.repo_root / 'runtime-hint'),
            GridEngine(),
            HeuristicRuntimeAdapter(REPO_ROOT, runtime_gateway=gateway),
        )
        session = service.create_session(self.puzzle)
        _, result = service.next_hint(self.puzzle, session.session_id, '4D')
        self.assertEqual(result['kind'].value, 'clue_type')
        self.assertIn('runtime', result['text'].lower())

    def test_runtime_symbolic_followup_downgrades_hard_conflict(self) -> None:
        class FollowupAdjudicator:
            def adjudicate(self, puzzle, session, clue, analysis, answer, mechanical_result, solver_justification=None):
                return {
                    'clueId': clue.id,
                    'result': ValidationResult.CONFLICT,
                    'reason': 'Definition fit is uncertain without a better mechanical read.',
                    'confidence': 0.4,
                    'symbolicFollowup': 'Try inserting KE into flower names.',
                }

        puzzle = self.loader.load_puzzle('prize-cryptic-85080')
        adapter = HeuristicRuntimeAdapter(REPO_ROOT, semantic_adjudicator=FollowupAdjudicator())
        service = SessionService(FileSessionStore(self.repo_root / 'symbolic-followup'), GridEngine(), adapter)
        session = service.create_session(puzzle)
        result = service.check_answer(puzzle, session.session_id, '6D', 'LIKELY')
        self.assertEqual(result['result'].value, 'plausible')
        self.assertIn('Suggested symbolic follow-up', result['reason'])
        self.assertEqual(result['symbolicFollowup'], 'Try inserting KE into flower names.')

        updated_session, _, _, _ = service.submit_entry(puzzle, session.session_id, '6D', 'LIKELY')
        self.assertEqual(updated_session.clue_states['6D'].validation.symbolic_followup, 'Try inserting KE into flower names.')

    def test_runtime_gateway_can_override_mechanical_confirmation(self) -> None:
        runtime_script = self._write_runtime_script()
        gateway = CommandRuntimeGateway([sys.executable, str(runtime_script)], REPO_ROOT)
        adapter = HeuristicRuntimeAdapter(
            REPO_ROOT,
            semantic_adjudicator=GatewaySemanticAdjudicator(gateway),
            runtime_gateway=gateway,
        )
        service = SessionService(FileSessionStore(self.repo_root / 'runtime-semantic'), GridEngine(), adapter)
        session = service.create_session(self.puzzle)
        result = service.check_answer(self.puzzle, session.session_id, '4D', 'ESTABLISH')
        self.assertEqual(result['result'].value, 'plausible')
        self.assertIn('runtime semantic review', result['reason'].lower())

    def test_reference_context_includes_linked_entries_and_solved_references(self) -> None:
        puzzle = self.loader.load_puzzle('prize-cryptic-83730')
        service = SessionService(
            FileSessionStore(self.repo_root / 'reference-context'),
            GridEngine(),
            StubRuntimeAdapter(),
        )
        session = service.create_session(puzzle)
        session.entries['19A'] = service.grid_engine.make_entry_record('RICK', 'confirmed')
        session.entries['9D'] = service.grid_engine.make_entry_record('LUND', 'confirmed')
        service.store.save(session)
        updated = service.get_session(session.session_id)
        adapter = HeuristicRuntimeAdapter(REPO_ROOT)
        clue = puzzle.clues['26A']
        analysis = adapter._analyze_clue(clue, updated.clue_states['26A'].current_pattern)
        request = build_next_hint_request(
            puzzle,
            updated,
            clue,
            updated.clue_states['26A'].current_pattern,
            updated.clue_states['26A'].hint_level_shown,
            analysis,
        )
        self.assertEqual(request.context.linkedEntries, ['26A', '13A', '21D'])
        referenced = {item.clueId: item for item in request.context.referencedClues}
        self.assertIn('19A', referenced)
        self.assertIn('9D', referenced)
        self.assertEqual(referenced['19A'].answer, 'RICK')
        self.assertEqual(referenced['9D'].answer, 'LUND')

    def test_runtime_payload_includes_symbolic_analysis(self) -> None:
        puzzle = self.loader.load_puzzle('prize-cryptic-85080')
        service = SessionService(
            FileSessionStore(self.repo_root / 'symbolic-payload'),
            GridEngine(),
            StubRuntimeAdapter(),
        )
        session = service.create_session(puzzle)
        adapter = HeuristicRuntimeAdapter(REPO_ROOT)
        clue = puzzle.clues['17A']
        analysis = adapter._analyze_clue(clue, session.clue_states['17A'].current_pattern)
        request = build_next_hint_request(
            puzzle,
            session,
            clue,
            session.clue_states['17A'].current_pattern,
            session.clue_states['17A'].hint_level_shown,
            analysis,
        )
        self.assertEqual(request.context.symbolicAnalysis.clueType, 'anagram')
        self.assertEqual(request.context.symbolicAnalysis.indicator, 'revolutionary')
        self.assertGreater(request.context.symbolicAnalysis.confidence or 0, 0.7)

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
                    payload = {
                        'clueId': '4D',
                        'hints': [
                            {'level': 1, 'kind': 'clue_type', 'text': f'Wrapper level 1 via {model}/{reasoning}.'},
                            {'level': 2, 'kind': 'structure', 'text': f'Wrapper next hint via {model}/{reasoning}.'},
                            {'level': 3, 'kind': 'wordplay_focus', 'text': 'Wrapper level 3.'},
                            {'level': 4, 'kind': 'candidate_space', 'text': 'Wrapper level 4.'},
                            {'level': 5, 'kind': 'answer_reveal', 'text': 'Wrapper level 5.'},
                        ],
                        'confidence': 0.6
                    }
                print(json.dumps({'msg': {'type': 'task_complete', 'last_agent_message': json.dumps(payload)}}))
                print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 321, 'cached_input_tokens': 45, 'output_tokens': 67}}))
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
        self.assertEqual(decoded['hints'][1]['kind'], 'structure')
        self.assertEqual(decoded['hints'][1]['level'], 2)
        self.assertIn('test-reasoner-model', decoded['hints'][1]['text'])
        self.assertIn('/low', decoded['hints'][1]['text'])
        self.assertEqual(decoded['_usage']['input_tokens'], 321)
        self.assertEqual(decoded['_usage']['cached_input_tokens'], 45)
        self.assertEqual(decoded['_usage']['output_tokens'], 67)

    def test_loader_exposes_puzzle_definition(self) -> None:
        self.assertEqual(self.puzzle.puzzle_id, 'cryptic-2026-03-03')
        self.assertIn('1A', self.puzzle.clues)

    def test_local_thesaurus_filters_by_length(self) -> None:
        service = ThesaurusService(REPO_ROOT)
        candidates = service.lookup('story', length=7)
        words = {candidate['word'] for candidate in candidates}
        self.assertIn('account', words)
        self.assertIn('history', words)
        self.assertNotIn('tale', words)

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
                        'hints': [
                            {'level': 1, 'kind': 'clue_type', 'text': 'Runtime clue type hint.'},
                            {'level': 2, 'kind': 'structure', 'text': 'Runtime says the definition is at the start.'},
                            {'level': 3, 'kind': 'wordplay_focus', 'text': 'Runtime wordplay hint.'},
                            {'level': 4, 'kind': 'candidate_space', 'text': 'Runtime candidate hint.'},
                            {'level': 5, 'kind': 'answer_reveal', 'text': 'Runtime reveal hint.'},
                        ],
                        'confidence': 0.66,
                        '_usage': {'input_tokens': 120, 'cached_input_tokens': 30, 'output_tokens': 12},
                    }))
                elif operation == 'semantic_judgement':
                    print(json.dumps({
                        'result': 'plausible',
                        'reason': 'Runtime semantic review says the mechanical parse is good but definition fit needs confirmation.',
                        'confidence': 0.42,
                        '_usage': {'input_tokens': 100, 'cached_input_tokens': 20, 'output_tokens': 8},
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