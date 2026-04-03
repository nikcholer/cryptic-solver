# Handover

This file is the quick restart point for the next session.

## Current status

The repository is clean and the latest completed work is committed.

Recent commits:
- `d699ce4` Add maintenance command for runtime cleanup
- `af3d971` Add retention helpers for stored sessions and imports
- `d748a9a` Make storage roots configurable
- `405fe0d` Extend storage adapters for sessions and puzzles
- `5daf4a4` Abstract backend session storage
- `5eb6312` Use explicit local API addressing for SPA dev

## Where the project stands

Phase 1 is complete:
- SPA/API split-hosting support is in place.
- Local development now mirrors split hosting.
- SPA runs on `http://127.0.0.1:5173`.
- API runs on `http://127.0.0.1:8000`.
- Frontend uses explicit `VITE_API_BASE_URL` instead of a Vite proxy.

Phase 2 is complete:
- session storage is abstracted
- session backends: `filesystem`, `sqlite`
- puzzle/import storage is abstracted
- puzzle/import backends: `filesystem`, `sqlite`
- filesystem and sqlite roots/paths are configurable by env
- retention helpers exist for stale sessions and imported puzzles
- maintenance command exists: `python backend/tools/cleanup_runtime_data.py`

Phase 3 has not started.

## Recommended next task

Start Phase 3: replace subprocess-based deterministic solver calls with direct Python imports.

Primary target:
- `backend/app/runtime/adapter.py`

Current state there:
- deterministic solvers still shell out to scripts in `cryptic_skills/*.py`
- backend hosting no longer depends on changing this immediately, but it is the next structural cleanup step

Recommended sequence:
1. Identify the solver scripts currently invoked by subprocess.
2. Extract/import callable functions from those solver modules.
3. Update `HeuristicRuntimeAdapter._solver_candidates()` to call Python functions directly.
4. Keep the external runtime boundary only for LLM-facing operations.
5. Re-run backend tests and add targeted tests for the in-process solver path.

## Key files to read first

- `docs/hosting.md`
- `backend/app/runtime/adapter.py`
- `backend/app/stores/session_store.py`
- `backend/app/stores/puzzle_store.py`
- `backend/tools/cleanup_runtime_data.py`
- `backend/tests/test_api.py`

## Useful commands

Run backend tests:
```bash
python -m unittest backend.tests.test_api
```

Run frontend locally:
```bash
cd visualizer
npm install
npm run dev
```

Run backend locally:
```bash
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Run maintenance cleanup:
```bash
python backend/tools/cleanup_runtime_data.py
```

## Environment notes

Frontend:
- `visualizer/.env.development` sets `VITE_API_BASE_URL=http://127.0.0.1:8000`

Backend storage-related env vars:
- `CROSSWORD_SESSION_STORE`
- `CROSSWORD_SESSION_FILESYSTEM_ROOT`
- `CROSSWORD_SESSION_SQLITE_PATH`
- `CROSSWORD_PUZZLE_STORE`
- `CROSSWORD_PUZZLE_FILESYSTEM_ROOT`
- `CROSSWORD_PUZZLE_SQLITE_PATH`

CORS / hosting env vars:
- `CROSSWORD_CORS_ORIGINS`

## Verification status

At the last checkpoint before writing this file:
- worktree was clean
- backend test suite was passing
- cleanup tool executed successfully

## Resume prompt suggestion

On the next machine/session, point the assistant at:
- `docs/handover.md`
- `docs/hosting.md`

Then say:
- "Continue from the handover. Start Phase 3 by replacing subprocess solver calls with direct Python imports."
