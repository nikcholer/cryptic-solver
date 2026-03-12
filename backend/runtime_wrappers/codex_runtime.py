from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / 'backend'
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.runtime.schemas import RuntimeRequest  # noqa: E402

NEXT_HINT_SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': ['clueId', 'hints', 'confidence'],
    'properties': {
        'clueId': {'type': 'string'},
        'hints': {
            'type': 'array',
            'minItems': 5,
            'maxItems': 5,
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'required': ['level', 'kind', 'text'],
                'properties': {
                    'level': {'type': 'integer'},
                    'kind': {
                        'type': 'string',
                        'enum': ['clue_type', 'structure', 'wordplay_focus', 'candidate_space', 'answer_reveal'],
                    },
                    'text': {'type': 'string'},
                },
            },
        },
        'confidence': {'type': ['number', 'null']},
    },
}

SEMANTIC_SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': ['result', 'reason', 'confidence', 'symbolicFollowup'],
    'properties': {
        'result': {'type': 'string', 'enum': ['confirmed', 'plausible', 'conflict']},
        'reason': {'type': 'string'},
        'confidence': {'type': ['number', 'null']},
        'symbolicFollowup': {'type': ['string', 'null']},
    },
}


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        _print_error('No runtime payload received on stdin.')
        return 1

    try:
        payload = RuntimeRequest.model_validate_json(raw)
    except Exception as exc:
        _print_error(f'Invalid runtime payload: {exc}')
        return 1

    payload_dict = payload.model_dump()
    prompt, schema = build_prompt_and_schema(payload_dict)
    result = invoke_codex(prompt, schema, payload_dict.get('capability'))
    if result is None:
        _print_error('Codex returned no structured result.')
        return 1

    print(json.dumps(result))
    return 0


def build_prompt_and_schema(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    operation = payload['operation']
    context = payload['context']
    linked_entries = context.get('linkedEntries') or []
    referenced_clues = context.get('referencedClues') or []
    if operation == 'next_hint':
        prompt = f"""
You are helping a crossword tutor backend. Return JSON only.

Generate a five-level hint ladder for one cryptic clue. Use the supplied symbolicAnalysis as your starting point, but treat it as provisional and revise it if the clue clearly supports a better reading. Keep hints concise, clue-specific, and internally consistent.

Context:
- clueId: {context['clueId']}
- clue: {context['clue']}
- enumeration: {context['enumeration']}
- pattern: {context['pattern']}
- hintLevelAlreadyShown: {context['hintLevelAlreadyShown']}
- clueType: {context['clueType']}
- definitionText: {context['definitionText']}
- definitionSide: {context['definitionSide']}
- indicator: {context.get('indicator')}
- fodderText: {context.get('fodderText')}
- solverCandidates: {context.get('solverCandidates')}
- symbolicAnalysis: {context.get('symbolicAnalysis')}
- linkedEntries: {linked_entries}
- referencedClues: {referenced_clues}

Return exactly five hints in order, with kinds fixed as:
1 clue_type
2 structure
3 wordplay_focus
4 candidate_space
5 answer_reveal

Rules:
- Each level must add something new and remain consistent with later levels.
- Level 1: identify only the likely clue family, or say no single type stands out.
- Level 2: give high-level structure such as likely definition side and maybe one indicator word.
- Level 3: mention the specific operation or fodder if helpful.
- Level 4: narrow the search using meaning, enumeration, or checkers without effectively giving the answer away.
- Level 5: reveal the answer only if genuinely confident; otherwise say no confident reveal is available yet.
- Before level 5, do not reveal the answer or use a near-synonym that effectively reveals it.
- If the clue has linkedEntries or referencedClues, use them as meaningful context.
- Plain English only; no markdown; do not mention backend fields.
""".strip()
        return prompt, NEXT_HINT_SCHEMA

    if operation == 'semantic_judgement':
        prompt = f"""
You are helping a crossword tutor backend. Return JSON only.

Judge whether a proposed answer fits a cryptic clue. Use symbolicAnalysis as deterministic pre-LLM evidence, but do not treat it as guaranteed truth. Consider all plausible definition readings, natural crossword sense, part of speech, and number.

Context:
- clueId: {context['clueId']}
- clue: {context['clue']}
- enumeration: {context['enumeration']}
- proposedAnswer: {context['proposedAnswer']}
- definitionText: {context['definitionText']}
- definitionSide: {context['definitionSide']}
- clueType: {context['clueType']}
- indicator: {context.get('indicator')}
- fodderText: {context.get('fodderText')}
- solverCandidates: {context.get('solverCandidates')}
- symbolicAnalysis: {context.get('symbolicAnalysis')}
- linkedEntries: {linked_entries}
- referencedClues: {referenced_clues}
- solverJustification: {context.get('solverJustification')}
- mechanicalResult: {context['mechanicalResult']}

Rules:
- confirmed: strong definition fit; include brief wordplay explanation if it is clear.
- plausible: could fit, or the likely definition span may differ from the current guess.
- conflict: fails against all plausible definition readings.
- Do not reject an answer merely because it overturns an earlier parse guess.
- Treat symbolicAnalysis as the deterministic starting point for letter mechanics. Use it if it supports a parse; if it is weak or unresolved, say so rather than inventing a detailed new mechanism.
- Only describe precise letter operations when they are supported by symbolicAnalysis, solverJustification, or an obvious one-step clue device.
- If symbolicAnalysis has no solverCandidates and no fodderText, avoid speculative assembly/disassembly claims and judge mainly on definition fit unless solverJustification clearly supplies the mechanics.
- If the answer seems semantically plausible but the mechanics are unresolved, set result to plausible and use symbolicFollowup to suggest the next symbolic search the caller should try.
- symbolicFollowup should be null unless you are explicitly suggesting a targeted symbolic next step such as testing an insertion, anagram fodder, hidden answer span, or letter-selection pattern.
- If solverJustification is present, treat it as extra human evidence, not an automatic override.
- Prefer explanation with both definition and wordplay for straightforward clues.
- Inspect the clue itself for simple mechanisms such as anagram, containment, reversal, hidden answer, initial letters, charade, or homophone.
- Keep the reason concise, natural, and free of backend/internal terminology.
""".strip()
        return prompt, SEMANTIC_SCHEMA

    raise ValueError(f'Unsupported operation: {operation}')


def invoke_codex(prompt: str, schema: dict[str, Any], capability: str | None) -> dict[str, Any] | None:
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as schema_file:
        schema_path = Path(schema_file.name)
        json.dump(schema, schema_file)

    with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8') as prompt_file:
        prompt_path = Path(prompt_file.name)
        prompt_file.write(prompt)

    try:
        # Read the prompt back as a single string to avoid Windows CLI
        # argument truncation with multi-line strings.
        prompt_text = prompt_path.read_text(encoding='utf-8')
        command = [
            *resolve_codex_command(),
            'exec',
            prompt_text,
            '--skip-git-repo-check',
            '--sandbox',
            'read-only',
        ]
        model = resolve_codex_model(capability)
        if model:
            command.extend(['-m', model])
        reasoning_effort = resolve_codex_reasoning_effort(capability)
        if reasoning_effort:
            command.extend(['-c', f'model_reasoning_effort="{reasoning_effort}"'])
        command.extend([
            '--output-schema',
            str(schema_path),
            '--json',
            '-C',
            str(ROOT),
        ])
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=ROOT,
            check=False,
            timeout=int(os.environ.get('CODEX_RUNTIME_TIMEOUT_SECONDS', '90')),
        )
        if completed.returncode != 0:
            _print_error('CODEX_STDERR_START')
            _print_error(completed.stderr or '')
            _print_error('CODEX_STDERR_END')
            _print_error('CODEX_STDOUT_START')
            _print_error(completed.stdout or '')
            _print_error('CODEX_STDOUT_END')
            return None
        parsed = parse_codex_jsonl(completed.stdout)
        if parsed is None:
            _print_error('CODEX_STDERR_START')
            _print_error(completed.stderr or '')
            _print_error('CODEX_STDERR_END')
            _print_error('CODEX_STDOUT_START')
            _print_error(completed.stdout or '')
            _print_error('CODEX_STDOUT_END')
        return parsed
    except subprocess.TimeoutExpired:
        _print_error('Codex runtime timed out.')
        return None
    except PermissionError as exc:
        _print_error(f'Codex runtime launch failed: {exc}')
        return None
    finally:
        schema_path.unlink(missing_ok=True)


def resolve_codex_command() -> list[str]:
    override = os.environ.get('CODEX_RUNTIME_EXECUTABLE', '').strip()
    if override:
        command = shlex.split(override, posix=False)
    else:
        resolved = shutil.which('codex')
        command = [resolved] if resolved else ['codex']

    executable = command[0]
    lowered = executable.lower()
    if lowered.endswith('.cmd') or lowered.endswith('.bat'):
        return ['cmd.exe', '/c', executable, *command[1:]]
    if lowered.endswith('.ps1'):
        return ['powershell.exe', '-ExecutionPolicy', 'Bypass', '-File', executable, *command[1:]]
    return command




def resolve_codex_model(capability: str | None) -> str | None:
    role = (capability or '').strip().upper()
    if role:
        specific = os.environ.get(f'CODEX_MODEL_{role}', '').strip()
        if specific:
            return specific
    default = os.environ.get('CODEX_MODEL', '').strip()
    return default or None



def resolve_codex_reasoning_effort(capability: str | None) -> str | None:
    role = (capability or '').strip().upper()
    if role:
        specific = os.environ.get(f'CODEX_REASONING_EFFORT_{role}', '').strip()
        if specific:
            return specific
    default = os.environ.get('CODEX_REASONING_EFFORT', '').strip()
    return default or None

def parse_codex_jsonl(stdout: str) -> dict[str, Any] | None:
    last_message: str | None = None
    usage: dict[str, Any] | None = None
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        if event.get('type') == 'exec.command_begin':
            continue
        if event.get('type') == 'exec.command_end':
            continue
        if event.get('type') == 'item.completed':
            item = event.get('item', {})
            if item.get('type') == 'message':
                content = item.get('content', [])
                for block in content:
                    if block.get('type') == 'output_text':
                        last_message = block.get('text', '')
            elif item.get('type') == 'agent_message' and isinstance(item.get('text'), str):
                last_message = item.get('text', '')
        if event.get('type') == 'agent_message_delta':
            delta = event.get('delta', {})
            if delta.get('type') == 'output_text_delta':
                last_message = (last_message or '') + delta.get('text', '')
        if event.get('msg', {}).get('type') == 'assistant_message':
            content = event['msg'].get('message', {}).get('content', [])
            for item in content:
                if item.get('type') == 'output_text':
                    last_message = item.get('text', '')
        elif event.get('msg', {}).get('type') == 'task_complete':
            result = event['msg'].get('last_agent_message')
            if isinstance(result, str) and result.strip():
                last_message = result
        if event.get('type') == 'turn.completed':
            event_usage = event.get('usage')
            if isinstance(event_usage, dict):
                usage = {
                    'input_tokens': int(event_usage.get('input_tokens', 0) or 0),
                    'cached_input_tokens': int(event_usage.get('cached_input_tokens', 0) or 0),
                    'output_tokens': int(event_usage.get('output_tokens', 0) or 0),
                }

    if not last_message:
        return None
    last_message = last_message.strip()
    if last_message.startswith('```'):
        parts = last_message.split('```')
        if len(parts) >= 3:
            last_message = parts[1]
            if last_message.startswith('json'):
                last_message = last_message[4:].strip()
    try:
        decoded = json.loads(last_message)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    if usage is not None:
        decoded['_usage'] = usage
    return decoded


def _print_error(message: str) -> None:
    print(message, file=sys.stderr)


if __name__ == '__main__':
    raise SystemExit(main())