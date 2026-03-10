*Status: Roadmap (in progress). Tracks planned improvements to `SKILL.md` for reliability, safety, and determinism. Unchecked items are planned.*

# Agent Instruction Quality Improvement Plan

## Purpose
Raise the reliability of prompt/skill-like instruction documents in this repo by adding explicit policies for:
- Hallucination resistance
- Idempotency and rerun safety
- Ambiguity handling
- Security and privacy defaults
- Dependency and compatibility declarations

This plan is intentionally opinionated: unclear instructions should fail safe, not "try harder".

## Goals
1. Make agent behavior deterministic enough to rerun safely.
2. Reduce fabricated outputs, made-up fields, and silent assumption drift.
3. Standardize how uncertainty is surfaced to the user.
4. Prevent accidental data leakage or unsafe command execution.
5. Make runtime prerequisites and supported environments explicit.

## Current Gaps (Inferred From Repo Scan)
Based on `SKILL.md` and `README.md`:
- Strong: workflow-level guidance exists (stage-based solving, termination condition, tool-first solving).
- Gap: no explicit "do not invent fields" contract for structured artifacts (`clues.yaml`, `grid_state.json`).
- Gap: no canonical output schema for intermediate/final responses (status, evidence, confidence, unresolved reasons).
- Gap: ambiguity policy is implicit; there is no mandatory behavior for low-confidence clue parsing.
- Gap: idempotency/rerun behavior is not defined (how to handle existing files, partial state, retries, or duplicate writes).
- Gap: security/privacy defaults are largely absent (file access boundaries, network defaults, sensitive content handling).
- Gap: dependency compatibility matrix is not declared (Python version, tested OS/shell assumptions, deterministic wordlist versioning).
- Gap: command safety contract is missing (what commands are prohibited, how destructive operations are gated).

## Recommended Standard Sections For Instruction Docs
Add these sections to `SKILL.md` (and mirror summaries in `README.md`):

1. **Execution Contract**
- Inputs accepted
- Files created/updated
- Output schema
- Success/failure criteria

2. **Ambiguity & Uncertainty Policy**
- Required confidence thresholds
- Allowed assumptions
- Escalation path for unclear clues/inputs

3. **Idempotency & Rerun Safety**
- File-write semantics (`create-if-missing`, `atomic replace`, `append forbidden` unless specified)
- Resume semantics from partial state
- Duplicate operation protections

4. **Hallucination Resistance Rules**
- Evidence requirements before committing answers
- No fabricated tool outputs or dictionary membership
- Claim-to-evidence mapping requirement

5. **Data Handling & Privacy Defaults**
- Local-only processing default
- Sensitive data minimization/redaction
- Retention policy for generated artifacts/logs

6. **Security Defaults**
- Command allowlist/denylist
- Prohibition of destructive operations without explicit user confirmation
- Network access policy default (off unless requested)

7. **Dependency & Compatibility Declaration**
- Required Python/runtime versions
- Library versions and lock strategy
- Platform assumptions and known unsupported environments

8. **Observability & Audit Trail**
- Required run summary format
- Decision log fields for unresolved clues
- Error categories and retry annotations

## Copy-Paste Policy Blocks
Use these snippets verbatim or with minimal edits.

### Ambiguity Policy
```md
## Ambiguity Policy
- If clue interpretation is ambiguous and no parse is >= 0.75 confidence, do not commit an answer.
- Produce up to 3 candidate parses, each with: `parse`, `indicator_evidence`, `tool_to_call`, `confidence`.
- Ask one targeted clarification question or mark clue as `blocked_ambiguity` and continue other clues.
- Never treat missing user input as consent for risky assumptions.
```

### Idempotency Policy
```md
## Idempotency Policy
- Re-running the same task against the same workspace must not duplicate or corrupt state.
- Writes to `clues.yaml` and `grid_state.json` must be atomic replace operations.
- Before writing, load existing state and perform a semantic diff; if no change, skip write.
- `place_answer` must be no-op when the same answer already exists for that clue.
- On partial failure, leave existing valid state intact and emit a recovery hint.
```

### Data Handling Policy
```md
## Data Handling
- Default to local file processing only; do not exfiltrate puzzle/user data.
- Log only operational metadata (file paths, clue ids, timings), not full sensitive content unless required.
- Redact secrets/tokens if encountered in files or command output.
- Retain generated artifacts only in the designated workspace directory.
```

### No-Inventing-Fields Policy
```md
## No-Inventing-Fields
- Do not add undocumented keys to YAML/JSON outputs.
- If a required field is unavailable, set it to `null` and add a `missing_reason` field only if the schema defines it.
- Do not fabricate tool results, dictionary matches, coordinates, or clue metadata.
- Every committed answer must reference at least one concrete evidence source (pattern match, solver output, or crossing letters).
```

### Output Contract
```md
## Output Contract
Final response must include:
1. `status`: `complete` | `partial` | `blocked`
2. `solved_clues`: list of `{id, answer, confidence, evidence}`
3. `unsolved_clues`: list of `{id, pattern, reason}`
4. `files_updated`: list of workspace-relative paths
5. `next_action`: one concise instruction for user or next pass

If `status != complete`, include `blocking_reason` with concrete remediation.
```

### Security Default Policy
```md
## Security Defaults
- Never run destructive shell commands (`rm -rf`, force-reset, mass overwrite) without explicit user approval.
- Restrict operations to the current workspace unless user explicitly broadens scope.
- Treat all external inputs as untrusted; validate file format and expected keys before processing.
- Network access is disabled by default; enable only when task explicitly requires it.
```

### Dependency & Compatibility Block
```md
## Dependency and Compatibility
- Python: 3.10+ (tested on 3.11)
- OS: Linux/macOS tested; Windows unverified
- Required files: `cryptic_skills/words.txt`, `cryptic_skills/indicators.yml`, `cryptic_skills/abbreviations.json`
- Determinism note: candidate ordering must be stable for identical inputs
- Versioning: bump skill metadata version when output schema or policy semantics change
```

## Suggested `SKILL.md` Structure (Template)
1. Identity and Scope
2. Execution Contract
3. Tooling Interface
4. Hallucination Resistance
5. Ambiguity Policy
6. Idempotency Policy
7. Data Handling & Security Defaults
8. Dependency & Compatibility
9. Failure Modes and Recovery
10. Output Contract

## Staged Rollout Checklist

### Stage 0: Baseline (Day 0)
- [ ] Create a short "Instruction Quality Standard" section in `README.md` linking required policy blocks.
- [ ] Add `Execution Contract` and `Output Contract` to `SKILL.md`.
- [ ] Freeze a minimal schema for `clues.yaml` and `grid_state.json`.

### Stage 1: Safety and Determinism (Week 1)
- [ ] Add `Ambiguity Policy`, `No-Inventing-Fields`, and `Idempotency Policy` blocks to `SKILL.md`.
- [ ] Update Python tools to return stable, machine-readable output where needed.
- [ ] Ensure writes are atomic and no-op on semantic no-change.

### Stage 2: Security/Privacy Hardening (Week 1-2)
- [ ] Add `Data Handling` and `Security Defaults` sections to `SKILL.md` and `README.md`.
- [ ] Document command restrictions and workspace boundaries.
- [ ] Add a short redaction guideline for logs/diagnostics.

### Stage 3: Compatibility and Governance (Week 2)
- [ ] Add dependency/version compatibility matrix to `README.md`.
- [ ] Define version bump rules for instruction contract changes.
- [ ] Add a lightweight review checklist for any prompt/skill doc PR.

### Stage 4: Verification (Week 2+)
- [ ] Add replay tests: same input workspace run twice yields identical outputs.
- [ ] Add ambiguity tests: intentionally underspecified clues produce `blocked_ambiguity`, not guessed answers.
- [ ] Add schema conformance checks for agent-produced YAML/JSON artifacts.

## Acceptance Criteria
- New contributors can implement an instruction doc that is safe by default without tribal knowledge.
- Re-running solver workflows in the same workspace is non-destructive and deterministic.
- Ambiguous inputs reliably surface as explicit uncertainty instead of silent guesses.
- Outputs are parseable and stable across runs.
