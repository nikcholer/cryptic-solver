from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
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
    'required': ['clueId', 'hintLevel', 'kind', 'text', 'confidence'],
    'properties': {
        'clueId': {'type': 'string'},
        'hintLevel': {'type': 'integer'},
        'kind': {
            'type': 'string',
            'enum': ['clue_type', 'structure', 'wordplay_focus', 'candidate_space', 'answer_reveal'],
        },
        'text': {'type': 'string'},
        'confidence': {'type': ['number', 'null']},
    },
}

SEMANTIC_SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': ['result', 'reason', 'confidence'],
    'properties': {
        'result': {'type': 'string', 'enum': ['confirmed', 'plausible', 'conflict']},
        'reason': {'type': 'string'},
        'confidence': {'type': ['number', 'null']},
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
    if operation == 'next_hint':
        prompt = f"""
You are helping a crossword tutor backend. Return JSON only.

Task: Provide exactly one next-stage hint for a single cryptic clue.
Do not solve the clue outright unless the requested hint level implies answer reveal.
Keep the hint concise and useful to a human solver.
Respect the clue-specific evidence already supplied.
This tutor uses a strict staged hint ladder. Do not skip ahead.
The supplied clue analysis is provisional evidence from a local heuristic, not guaranteed truth.
You may disagree with the proposed clue type, definition side, indicator, or fodder if the clue suggests a better reading.
When the evidence looks ambiguous, prefer cautious wording such as likely, may, or probably.

Return fields:
- clueId
- hintLevel
- kind
- text
- confidence

Clue context:
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

Requested output semantics:
- hintLevel must equal hintLevelAlreadyShown + 1
- kind and text must match this ladder:
  - Level 1: kind=clue_type. Identify the likely clue type only. If the local clue type looks doubtful, give your best high-level reading instead of repeating it blindly.
  - Level 2: kind=structure. Mention high-level structure such as likely definition side and, if relevant, the indicator word. Do not mention fodder text, letter selection, candidate answers, or overcommit to a shaky parse.
  - Level 3: kind=wordplay_focus. You may mention fodder text or the specific cryptic operation.
  - Level 4: kind=candidate_space. You may narrow the search space using pattern/checkers or meaning.
  - Level 5: kind=answer_reveal. Only now may you state the answer directly.
- text must be plain English, not markdown, and not mention internal backend machinery
- For early hints, preserve challenge. Prefer the least revealing wording that still helps.
""".strip()
        return prompt, NEXT_HINT_SCHEMA

    if operation == 'semantic_judgement':
        prompt = f"""
You are helping a crossword tutor backend. Return JSON only.

Task: Judge whether a proposed answer matches the direct definition of a cryptic clue.
The supplied clue analysis is provisional evidence from a local heuristic, not guaranteed truth.
Use it as context, but do not assume the proposed definition side or clue type is correct if the clue suggests otherwise.
Focus on semantic fit, part of speech, number, and natural crossword sense.

Return fields:
- result
- reason
- confidence

Guidance:
- Use 'confirmed' only if the answer matches the direct definition well.
- Use 'plausible' if the answer could fit but you are not fully sure, or if the local analysis may be pointing at the wrong definition span.
- Use 'conflict' if the answer does not match the direct definition.
- Reason should be one short sentence.

Clue context:
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
- mechanicalResult: {context['mechanicalResult']}
""".strip()
        return prompt, SEMANTIC_SCHEMA

    raise ValueError(f'Unsupported operation: {operation}')


def invoke_codex(prompt: str, schema: dict[str, Any], capability: str | None) -> dict[str, Any] | None:
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as schema_file:
        schema_path = Path(schema_file.name)
        json.dump(schema, schema_file)

    try:
        command = [
            *resolve_codex_command(),
            'exec',
            prompt,
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
    finally:
        schema_path.unlink(missing_ok=True)


def resolve_codex_command() -> list[str]:
    override = os.environ.get('CODEX_RUNTIME_EXECUTABLE', '').strip()
    if override:
        return shlex.split(override, posix=False)
    return ['codex']




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
        return json.loads(last_message)
    except json.JSONDecodeError:
        return None


def _print_error(message: str) -> None:
    print(message, file=sys.stderr)


if __name__ == '__main__':
    raise SystemExit(main())