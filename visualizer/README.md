# Interactive Crossword Tutor

The tutor is a browser-based UI for solving cryptic crosswords with guided hints and validation. It connects to the same neuro-symbolic solver engine that powers the autonomous agent mode, but presents it as an interactive learning tool — the user fills in answers, requests progressively revealing hints, and gets immediate feedback on their guesses.

## Features

- **Interactive grid** with checker propagation — placing an answer fills crossing letters into intersecting clues automatically
- **5-stage hint ladder** — hints progress from clue-type identification through structure, wordplay focus, candidate narrowing, to full answer reveal
- **Validation feedback** — deterministic checks (length, pattern, dictionary, solver confirmation) run first; optional semantic LLM adjudication follows
- **Thesaurus lookup** — search for synonyms to help with definition matching
- **Symbolic follow-up suggestions** — when the system cannot confirm or reject an answer, it may suggest a targeted next step (e.g. "Try inserting KE into flower names")
- **PDF upload** — import a new puzzle from a PDF file

## Quick Start

Prerequisites:
- Node 18+
- Backend running (see [backend/README.md](../backend/README.md))

```bash
cd visualizer
npm install
npm run dev
```

The dev server starts at `http://127.0.0.1:5173` by default.
In the current setup, local development uses explicit API addressing via `VITE_API_BASE_URL=http://127.0.0.1:8000` from `visualizer/.env.development`, so the browser talks to the backend the same way it will in split hosting.

For split hosting, set `VITE_API_BASE_URL` to the deployed backend origin so the SPA calls the API by full URL instead of relying on same-origin `/api` paths.

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `VITE_PUZZLE_ID` | Puzzle loaded on first visit (must match a puzzle ID known to the backend) | `cryptic-2026-03-03` |
| `VITE_API_BASE_URL` | Base URL for the backend API, e.g. `http://127.0.0.1:8000` locally or `https://cryptic-api.onrender.com` when split-hosted | `http://127.0.0.1:8000` in `development` via `visualizer/.env.development` |

Set Vite env vars in a `.env.local` file or inline: `VITE_PUZZLE_ID=prize-cryptic-85080 npm run dev`.

Example split-hosting `.env.local`:

```bash
VITE_API_BASE_URL=https://your-backend-host.example.com
VITE_PUZZLE_ID=cryptic-2026-03-03
```

## Components

| Component | File | Purpose |
|-----------|------|---------|
| `CrosswordGrid` | `src/components/CrosswordGrid.tsx` | Renders the grid, handles cell selection and navigation |
| `ClueList` | `src/components/ClueList.tsx` | Across/Down clue panels with status indicators |
| `ClueWorkspace` | `src/components/ClueWorkspace.tsx` | Active clue detail: answer input, submit, check, hint request, validation card, symbolic follow-up display |
| `HintStack` | `src/components/HintStack.tsx` | Renders the accumulated hint history for the selected clue |
| `ThesaurusPanel` | `src/components/ThesaurusPanel.tsx` | Synonym lookup interface |
| `Cell` | `src/components/Cell.tsx` | Individual grid cell with letter display, selection, and status styling |

## Source Layout

```
src/
  hooks/
    useTutorSession.ts   — session lifecycle, answer submission, hint requests, puzzle switching
  api.ts                 — HTTP client (fetchJson, fetchFormJson wrappers)
  gridUtils.ts           — grid geometry helpers (iterateClueCells, sortClues)
  format.ts              — display helpers (formatStatus, formatTokens)
  sessionStorage.ts      — browser localStorage for session persistence
  types/
    index.ts             — TypeScript models mirroring the backend (PuzzleClue, SessionState, HintRecord, ValidationRecord, etc.)
  components/            — React components listed above
  App.tsx                — root component, wires useTutorSession to the UI
```


Current limitation: the bundled PDF import path is tuned for Telegraph-style born-digital PDFs. Other layouts may need custom extraction logic or a pre-generated clues.yaml and grid_state.json.

