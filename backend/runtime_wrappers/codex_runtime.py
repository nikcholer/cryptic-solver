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
        # Keep the prompt compact: on Windows, extremely long CLI arguments can be
        # truncated or mis-parsed, which can drop critical fields like clue text.
        prompt = (
            "Return JSON only. "
            "Task: generate a five-level hint ladder (exactly five hints) for a cryptic clue. "
            f"clueId={context.get('clueId')}; "
            f"clue={context.get('clue')}; "
            f"enumeration={context.get('enumeration')}; "
            f"pattern={context.get('pattern')}; "
            f"hintLevelAlreadyShown={context.get('hintLevelAlreadyShown')}; "
            f"clueType={context.get('clueType')}; "
            f"definitionText={context.get('definitionText')}; "
            f"definitionSide={context.get('definitionSide')}; "
            f"indicator={context.get('indicator')}; "
            f"fodderText={context.get('fodderText')}; "
            f"solverCandidates={context.get('solverCandidates')}; "
            f"symbolicAnalysis={context.get('symbolicAnalysis')}; "
            f"linkedEntries={linked_entries}; "
            f"referencedClues={referenced_clues}. "
            "Rules: concise, clue-specific, consistent across levels; do not reveal the answer before level 5."
        )
        return prompt, NEXT_HINT_SCHEMA

    if operation == 'semantic_judgement':
        prompt = (
            "Return JSON only. "
            "Task: judge whether a proposed answer fits a cryptic clue. "
            f"clueId={context.get('clueId')}; "
            f"clue={context.get('clue')}; "
            f"enumeration={context.get('enumeration')}; "
            f"proposedAnswer={context.get('proposedAnswer')}; "
            f"definitionText={context.get('definitionText')}; "
            f"definitionSide={context.get('definitionSide')}; "
            f"clueType={context.get('clueType')}; "
            f"indicator={context.get('indicator')}; "
            f"fodderText={context.get('fodderText')}; "
            f"solverCandidates={context.get('solverCandidates')}; "
            f"symbolicAnalysis={context.get('symbolicAnalysis')}; "
            f"linkedEntries={linked_entries}; "
            f"referencedClues={referenced_clues}; "
            f"solverJustification={context.get('solverJustification')}; "
            f"mechanicalResult={context.get('mechanicalResult')}. "
            "Rules: confirmed/plausible/conflict; keep reason concise; use symbolicFollowup only for targeted next step."
        )
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
        # Normalize Windows newlines. Some CLI stacks treat `\r` as a hard
        # terminator when ingesting prompt strings, which can drop everything
        # after the first line (including the clue text).
        prompt_text = prompt_text.replace('\r\n', '\n').replace('\r', '\n')
        if not prompt_text.strip():
            _print_error('Empty prompt passed to Codex.')
            return None
        # NOTE: `codex exec` expects flags before the PROMPT argument.
        # If the prompt is placed before flags, Codex can treat later tokens as
        # part of the prompt, ignoring options like --json and --output-schema.
        command = [
            *resolve_codex_command(),
            'exec',
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
        command.append(prompt_text)
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