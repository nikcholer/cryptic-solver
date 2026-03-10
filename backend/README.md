This is the development guide for the FastAPI backend. See the [project README](../README.md) for an overview.

# Backend

Run locally with:

```bash
uvicorn app.main:app --app-dir backend --reload
```

Run smoke tests with:

```bash
python -m unittest backend.tests.test_api
```

Run the edge-case evaluation harness with:

```bash
python backend/tools/evaluate_edge_cases.py
```

## Optional Agent Runtime Hook

The default backend runtime is local-first:
- clue-type detection and staged hints come from heuristic text analysis
- candidate generation comes from the `cryptic_skills/` Python scripts
- mechanical validation can confirm obvious wordplay such as anagrams and hidden words

If you want to hand clue-scoped requests to an external agent runtime, set `CROSSWORD_RUNTIME_COMMAND` to a command that reads JSON on stdin and writes JSON on stdout.

The backend currently sends these operations through that boundary:
- `next_hint`
- `semantic_judgement`

Expected top-level request fields:
- `skill`
- `operation`
- `capability`
- `response_format`
- `context`

Example `next_hint` response:

```json
{
  "clueId": "4D",
  "hintLevel": 2,
  "kind": "structure",
  "text": "The definition is probably at the start.",
  "confidence": 0.71
}
```

Example `semantic_judgement` response:

```json
{
  "result": "confirmed",
  "reason": "Matches the direct definition as a verb in the required sense.",
  "confidence": 0.84
}
```

Valid semantic `result` values are:
- `confirmed`
- `plausible`
- `conflict`

If you want a separate command just for final semantic adjudication, you can still set `CROSSWORD_SEMANTIC_COMMAND`. That overrides the semantic use of `CROSSWORD_RUNTIME_COMMAND` while keeping other runtime-routed operations on the main command.

This keeps provider routing outside the backend. A deployment can point either command at any local alias, wrapper, or agent runtime it wants.

## Codex Wrapper Model Selection

If `CROSSWORD_RUNTIME_COMMAND` points at `backend/runtime_wrappers/codex_runtime.py`, you can choose the Codex model explicitly with environment variables.

Supported model variables:
- `CODEX_MODEL`
- `CODEX_MODEL_LITE`
- `CODEX_MODEL_REASONER`
- `CODEX_MODEL_VISION`

Supported reasoning-effort variables:
- `CODEX_REASONING_EFFORT`
- `CODEX_REASONING_EFFORT_LITE`
- `CODEX_REASONING_EFFORT_REASONER`
- `CODEX_REASONING_EFFORT_VISION`

Resolution order is:
1. capability-specific variable such as `CODEX_MODEL_REASONER`
2. fallback variable such as `CODEX_MODEL`

Reasoning effort is resolved the same way and passed through to Codex as `model_reasoning_effort`.

This keeps capability mapping in deployment config rather than inferring roles from model names.
## Edge-Case Harness

`backend/tools/evaluate_edge_cases.py` runs a small clue suite through:
- the local heuristic analysis
- the configured Codex wrapper profiles
- both `next_hint` and `semantic_judgement`

It defaults to the built-in edge-case set from the sample puzzle and prints Markdown. You can also:
- use `--format json` for machine-readable output
- use `--include-codex-53` to add `gpt-5.3-codex`
- use `--cases-file backend/edge_cases.example.json` to run a custom suite

