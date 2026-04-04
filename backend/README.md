This is the development guide for the FastAPI backend. See the [project README](../README.md) for an overview.

# Backend

Run locally with:

```bash
uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Run smoke tests with:

```bash
python -m unittest backend.tests.test_api
```

Run the edge-case evaluation harness with:

```bash
python backend/tools/evaluate_edge_cases.py
```

Clean up expired runtime data with:

```bash
python backend/tools/cleanup_runtime_data.py
```

Adjust retention explicitly if needed:

```bash
python backend/tools/cleanup_runtime_data.py --session-ttl-hours 72 --import-ttl-hours 24
```

## Environment Variables

All environment variables are optional. The backend runs fully locally with no configuration.

| Variable | Purpose | Default |
|----------|---------|---------|
| `CROSSWORD_RUNTIME_MODE` | Runtime adapter selection: `heuristic` (full local analysis + optional external LLM) or `stub` (length/pattern checks only, useful for UI development without solvers) | `heuristic` |
| `CROSSWORD_CORS_ORIGINS` | Comma-separated list of frontend origins allowed to call the API in split deployments | `http://127.0.0.1:5173,http://localhost:5173` when unset |
| `CROSSWORD_SESSION_STORE` | Session storage backend selector | `filesystem` |
| `CROSSWORD_SESSION_FILESYSTEM_ROOT` | Optional directory root when `CROSSWORD_SESSION_STORE=filesystem` | `backend_data/sessions` |
| `CROSSWORD_SESSION_SQLITE_PATH` | Optional SQLite database path when `CROSSWORD_SESSION_STORE=sqlite` | `backend_data/sessions.sqlite3` |
| `CROSSWORD_PUZZLE_STORE` | Puzzle definition/import storage backend selector | `filesystem` |
| `CROSSWORD_PUZZLE_FILESYSTEM_ROOT` | Optional directory root when `CROSSWORD_PUZZLE_STORE=filesystem` | `samples` |
| `CROSSWORD_PUZZLE_SQLITE_PATH` | Optional SQLite database path when `CROSSWORD_PUZZLE_STORE=sqlite` | `backend_data/puzzles.sqlite3` |
| `CROSSWORD_RUNTIME_COMMAND` | Shell command for external LLM integration — receives JSON on stdin, writes JSON on stdout | empty (disabled) |
| `CROSSWORD_SEMANTIC_COMMAND` | Override just the semantic adjudication path, keeping other operations on the main runtime command | empty (disabled) |
| `CODEX_MODEL` | Default model when using the Codex wrapper | empty |
| `CODEX_MODEL_LITE` / `_REASONER` / `_VISION` | Capability-specific model overrides | falls back to `CODEX_MODEL` |
| `CODEX_REASONING_EFFORT` | Default reasoning effort level | empty |
| `CODEX_REASONING_EFFORT_LITE` / `_REASONER` / `_VISION` | Capability-specific effort overrides | falls back to `CODEX_REASONING_EFFORT` |
| `CODEX_RUNTIME_EXECUTABLE` | Path to the codex CLI binary | auto-detected via `shutil.which('codex')` |
| `CODEX_RUNTIME_TIMEOUT_SECONDS` | Subprocess timeout for codex calls | `90` |

### Split Hosting Notes

For SPA/API split hosting:
- deploy `visualizer/` as the frontend
- deploy `backend/` as the API service
- set the frontend `VITE_API_BASE_URL` to the backend origin
- set backend `CROSSWORD_CORS_ORIGINS` to include the frontend origin

Local development already uses the same explicit-addressing model, with the SPA calling `http://127.0.0.1:8000` directly.

Session persistence is now behind a store interface. Supported implementations are `filesystem` and `sqlite`.
Imported puzzle persistence is now behind a matching store interface. Supported implementations are `filesystem` and `sqlite`.
The SQLite puzzle store keeps bundled sample puzzles on disk while persisting imported puzzles in SQLite and rehydrating them on demand.

### Fly.io Notes

The repository now includes a baseline [`fly.toml`](../fly.toml) and [`Dockerfile`](../Dockerfile) for backend deployment on Fly.io.

Recommended first deployment shape:
- run the FastAPI backend as a single Fly app
- attach one volume mounted at `/data`
- use SQLite for both session and imported-puzzle persistence
- keep bundled sample puzzles in the image at `/app/samples`

Recommended backend env for Fly:

```bash
CROSSWORD_SESSION_STORE=sqlite
CROSSWORD_SESSION_SQLITE_PATH=/data/sessions.sqlite3
CROSSWORD_PUZZLE_STORE=sqlite
CROSSWORD_PUZZLE_SQLITE_PATH=/data/puzzles.sqlite3
CROSSWORD_PUZZLE_FILESYSTEM_ROOT=/app/samples
```

You still need to set:
- `CROSSWORD_CORS_ORIGINS` to the deployed frontend origin
- `CROSSWORD_RUNTIME_COMMAND` and any harness-specific env vars if you want external agent-backed hint generation


Example backend setting:

```bash
CROSSWORD_CORS_ORIGINS=https://your-frontend-host.example.com,http://localhost:5173
```

## Optional Agent Runtime Hook

The default backend runtime is local-first:
- clue-type detection and staged hints come from heuristic text analysis
- candidate generation comes from in-process calls into the `cryptic_skills/` Python modules
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
  "hints": [
    {"level": 1, "kind": "clue_type", "text": "This looks like an anagram clue."},
    {"level": 2, "kind": "structure", "text": "The definition is probably at the start."},
    {"level": 3, "kind": "wordplay_focus", "text": "Try rearranging the fodder near 'wobbly'."},
    {"level": 4, "kind": "candidate_space", "text": "Use the checkers to narrow the anagram candidates."},
    {"level": 5, "kind": "answer_reveal", "text": "The strongest answer here is ESTABLISH."}
  ],
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

## Reference Wrapper Model Selection

If `CROSSWORD_RUNTIME_COMMAND` points at `backend/runtime_wrappers/codex_runtime.py`, you can use the current reference wrapper for any `SKILL.md`-compatible harness that exposes a Codex-style CLI entry point.

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

The wrapper in this repository is a reference implementation for the current Codex CLI flow, not a requirement of the overall architecture. The broader contract is the JSON request/response boundary plus a SKILL.md-compatible harness.
## Edge-Case Harness

`backend/tools/evaluate_edge_cases.py` runs a small clue suite through:
- the local heuristic analysis
- the configured Codex wrapper profiles
- both `next_hint` and `semantic_judgement`

It defaults to the built-in edge-case set from the sample puzzle and prints Markdown. You can also:
- use `--format json` for machine-readable output
- use `--include-codex-53` to add `gpt-5.3-codex`
- use `--cases-file backend/edge_cases.example.json` to run a custom suite



