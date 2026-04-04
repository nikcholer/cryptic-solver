# Handover

This file is the quick restart point for the next session.

## Current status

The repository has verified local Fly deployment preparation changes in progress that are not yet committed.

Recent commits:
- `173ce43` Refactor local backend tooling in-process
- `d8f8c1b` Fix edge-case harness CI wiring
- `065608b` Complete puzzle import storage abstraction
- `d699ce4` Add maintenance command for runtime cleanup
- `af3d971` Add retention helpers for stored sessions and imports
- `d748a9a` Make storage roots configurable
- `405fe0d` Extend storage adapters for sessions and puzzles

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
- CI covers backend tests, the edge-case harness, and the frontend build

Phase 3 is in progress:
- heuristic deterministic solver calls now run in-process via direct Python imports
- PDF import extraction now runs in-process via direct Python imports
- backend no longer shells out for those local deterministic paths
- the external runtime wrapper boundary remains subprocess-based by design

Fly deployment prep is in progress:
- baseline `Dockerfile`, `.dockerignore`, and `fly.toml` now exist locally
- recommended first deployment shape is SQLite-backed sessions/imports on a Fly volume mounted at `/data`
- backend/docs env guidance has been updated for Fly
- actual Fly launch, secrets, and first deploy have not been executed yet

## Recommended next task

Finish and test the first Fly deployment, then decide whether any further Phase 3 cleanup is still worth doing.

Primary targets:
- `fly.toml`
- `Dockerfile`
- `backend/README.md`
- `docs/hosting.md`

Current state there:
- the backend container/deploy shape is defined
- SQLite-on-volume is the recommended first hosted persistence model
- the remaining unknowns are operational: actual app name, Fly volume creation, secrets/env, and first deployment behavior

Recommended sequence:
1. Change the placeholder app name in `fly.toml`.
2. Create the Fly volume and set deploy-time env/secrets such as `CROSSWORD_CORS_ORIGINS`.
3. Run the first `fly deploy` and validate `/health`.
4. Decide whether cleanup should stay manual or move to a scheduled deployment/automation step.
5. Only after that, decide whether any more shared deterministic-tool cleanup is worth doing.

## Key files to read first

- `docs/hosting.md`
- `fly.toml`
- `Dockerfile`
- `backend/app/runtime/adapter.py`
- `backend/app/services/puzzle_import_service.py`
- `backend/app/stores/session_store.py`
- `backend/app/stores/puzzle_store.py`
- `cryptic_skills/extract_clues_from_pdf_text.py`
- `cryptic_skills/extract_grid_state_from_pdf_vector.py`
- `backend/tools/evaluate_edge_cases.py`
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
- worktree contained uncommitted verified Fly deployment prep changes
- backend test suite was passing
- edge-case harness executed successfully without a configured runtime
- frontend build was passing
- GitHub Actions CI on `master` was green

## Resume prompt suggestion

On the next machine/session, point the assistant at:
- `docs/handover.md`
- `docs/hosting.md`

Then say:
- "Continue from the handover. The next task is the first Fly deployment using the documented SQLite-on-volume setup."
