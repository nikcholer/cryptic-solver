# Sample puzzle workspace (cryptic-2026-03-03)

This folder is a captured, solved workspace used to regression-test the solver workflow:

- `cryptic-crossword-83732.pdf` — source puzzle
- `grid_only.png` — cropped grid image used for deterministic grid extraction
- `clues.yaml` — extracted clues
- `grid_state.json` — grid coordinates + placed answers
- `progress.md` / `progress.jsonl` — telemetry logs produced during solving

Notes:
- Large rendered page images (e.g. `page-1.png`) are intentionally omitted to keep the repo lighter.
