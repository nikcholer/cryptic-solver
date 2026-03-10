# Contributing

## Getting Started

```bash
# Clone the repository
git clone https://github.com/nikcholer/cryptic-solver.git
cd cryptic-solver

# Install Python dependencies
pip install -r requirements.txt

# Run the backend
uvicorn app.main:app --app-dir backend --reload

# In a separate terminal, install and run the visualizer
cd visualizer
npm install
npm run dev

# Run backend tests
python -m unittest backend.tests.test_api
```

## Project Layout

| Directory | What lives here |
|-----------|----------------|
| `cryptic_skills/` | Standalone CLI solver scripts and data files (wordlist, abbreviations, indicators, thesaurus). Each script is invoked via `python cryptic_skills/<script>.py --fodder ... --pattern ...` and writes JSON to stdout. |
| `backend/` | FastAPI application — API routes, session service, grid engine, runtime adapter, Pydantic models, tests. |
| `backend/app/runtime/` | Runtime abstraction layer — `HeuristicRuntimeAdapter`, external LLM gateway, semantic adjudicator. |
| `visualizer/` | React + TypeScript frontend (Vite). Interactive tutor UI. |
| `samples/` | Sample puzzle definitions used by the backend's `PuzzleLoader`. |
| `backend_data/` | Runtime data — live session state files. |
| `docs/` | Architecture reference and design documents. |
| `config/` | Example deployment configs (model routing). |
| `SKILL.md` | Agent instruction document — machine-facing, defines the autonomous solving protocol. |

## Adding a New Solver

All solvers follow the same pattern:

1. **Create the script** at `cryptic_skills/new_solver.py`.
2. **Accept standard CLI arguments:**
   - `--fodder` — the input text to operate on
   - `--pattern` — the crossing-letter constraint (e.g. `S..R...`)
   - Any type-specific arguments (e.g. `--length`, `--outer`)
3. **Write JSON to stdout:**
   ```json
   {"candidates": ["word1", "word2"]}
   ```
4. **Validate against `words.txt`** — only return candidates that appear in the wordlist.
5. **Register in `SKILL.md`** — add a tool section so the agent knows how to invoke it.
6. **Add detection in `HeuristicAdapter`** — update `backend/app/runtime/adapter.py`:
   - Add indicator words to the appropriate list (or create a new one).
   - Add a detection branch in `_detect_clue_type()`.
   - Add a solver-invocation branch in `_solver_candidates()`.

## Running Tests

### Backend tests

```bash
python -m unittest backend.tests.test_api
```

### Edge-case evaluation harness

```bash
python backend/tools/evaluate_edge_cases.py
```

This runs a curated clue suite through the heuristic analyser and (optionally) the configured external runtime. Use `--format json` for machine-readable output.

### Visualizer

No test suite is established yet. Contributions welcome.

## Code Conventions

- **Python**: type annotations on all function signatures. Pydantic models for API request/response schemas. Enum values for status vocabularies (`ClueStatus`, `ValidationResult`, `HintKind`).
- **TypeScript**: strict mode enabled. Types mirror the backend models in `visualizer/src/types/index.ts`.
- **Solvers**: each script is self-contained — it loads its own data files and has no import dependencies on the backend.
