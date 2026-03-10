*Status: Implemented. This is the original design specification for the tutor backend. The implementation lives in `backend/app/`. Some planned items (SQLite phase-2) are not yet built.*

# Interactive Tutor Backend Design

## Goal

Provide a backend that can support a single-page crossword tutor UI where the user fills answers, requests staged hints, and gets immediate checker-aware feedback.

The backend must be the source of truth for live puzzle sessions. The agent runtime is an analysis dependency, not the system of record.

## Responsibilities Split

### Backend Owns

- session lifecycle
- puzzle state persistence
- user-entered answers and cell letters
- checker propagation and pattern recomputation
- clue status transitions
- hint history shown to the user
- validation result persistence
- runtime invocation orchestration
- API response shaping

### Agent Runtime Owns

- clue interpretation
- staged hint generation
- semantic validation of candidate answers
- parse/ranking of plausible candidates
- clue re-analysis under new patterns

### Agent Runtime Does Not Own

- authentication
- session persistence
- credentials and provider routing
- clue hint progression policy storage
- browser-facing response formatting
- conflict resolution between concurrent user edits

## Recommended Stack

Use Python for the backend.

Reasoning:
- the repo already contains Python crossword tooling in `cryptic_skills/`
- local solver calls are easier to keep in-process or near-process
- the future skill/runtime adapter can stay close to the existing Python scripts and workspace model

Recommended framework: FastAPI.

Reasons:
- typed request and response models
- simple async route handling
- easy SPA integration
- straightforward separation between deterministic services and runtime adapters

## Top-Level Modules

### 1. Session API Layer

Purpose: HTTP routes, request validation, response models.

Suggested package layout:

```text
backend/
  app/
    main.py
    api/
      sessions.py
      clues.py
    models/
      session.py
      clue.py
      responses.py
```

### 2. Crossword Engine

Purpose: deterministic local logic.

Responsibilities:
- derive playable cells from grid metadata
- apply clue answers to cells
- compute crossing patterns for any clue
- detect conflicts between overlapping entries
- enumerate affected clues after a fill
- maintain clue statuses such as untouched, in_progress, plausible, confirmed, conflict

Suggested package layout:

```text
backend/
  app/
    services/
      grid_engine.py
      session_service.py
      validation_service.py
```

### 3. Agent Gateway

Purpose: isolate the runtime dependency.

Responsibilities:
- build operation-specific runtime payloads
- select capability role required by operation
- call runtime adapter
- parse structured runtime output
- convert runtime failures into stable backend errors

Suggested package layout:

```text
backend/
  app/
    runtime/
      adapter.py
      payloads.py
      schemas.py
```

### 4. Persistence Layer

Purpose: store puzzle definitions and live session state.

Start simple:
- puzzle definitions from files already in repo
- session state from JSON files or SQLite

Recommended progression:
- phase 1: filesystem-backed sessions for fast iteration
- phase 2: SQLite for durability and concurrency

## Session Model

The session model should be clue-centric and cell-centric at the same time.

```json
{
  "sessionId": "sess_123",
  "puzzleId": "cryptic-2026-03-03",
  "selectedClueId": "14D",
  "cells": {
    "4,6": "S",
    "4,7": "O"
  },
  "entries": {
    "14D": {
      "answer": "SOMETHING",
      "source": "user",
      "status": "plausible",
      "updatedAt": "2026-03-06T12:00:00Z"
    }
  },
  "clueStates": {
    "14D": {
      "status": "in_progress",
      "currentPattern": "S....I...",
      "hintLevelShown": 2,
      "hints": [
        {
          "level": 1,
          "kind": "clue_type",
          "text": "This looks like an anagram."
        }
      ],
      "validation": {
        "result": "plausible",
        "reason": "Fits crossings, parse not yet confirmed."
      }
    }
  }
}
```

## Public Status Vocabulary

### Clue Status

Use these statuses in the backend and API:
- `untouched`
- `in_progress`
- `plausible`
- `confirmed`
- `conflict`

### Validation Result

Use exactly three public validation outcomes:
- `confirmed`
- `plausible`
- `conflict`

Rationale:
- avoids false certainty
- lets the tutor be supportive without overclaiming
- preserves room for user-led solving under uncertainty

## Symbolic Follow-up

When the semantic adjudicator (external LLM) returns a `conflict` verdict but also suggests a targeted next step via `symbolicFollowup`, the backend downgrades the result to `plausible` — but only when the local heuristic engine had no solver candidates and no identified fodder text. This prevents a hard rejection when the mechanics are simply unresolved rather than provably wrong.

The downgrade is applied in a single place: `HeuristicRuntimeAdapter._apply_semantic_judgement()`. The adjudicator itself returns the raw verdict; policy is not mixed into the gateway layer.

The `symbolicFollowup` string (e.g. "Try inserting KE into flower names") is persisted on the `ValidationRecord` and forwarded to the frontend, where `ClueWorkspace` renders it as a "Suggested next step" beneath the validation card. This gives the user actionable guidance when the tutor cannot yet confirm or reject an answer.

`symbolicFollowup` is `null` unless the adjudicator is explicitly suggesting a targeted symbolic search such as testing an insertion, anagram fodder, hidden-answer span, or letter-selection pattern.

## Hint Ladder

Hints are monotonic and per-clue.

Levels:
1. `clue_type`
2. `structure`
3. `wordplay_focus`
4. `candidate_space`
5. `answer_reveal`

The backend stores which level has already been shown and only asks the runtime for the next stage.

## API Contract

All frontend communication goes through the backend.

### POST `/api/sessions`

Create a live session.

Request:

```json
{
  "puzzleId": "cryptic-2026-03-03"
}
```

Response:

```json
{
  "sessionId": "sess_123",
  "puzzle": {
    "grid": {
      "width": 15,
      "height": 15,
      "clues": {}
    },
    "clues": {}
  },
  "sessionState": {
    "selectedClueId": null,
    "cells": {},
    "entries": {},
    "clueStates": {}
  }
}
```

### GET `/api/sessions/{sessionId}`

Return full live session state for SPA hydration.

### POST `/api/sessions/{sessionId}/select-clue`

Request:

```json
{
  "clueId": "14D"
}
```

Response:

```json
{
  "selectedClueId": "14D"
}
```

### POST `/api/sessions/{sessionId}/entries`

Submit or overwrite a clue answer.

Request:

```json
{
  "clueId": "14D",
  "answer": "SOMETHING"
}
```

Response:

```json
{
  "clueId": "14D",
  "validation": {
    "result": "plausible",
    "reason": "Fits enumeration and current crossings."
  },
  "sessionDelta": {
    "updatedCells": {
      "4,6": "S",
      "4,7": "O"
    },
    "updatedPatterns": {
      "10A": "S..R...",
      "16D": "..M...."
    },
    "affectedClues": ["10A", "16D"]
  }
}
```

Behavior:
- backend first applies deterministic checker propagation
- backend then invokes semantic validation for the submitted clue
- backend persists the entry and updated clue states

### POST `/api/sessions/{sessionId}/clues/{clueId}/check`

Check an answer without fully committing it as the session answer.

Request:

```json
{
  "answer": "SOMETHING"
}
```

Response:

```json
{
  "clueId": "14D",
  "result": "confirmed",
  "reason": "Matches pattern and a consistent parse was found."
}
```

### POST `/api/sessions/{sessionId}/clues/{clueId}/next-hint`

Return only the next hint stage for that clue.

Request:

```json
{
  "mode": "incremental"
}
```

Response:

```json
{
  "clueId": "14D",
  "hintLevel": 2,
  "kind": "structure",
  "text": "The definition is probably at the end.",
  "updatedHintHistory": [
    {
      "level": 1,
      "kind": "clue_type"
    },
    {
      "level": 2,
      "kind": "structure"
    }
  ]
}
```

### POST `/api/sessions/{sessionId}/reanalyze-affected`

Optional endpoint for proactive strengthening of clue guidance after new checkers appear.

Request:

```json
{
  "clueIds": ["10A", "16D"]
}
```

Response:

```json
{
  "clueUpdates": [
    {
      "clueId": "10A",
      "currentPattern": "S..R...",
      "hintAvailability": 3
    }
  ]
}
```

This can remain synchronous at first and become a background job later.

## Runtime Gateway Contract

The backend should never expose raw runtime prose to the browser.

All runtime calls must request structured output.

### Example Operation: `next_hint`

Runtime payload:

```json
{
  "skill": "cryptic-crossword-solver",
  "mode": "hint",
  "operation": "next_hint",
  "capability": "reasoner",
  "context": {
    "clueId": "14D",
    "clue": "Prove his table's wobbly",
    "enumeration": "(9)",
    "pattern": "E...B....",
    "hintLevelAlreadyShown": 1,
    "crossings": {
      "2": "E",
      "5": "B"
    }
  },
  "response_format": "json"
}
```

Expected runtime response:

```json
{
  "clueId": "14D",
  "hintLevel": 2,
  "kind": "structure",
  "text": "This looks like an anagram; the indicator appears to be 'wobbly'.",
  "confidence": 0.86
}
```

### Example Operation: `validate_answer`

Runtime payload:

```json
{
  "skill": "cryptic-crossword-solver",
  "mode": "validate_answer",
  "operation": "validate_answer",
  "capability": "reasoner",
  "context": {
    "clueId": "14D",
    "clue": "Prove his table's wobbly",
    "enumeration": "(9)",
    "patternBefore": "E...B....",
    "proposedAnswer": "ESTABLISH",
    "crossings": {
      "1": "E",
      "5": "B"
    }
  },
  "response_format": "json"
}
```

Expected runtime response:

```json
{
  "clueId": "14D",
  "result": "confirmed",
  "reason": "Matches definition and a strong anagram parse.",
  "confidence": 0.93
}
```

## Internal Service Flow

### Submit Entry Flow

1. receive clue answer from SPA
2. load session and puzzle metadata
3. apply answer to the grid deterministically
4. compute crossing effects and affected clues
5. call runtime for semantic validation of the submitted clue
6. persist cells, entry state, clue state, and validation outcome
7. return a small session delta to the SPA

### Next Hint Flow

1. receive clue id
2. load current clue state and current pattern
3. determine next hint level to request
4. call runtime for exactly that next hint level
5. persist hint history
6. return that single hint item to the SPA

## Persistence Strategy

### Phase 1

Filesystem-backed sessions.

Suggested layout:

```text
backend_data/
  sessions/
    sess_123/
      session.json
```

Advantages:
- easy to inspect while designing the product
- matches current workspace-heavy repo style
- low implementation cost

### Phase 2

Move session state to SQLite.

Recommended tables:
- `sessions`
- `session_cells`
- `session_entries`
- `session_clue_states`
- `session_hints`
- `session_events`

## Concurrency Rules

Keep them simple initially.

- one active editor per session
- last write wins for clue entries
- optimistic version field on session state
- reject stale writes if version mismatch appears

## Error Model

Frontend should receive stable backend error types, never raw runtime stack traces.

Suggested error codes:
- `session_not_found`
- `clue_not_found`
- `invalid_answer_length`
- `grid_conflict`
- `runtime_unavailable`
- `runtime_invalid_response`
- `hint_limit_reached`

## SPA-Facing Principle

The SPA should not need to know anything about skill prompts, provider routing, or runtime internals.

It should only know:
- session state
- clue state
- hint items
- validation outcomes
- grid deltas

## Suggested Build Order

1. implement puzzle/session persistence
2. implement deterministic grid engine
3. implement `POST /sessions`, `GET /sessions/{id}`, `POST /entries`
4. wire clue validation through an adapter interface with a fake runtime first
5. add `next-hint`
6. replace fake runtime with actual skill/runtime integration
7. add background re-analysis for affected clues if needed

## Immediate Next Step

Create the backend skeleton with:
- FastAPI app
- Pydantic models for session and API contracts
- filesystem-backed session store
- pure Python grid/checker propagation service
- runtime adapter interface with a stub implementation

That is the minimal backend foundation the SPA can build against.