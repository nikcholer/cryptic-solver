# Architecture

## Neuro-Symbolic Design Philosophy

Cryptic crosswords sit at an intersection that defeats both pure LLMs and pure algorithms:

- **LLMs** excel at semantics — recognising that "complicated" is an anagram indicator, that "those with paying guests" defines HOTELIERS, or that "for starters" signals an initials clue. But tokenisation makes them fundamentally unreliable at letter-level mechanics: counting characters, enumerating anagrams, or confirming that THEROLEIS rearranges to HOTELIERS.

- **Algorithmic solvers** handle mechanics perfectly — anagram enumeration, hidden-word sliding windows, pattern matching against dictionaries — but they have no world knowledge. They cannot decide which part of a clue is the definition, which is the indicator, or whether a candidate answer actually means what the definition asks.

This project combines both. The LLM handles *interpretation* (parsing clue structure, identifying indicators, matching definitions). The algorithms handle *execution* (generating candidates that satisfy mechanical constraints). A final semantic evaluation step lets the LLM rank or confirm candidates the algorithms produce, closing the loop.

## Pipeline Stages

Every clue passes through three stages:

```
┌─────────┐      structured parse      ┌──────────┐     candidate list     ┌───────────┐
│  Parser  │ ──────────────────────────▶│  Solvers │ ─────────────────────▶│ Evaluator │
│  (LLM)   │   clue_type, indicator,   │  (algo)  │   words matching      │  (LLM)    │
│          │   fodder, definition_side  │          │   mechanical rules    │           │
└─────────┘                            └──────────┘                       └───────────┘
```

**Parser → Solvers boundary** (input to solvers):

| Field | Type | Example |
|-------|------|---------|
| `clue_type` | string | `"anagram"` |
| `indicator` | string \| null | `"complicated"` |
| `fodder_text` | string \| null | `"The role is"` |
| `definition_side` | `"start"` \| `"end"` \| `"unknown"` | `"end"` |
| `pattern` | string | `"........."` (dots for unknowns) |

**Solvers → Evaluator boundary** (output from solvers):

| Field | Type | Example |
|-------|------|---------|
| `candidates` | list[string] | `["hoteliers"]` |
| `fodder` | string | `"theroleis"` |
| `pattern` | string | `"........."` |

The evaluator receives the original clue, the definition text, and the candidate list. It returns a ranked result with confidence scores.

## Solver Inventory

### CLI Scripts (`cryptic_skills/`)

Each solver is a standalone Python CLI script that reads arguments and writes JSON to stdout.

| Script | Clue Type | Key Arguments | Output | Data Files Used |
|--------|-----------|---------------|--------|-----------------|
| `anagram.py` | Anagram | `--fodder <letters> --pattern <pattern>` | `{"candidates": [...]}` | `words.txt` |
| `hidden.py` | Hidden word | `--fodder <phrase> --length <int> --pattern <pattern>` | `{"candidates": [...]}` | `words.txt` |
| `reversal.py` | Reversal | `--fodder <letters> --pattern <pattern>` | `{"candidates": [...]}` | `words.txt` |
| `insertion.py` | Container | `--fodder <inner> --outer <outer> --pattern <pattern>` | `{"candidates": [...]}` | `words.txt`, `abbreviations.json` |
| `charade.py` | Charade | `--components <word> ... --pattern <pattern>` | `{"candidates": [...]}` | `words.txt`, `abbreviations.json` |
| `grid_manager.py` | Grid state | `--state_file <file> --action get_pattern\|place_answer --clue <id>` | Pattern or updated grid | — |

### Extraction Tools

| Script | Purpose |
|--------|---------|
| `extract_clues_from_pdf_text.py` | Parse clue text from PDF content |
| `extract_grid_state_from_image.py` | Extract grid layout from a crossword image (vision) |
| `extract_grid_state_from_pdf_vector.py` | Extract grid layout from PDF vector graphics |
| `preprocess_pdf.py` | Prepare PDF files for downstream extraction |

### Data Files

| File | Contents |
|------|----------|
| `words.txt` | Crossword-grade English wordlist for candidate validation |
| `abbreviations.json` | Crossword abbreviations (e.g. "ship" → "SS", "doctor" → "DR") |
| `indicators.yml` | Categorised indicator word lists by clue type |
| `thesaurus.json` | Synonym lookup for definition matching and hint generation |

## Grid Orchestration as CSP

A full puzzle is a Constraint Satisfaction Problem (CSP). Crossing clues share cells, so placing one answer constrains others.

**Priority ordering:** The solver grades all clues by algorithmic certainty and tackles the strongest types first:

1. **Hidden words** — once the fodder span is identified, a sliding-window search over the dictionary is near-deterministic.
2. **Anagrams** — given correct fodder, enumeration against a pre-indexed anagram dictionary is exhaustive and fast.
3. **Initials / Acrostics** — trivial mechanical transforms once parsed.
4. **Reversals** — simple string reversal with dictionary validation.
5. **Containers, charades** — hybrid; more combinatorial but bounded by abbreviation tables.
6. **Double definitions, cryptic definitions** — heavily LLM-dependent; benefit most from crossing letters.

**Checker propagation:** Every committed answer writes letters into shared grid cells. Crossing clues immediately gain pattern constraints (e.g. `S......` → `S..R...`), which dramatically reduce their candidate space for the next sweep.

**Sweep-and-yield termination:** The solver loops over all unresolved clues. If a full sweep produces no new answers, the loop stops. This prevents infinite hallucination loops on clues the system cannot yet solve. The partial grid is yielded for human input.

## Two Modes, One Engine

The same solver layer powers two different interfaces:

```
                          ┌──────────────────────────────┐
                          │      cryptic_skills/*.py      │
                          │   (CLI solvers + data files)  │
                          └──────────┬───────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
    ┌─────────▼─────────┐ ┌─────────▼─────────┐           │
    │   Agent Mode       │ │   Tutor Mode       │           │
    │                    │ │                    │           │
    │  LLM orchestrator  │ │  Human user        │           │
    │  reads SKILL.md    │ │  interacts via      │           │
    │  invokes CLI tools │ │  React UI           │           │
    │  manages grid_     │ │                    │           │
    │  state.json        │ │  FastAPI backend    │           │
    │                    │ │  HeuristicAdapter   │           │
    │  Autonomous loop   │ │  calls same CLI     │           │
    │  over all clues    │ │  tools + optional   │           │
    │                    │ │  external LLM       │           │
    └────────────────────┘ └────────────────────┘           │
                                                            │
                          ┌─────────────────────────────────┘
                          │  Optional: CROSSWORD_RUNTIME_COMMAND
                          │  (external LLM for hints + semantic judgement)
                          └─────────────────────────────────
```

**Agent mode:** Any `SKILL.md`-compatible harness can read `SKILL.md`, drive the CLI tools, manage `grid_state.json`, and loop until the puzzle is solved or it stalls. A specific model or provider is not part of the core contract.

**Tutor mode:** A human interacts through the React frontend. The FastAPI backend provides session management, hint generation, and validation. The `HeuristicRuntimeAdapter` performs clue-type detection and calls the same CLI solvers. An optional external LLM (`CROSSWORD_RUNTIME_COMMAND`) handles semantic judgement and richer hints.

## Tutor Backend Layers

The tutor backend (`backend/app/`) is structured as four layers:

### Session API (`api/sessions.py`, `api/clues.py`)

HTTP routes and request validation. Key endpoints:
- `POST /api/sessions` — create a session from a puzzle ID
- `GET /api/sessions/{id}` — load full session state
- `POST /api/sessions/{id}/entries` — submit an answer
- `POST /api/sessions/{id}/clues/{id}/next-hint` — request next hint
- `POST /api/sessions/{id}/clues/{id}/check` — validate without committing
- `POST /api/imports/pdf` — import a puzzle from PDF

### Session Service (`services/session_service.py`)

Orchestrates business logic:
1. Receives an answer submission
2. Delegates to `GridEngine` for deterministic checker propagation
3. Delegates to `RuntimeAdapter` for validation
4. Persists updated state
5. Returns a session delta to the frontend

### Grid Engine (`services/grid_engine.py`)

Pure deterministic logic:
- Derives playable cells from grid metadata
- Applies answers to cells
- Computes crossing patterns for any clue
- Detects conflicts between overlapping entries

### HeuristicAdapter (`runtime/adapter.py`)

The runtime layer with three tiers of intelligence:

1. **Deterministic analysis** — indicator word matching, fodder extraction, clue-type detection using hardcoded indicator lists (anagram, hidden, reversal, container, initials, charade indicators).
2. **Local solver execution** — calls `cryptic_skills/*.py` CLI scripts via subprocess and collects candidates.
3. **External LLM** (optional) — if `CROSSWORD_RUNTIME_COMMAND` is set, routes `next_hint` and `semantic_judgement` operations to an external process for richer analysis.

### Hint Ladder

Hints are monotonic and per-clue, progressing through five levels:

| Level | Kind | Example |
|-------|------|---------|
| 1 | `clue_type` | "This looks like an anagram clue." |
| 2 | `structure` | "The definition is probably at the end, and 'complicated' looks like the indicator." |
| 3 | `wordplay_focus` | "The fodder looks like 'The role is', to be rearranged." |
| 4 | `candidate_space` | "Using the current pattern, the strongest local candidates are: HOTELIERS." |
| 5 | `answer_reveal` | "The strongest answer here is HOTELIERS." |

### Validation Pipeline

Answer validation follows a deterministic-first, then semantic strategy:

1. **Length check** — answer must match the clue's enumeration.
2. **Pattern check** — answer must match current crossing letters.
3. **Solver confirmation** — if the answer appears in the local solver's candidate list for a strongly-typed clue (anagram, hidden, reversal, initials), it is `confirmed` with high confidence.
4. **Wordlist check** — if the answer is a valid dictionary word, it is `plausible`.
5. **Semantic adjudication** (optional) — if an external LLM is configured, it reviews the answer against the full clue parse. A `conflict` verdict with a `symbolicFollowup` suggestion is downgraded to `plausible` when the local solver had no candidates and no fodder — this prevents hard rejections when mechanics are simply unresolved.

Validation results use three values: `confirmed`, `plausible`, `conflict`.

## Runtime Abstraction

The project separates *what capability is needed* from *which model provides it*.

### Capability Roles

| Role | Used For |
|------|----------|
| `lite` | Fast, cheap candidate generation and broad recall |
| `reasoner` | Ambiguity resolution, semantic ranking, explanation |
| `vision` | Puzzle image reading, OCR, grid-layout extraction |

### `CROSSWORD_RUNTIME_COMMAND` Boundary

The backend never calls a specific LLM API directly. Instead, it shells out to a command configured via the `CROSSWORD_RUNTIME_COMMAND` environment variable. This command receives a JSON payload on stdin and returns structured JSON on stdout.

Operations sent through this boundary:
- `next_hint` — request a hint at a specific level
- `semantic_judgement` — evaluate an answer against the clue

A separate `CROSSWORD_SEMANTIC_COMMAND` can override just the semantic adjudication path.

### Deployment Mapping

The indirection is intentional:

1. `SKILL.md` asks for a capability (e.g. `reasoner`).
2. Deployment maps that to a local alias (e.g. `crossword-reasoner`).
3. A harness-specific runtime wrapper resolves the alias to the real model, credentials, and endpoint.

This lets the solver stay portable while different environments handle their own routing, secrets, and vendor integrations. Codex is the reference harness currently documented here, but the architectural boundary is `SKILL.md` plus the structured runtime JSON contract. An example deployment config lives at `config/model-routing.example.yaml`.


