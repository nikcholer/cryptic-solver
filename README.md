# Cryptic Crossword Solver: A Neuro-Symbolic Approach

A hybrid AI system that combines LLM reasoning with algorithmic solvers to crack cryptic crosswords — plus an interactive tutor UI for learning how cryptic clues work.

![Interactive Tutor UI showing a cryptic clue and AI-generated hints](docs/tutor_ui_demo.png)

## What Are Cryptic Crosswords?

Cryptic crosswords are puzzles where each clue is a miniature word puzzle with two paths to the answer:

- **The definition** â€” a synonym or description of the answer, always at the start or end of the clue.
- **The wordplay** â€” instructions for constructing the answer letter-by-letter through mechanisms like anagrams, hidden words, reversals, or charades.
- **The surface reading** â€” the clue is written to read as a plausible (if odd) English sentence, which is deliberate misdirection.

**Example:** *"The role is complicated for those with paying guests (9)"*

- **Definition:** "those with paying guests" â†’ HOTELIERS
- **Wordplay:** "The role is" = THEROLEIS, "complicated" = anagram indicator â†’ rearrange THEROLEIS â†’ HOTELIERS
- **Surface reading:** reads as though someone's role is complicated â€” pure misdirection.

## The Neuro-Symbolic Thesis

Neither an LLM nor a pure algorithmic solver can handle cryptic crosswords effectively alone:

- **LLMs** understand language â€” they can recognise that "complicated" signals an anagram, that "those with paying guests" defines HOTELIERS, and parse the misdirecting surface reading. But tokenisation makes them fundamentally unreliable at letter-level mechanics: they cannot reliably confirm that THEROLEIS rearranges into HOTELIERS, or count that a hidden word spans exactly 7 characters.

- **Algorithms** handle mechanics perfectly â€” anagram enumeration, pattern matching, dictionary validation â€” but they have no world knowledge. They cannot decide which part of a clue is the definition, which word is the indicator, or whether a candidate actually means what the clue asks.

Together they cover each other's weaknesses. The LLM handles *interpretation* (parsing, indicator recognition, definition matching). The algorithms handle *execution* (candidate generation under mechanical constraints). A final LLM evaluation step confirms that algorithmic candidates fit the definition.

## Worked Example

### Anagram: "The role is complicated for those with paying guests (9)"

**Step 1 â€” Indicator detection:** "complicated" is recognised as an anagram indicator.

**Step 2 â€” Fodder extraction:** The wordplay side is "The role is" = THEROLEIS (9 letters, matching the enumeration).

**Step 3 â€” Algorithmic solver:**
```bash
python cryptic_skills/anagram.py --fodder THEROLEIS --pattern .........
# â†’ {"candidates": ["hoteliers"]}
```

**Step 4 â€” Semantic confirmation:** The LLM verifies that "those with paying guests" = HOTELIERS. Confidence: 0.93.

**Step 5 â€” Grid commit:** HOTELIERS is placed in the grid. Checking letters propagate to crossing clues, constraining their search space.

### Initials: "wine honey enough now â€” for starters (4)"

**Step 1 â€” Indicator detection:** "for starters" signals an initial-letters clue.

**Step 2 â€” Letter extraction:** Take the first letter of each word: **W**ine **H**oney **E**nough **N**ow â†’ WHEN.

**Step 3 â€” Validation:** WHEN is in the dictionary and matches the pattern. Confidence: 0.93.

No external solver call is needed â€” the `HeuristicAdapter` extracts initials directly and validates against the wordlist.

## Try It: Interactive Tutor

The tutor UI lets you solve cryptic crosswords with guided hints and real-time validation.

```bash
# Start the backend
pip install -r requirements.txt
uvicorn app.main:app --app-dir backend --reload

# In a separate terminal, start the frontend
cd visualizer
npm install
npm run dev
```

Open `http://localhost:5173`. Select a clue, type your answer, and submit. Request hints (5 progressive levels from clue-type identification to full reveal), check answers against the solver engine, and watch crossing letters propagate through the grid.

See [visualizer/README.md](visualizer/README.md) for the full component map and source layout.

## Try It: Autonomous Agent

The solver can also run autonomously in any agent harness that can read `SKILL.md`, invoke local tools, and maintain a puzzle workspace:

**Option 1: `.skill` package** — Load `cryptic-solver.skill` into a compatible `SKILL.md`-aware runtime.

**Option 2: Clone and mount**
```bash
git clone https://github.com/nikcholer/cryptic-solver.git
pip install -r requirements.txt
```
Point your harness's skill search path at this repository. The agent will read `SKILL.md` and invoke the CLI solvers autonomously.

Codex is the reference harness currently documented in this repo, but the workflow is intentionally framed around `SKILL.md` compatibility rather than any single provider-specific runtime.

### Capability-based model allocation

The agent protocol uses capability roles rather than provider names:

| Role | Purpose |
|------|---------|
| `lite` | Fast, cheap candidate generation and broad recall |
| `reasoner` | Ambiguity resolution, semantic ranking, explanation |
| `vision` | Puzzle image reading, OCR, grid-layout extraction |

The runtime maps these roles to actual models, credentials, and endpoints. See `config/model-routing.example.yaml`.

## Architecture Overview

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                    Human or LLM                         â”‚
â”‚              (tutor UI  /  agent runtime)               â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                         â”‚
          â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
          â”‚     FastAPI Backend          â”‚
          â”‚  (sessions, grid engine,     â”‚
          â”‚   heuristic adapter)         â”‚
          â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                         â”‚
          â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
          â”‚   cryptic_skills/*.py        â”‚
          â”‚  (anagram, hidden, reversal, â”‚
          â”‚   insertion, charade,        â”‚
          â”‚   grid_manager)              â”‚
          â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                         â”‚
          â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
          â”‚   Data files                 â”‚
          â”‚  (words.txt, abbreviations,  â”‚
          â”‚   indicators, thesaurus)     â”‚
          â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

The backend detects clue types via indicator word matching, extracts fodder, calls the appropriate CLI solver, and validates candidates against the dictionary. An optional external LLM (configured via `CROSSWORD_RUNTIME_COMMAND`) provides semantic judgement and richer hints.

Full grid solving treats the puzzle as a Constraint Satisfaction Problem: high-confidence clue types (hidden words, anagrams) are solved first, their crossing letters constrain neighbouring clues, and the solver sweeps until no more progress can be made.

See [docs/architecture.md](docs/architecture.md) for the full technical reference.

### Why This Pattern Matters Beyond Crosswords

This project demonstrates a **neuro-symbolic orchestration pattern**: use LLMs for interpretation and judgement, delegate mechanical operations to deterministic tools, and close the loop with a semantic evaluation step. The same architecture applies wherever AI needs to work alongside rule-based systems â€” regulatory compliance, data transformation pipelines, scientific computation, or game engines.

## Clue Types

| Clue Type | Algorithmic Role | LLM Role | Solver Script |
|-----------|-----------------|----------|---------------|
| Anagram | Generate all dictionary anagrams of fodder | Detect indicator, extract fodder, confirm definition | `anagram.py` |
| Hidden word | Slide window across fodder text | Spot hidden-word indicator, identify fodder span | `hidden.py` |
| Reversal | Reverse fodder, validate against dictionary | Detect reversal indicator, identify fodder | `reversal.py` |
| Container | Insert inner element into outer, validate | Identify which element goes inside which | `insertion.py` |
| Charade | Concatenate abbreviations/synonyms, validate | Parse which components combine, identify abbreviations | `charade.py` |
| Initials/Acrostics | Extract first letters mechanically | Detect "initially"/"for starters" indicators | Built-in |
| Double definition | Pattern-filter dictionary candidates | Deep semantic matching against both definitions | Pattern only |
| Cryptic definition | Pattern filtering, n-gram frequency | World knowledge, phrase recognition | Pattern only |
| Homophone | Phonetic engine mapping (CMUdict) | Judge plausibility, select intended synonyms | Planned |

## Project Structure

```
cryptic-solver/
  SKILL.md                  â€” agent instruction document (machine-facing)
  cryptic_skills/           â€” CLI solver scripts and data files
  backend/                  â€” FastAPI application (API, services, runtime adapter)
  visualizer/               â€” React + TypeScript tutor UI
  samples/                  â€” sample puzzle definitions
  backend_data/             â€” live session state (runtime)
  config/                   â€” example deployment configs
  docs/                     â€” architecture and design documents
```

## Data Files

`cryptic_skills/words.txt` is an English wordlist (~370 K entries) used for candidate validation. It is derived from public-domain word lists and is included for development convenience. If you redistribute this project, verify compatibility with your intended use.

## Development

- [backend/README.md](backend/README.md) â€” running the backend, smoke tests, edge-case harness, runtime configuration
- [visualizer/README.md](visualizer/README.md) â€” tutor UI setup, component map, source layout
- [CONTRIBUTING.md](CONTRIBUTING.md) â€” dev onboarding, adding new solvers, code conventions

## Design Documents

- [docs/architecture.md](docs/architecture.md) â€” full technical reference: pipeline stages, solver inventory, grid orchestration, runtime abstraction
- [docs/interactive-tutor-backend.md](docs/interactive-tutor-backend.md) â€” original design specification for the tutor backend (implemented)
- [docs/agent-instructions-improvement-plan.md](docs/agent-instructions-improvement-plan.md) â€” roadmap for reliability, safety, and determinism improvements to `SKILL.md`



