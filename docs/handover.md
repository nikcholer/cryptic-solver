# Handover

This file is the quick restart point for the next session.

## Current status

The repository has verified local Phase 3 changes in progress that are not yet committed.

Recent commits:
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

## Recommended next task

Finish the remaining Phase 3 cleanup and decide how much of it is worth doing before the next showcase/share pass.

Primary targets:
- `backend/app/runtime/adapter.py`
- `backend/app/services/puzzle_import_service.py`
- `cryptic_skills/extract_clues_from_pdf_text.py`
- `cryptic_skills/extract_grid_state_from_pdf_vector.py`

Current state there:
- deterministic solver candidate generation is already in-process
- PDF import extraction is already in-process
- the remaining subprocess seam is the external runtime wrapper, which is acceptable to keep external
- optional next cleanup is shared helper/module consolidation across the deterministic skill scripts

Recommended sequence:
1. Decide whether to stop Phase 3 here or do one more pass on shared deterministic-tool helpers.
2. If continuing, centralize shared wordlist/pattern/abbreviation loading used by solver modules.
3. Keep the external runtime boundary only for LLM-facing operations.
4. Re-run backend tests and update docs/README language to reflect the new in-process backend shape.

## Key files to read first

- `docs/hosting.md`
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
- worktree contained uncommitted verified Phase 3 changes
- backend test suite was passing
- edge-case harness executed successfully without a configured runtime
- frontend build was passing
- GitHub Actions CI on `master` was green

## Resume prompt suggestion

On the next machine/session, point the assistant at:
- `docs/handover.md`
- `docs/hosting.md`

Then say:
- "Continue from the handover. Phase 3 is already underway; decide whether to stop after the current in-process refactor or do one more shared-helper cleanup pass."
