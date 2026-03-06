# Cryptic Crossword Solver: A Neuro-Symbolic Approach

The objective of this project is to create an automated solver for cryptic crosswords. 

While it is, of course, of no practical value to solve cryptic crosswords algorithmically, it serves as a highly valuable demonstration of a **Neuro-Symbolic** approach to AI: combining the semantic understanding of Large Language Models (LLMs) with the deterministic, combinatorial power of algorithmic search.

Neither an LLM nor a pure algorithmic solver can handle cryptic crosswords effectively on their own, but together they cover each other's weaknesses perfectly. For example, an anagram clue typically has indicator words ("mixed", "confused", "scrambled") that identify it as an anagram. Validating that possible solutions are anagrams of the given letters is nearly impossible for a language model due to tokenization constraints. However, it is mathematically straightforward with an algorithmic approach using wordlists and pre-calculated anagrams.

## Quick Start: Using the Solver

To solve a crossword using this Agent Skill:
1. **Initialize a Workspace**: Create a new, blank folder for your puzzle (e.g., `mkdir puzzle_83479`). This acts as an isolated sandbox for the agent to track its state.
2. **Provide the Input**: Place your crossword image or PDF inside this new workspace folder.
3. **Mount the Agent**: Point your OpenClaw or another compatible agent runtime at this project directory so it loads the Cryptic Solver `SKILL.md`.
4. **Invoke**: Tell the agent to target your workspace. Example prompt:
   > *"Using your Cryptic Crossword Solver skill, solve the puzzle found in `./puzzle_83479/crossword.pdf`. Save all your state files to that directory."*

## Installation & Deployment

This project is packaged as an **Agentic Skill Bundle**. 

### Option 1: The `.skill` Package (Recommended)
Many OpenClaw/Agentic runtimes support the `.skill` archive format (a zipped bundle containing the identity and tools).
1. Download `cryptic-solver.skill` from the repository releases (or build it locally by zipping the repository contents and renaming to `.skill`).
2. Load the `.skill` file directly into your agent runtime's Skill Manager.

### Option 2: Clone & Mount
1. **Clone the full repository** (not just the `SKILL.md`):
   ```bash
   git clone https://github.com/nikcholer/cryptic-solver.git
   ```
2. **Install local dependencies** to ensure the Python solvers have the necessary libraries:
   ```bash
   pip install -r requirements.txt
   ```
3. **Mount the Directory**: In your agent configuration, point the skill search path to the root of this repository. The `SKILL.md` file will serve as the instruction set, and the agent will invoke the scripts in `cryptic_skills/` via relative paths.

## Capability-Based Model Allocation

When this project delegates work across models, it should do so by capability role rather than provider name:

- **lite**: cheap, fast shortlist generation and broad candidate recall
- **reasoner**: ambiguity resolution, parse comparison, semantic ranking, and explanation
- **vision**: puzzle image reading, OCR, and grid-layout extraction

This keeps the workflow portable across runtimes. The runtime can map its available models onto these roles based on cost, latency, and quality.

### Deployment Mapping

The skill should stop at capability roles. Deployment is responsible for a second mapping layer:

1. `SKILL.md` asks for a capability such as `lite`, `reasoner`, or `vision`.
2. Deployment maps that capability to a local alias such as `crossword-lite`.
3. The calling agent resolves that alias to the real model identifier, credentials, endpoint, and any provider-specific options.

This indirection is intentional. It means the skill can stay portable while different environments handle their own routing, secrets, and vendor integrations.

An example deployment config lives at `config/model-routing.example.yaml`.

## The "Two-Engine" Architecture

This solver is architected as a pipeline with feedback loops, separating the semantic tasks from the raw computational tasks:

1. **The Parsing Model (the "Foreman")**:
   - **Input**: The clue, enumeration (e.g., `(5,4)`), and any known checked letters.
   - **Task**: Disambiguate the natural language to split the clue into its *Definition* and *Wordplay* components limit. Identify clue indicators (anagram indicators, hidden word indicators, etc.).
   - **Output**: Structured data (e.g., an Abstract Syntax Tree of operations) proposing likely parses to the algorithmic engine.

2. **The Algorithmic Solvers (The "Workers")**:
   - **Modules**: Pure programmatic algorithms such as `AnagramSolver`, `HiddenWordSolver`, `PatternMatcher`, or a `HomophoneEngine`.
   - **Task**: Take the structured instructions from the Parser, run heavily optimized searches against local dictionaries, and generate a list of candidate words that satisfy the mechanical constraints (length, checked letters, anagram fodder, etc.).

3. **The Evaluating Model (the "Judge")**:
   - **Input**: The original definition part of the clue and the list of candidates generated by the algorithms.
   - **Task**: Rank the candidates based on semantic similarity to the definition, preventing combinatorial explosions (like checking all charade combinations) from overwhelming the final output.

## Full Grid Orchestration: Solving the Puzzle

A complete puzzle is more than the sum of its independent clues due to the intersecting checking letters. Solving one clue drastically reduces the search space for intersecting clues. The solver orchestrates the full grid solve by treating it as a dynamic Constraint Satisfaction Problem (CSP).

### 1. Grading and The Initial Pass
Before brute-forcing everything, the system parses all clues and grades them by algorithmic certainty.
- **Highest Priority**: Hidden words, anagrams, and acrostics. Once a parsing model identifies the operational mechanism and fodder, the algorithmic solver generates a highly constrained, reliable candidate list. 
The solver tackles our toolkit's strongest clue types first to lock in high-confidence answers.

### 2. Constraining the Search Space
Every word placed in the grid generates **checked letters** for intersecting clues. This is where the algorithmic engine shines. A purely semantic clue (like a Double Definition) might initially have a search space of 40,000 words. But as intersecting letters are found (e.g., narrowed to `C.M.....`), the search space shrinks to a few dozen candidates. The LLM Evaluator only needs to rank those few remaining valid words.

### 3. Execution Pass and Termination (Graceful Yielding)
The solve process operates as a loop across all clues. The Agent should not get stuck attempting to brute-force a single clue:
1. **Sweep & Solve**: Scans all unresolved clues. Queries `grid_manager.py` for each clue's current checking-letter constraints (e.g., `S...S`).
2. **Algorithmic Execution**: The managing model routes the categorized parts to the `cryptic_skills/` CLI Python scripts for deterministic candidate generation.
3. **Commit**: If the Agent is highly confident in an algorithmic candidate, it commits it to the Grid State, unlocking new intersecting checking letters for the next sweep.
4. **Termination Condition**: To prevent infinite hallucination loops, if the Agent completes a full sweep of the remaining clues without adding any *new* answers to the grid, it abandons the loop. It immediately yields control back to the human, outputting the partial grid and asking for hints or guidance. This allows the Agent to handle novel or complex general knowledge clues without bricking the session.

---

## Clue Types and Engine Suitability

Here is a breakdown of how the Neuro-Symbolic division of labor applies to common cryptic clue types:

### 1. Anagram Clues
**Highly Algorithmic-Friendly**
- **Parsing model**: Detects the anagram indicator, identifies the exact fodder span, and confirms the definition half.
- **Multimodal Grid Mapping**: Native Agent runtimes can use Vision capabilities to "look" at an image of a crossword and mathematically map the 15x15 `x, y` geometric layout of the interlocking clues into `grid_state.json`.
- **Algorithm**: Generates anagrams, filters by enumeration/checked letters, and validates against a dictionary.
- *Pattern: Parser → Anagram Generator → Ranker*

### 2. Double-Definition Clues
**Highly LLM-Friendly**
- **Algorithm**: Enumerates candidate answers matching the word length and known checking letters.
- **Reasoner**: Deep semantic matching. Scores each candidate generated by the algorithm to see if it fits both definition-like phrases.

### 3. Hidden Clues
**Very Algorithmic-Friendly**
- **Parsing model**: Spots the oblique hidden-indicator and verifies the definition matching at the end.
- **Algorithm**: Slides a window across the clue text, finding contiguous substrings of the right length that match checked letters. 

### 4. Charades (Bits and Pieces)
**Hybrid (Algorithmic Generation, LLM Control)**
- **Parsing model**: Proposes parses (which word is the definition, which components are abbreviations vs synonyms).
- **Algorithm**: Uses tables of abbreviations and crosswordese to build candidates by concatenation.
- *Risk*: Combinatorial explosion. The managing model must prune bad components early, and the algorithmic engine requires optimized data structures (like Tries) to abandon dead-end combinations.

### 5. Start, Middle, and End (Acrostics)
**Mostly Algorithmic**
- **Parsing model**: Detects the operation ("initially", "heart of") and the target span.
- **Algorithm**: Mechanical transforms (first letters, odd letters, etc.). Generation is trivial once parsed.

### 6. Container and Contents
**Hybrid**
- **Parsing model**: Works out which chunk goes inside which, and identifies deletions or abbreviations before insertion.
- **Algorithm**: Executes the mechanical insertion transform and validates dictionary candidates.

### 7. Cryptic Definitions and All-in-Ones
**Heavily model-dependent**
- Requires world knowledge, phrase recognition, and ignoring surface misdirection.
- **Algorithm**: Mostly assists via pattern filtering, checking n-gram frequency, and verifying checking letters to limit the LLM's guess-space.

### 8. Homophones and Spoonerisms
**Hybrid (Phonetic Algorithmic)**
- **Reasoner**: Judges plausibility, selects intended synonyms, and accounts for accent-dependent loose matches ("we hear").
- **Algorithm**: Mandatory use of a phonetic engine (e.g., CMUdict, Double Metaphone) to map candidate words to phonetic codes and generate valid "sounds-like" candidates.

### 9. Reversals, Deletions, and Substitutions
**Algorithmic Transforms**
- **Parsing model**: Detects which complex operation applies (e.g., "endless" = delete last letter).
- **Algorithm**: Executes the mechanistic string manipulation and filters against valid vocabulary.