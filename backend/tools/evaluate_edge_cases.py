from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.runtime.adapter import HeuristicRuntimeAdapter, StubRuntimeAdapter  # noqa: E402
from app.runtime.payloads import build_next_hint_request, build_semantic_judgement_request  # noqa: E402
from app.services.grid_engine import GridEngine  # noqa: E402
from app.services.puzzle_loader import PuzzleLoader  # noqa: E402
from app.services.session_service import SessionService  # noqa: E402
from app.stores.puzzle_store import build_puzzle_store  # noqa: E402
from app.stores.session_store import build_session_store  # noqa: E402


DEFAULT_CASES = [
    {
        "clue_id": "3D",
        "family": "alternating",
        "note": "Letter-selection clue that the local heuristic tends to misclassify.",
    },
    {
        "clue_id": "12A",
        "family": "hidden",
        "note": "Straight hidden clue used as a control case.",
    },
    {
        "clue_id": "4D",
        "family": "anagram",
        "note": "Obvious anagram used as a control case.",
    },
    {
        "clue_id": "1D",
        "family": "charade_or_split",
        "note": "Likely split clue with definition ambiguity.",
    },
    {
        "clue_id": "17D",
        "family": "charade_or_container",
        "note": "Structure depends on where the definition boundary falls.",
    },
    {
        "clue_id": "23D",
        "family": "reversal_or_charade",
        "note": "Surface strongly invites multiple parses.",
    },
]


@dataclass
class RuntimeCallResult:
    returncode: int
    stdout: str
    stderr: str
    parsed: dict[str, Any] | None


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    loader = PuzzleLoader(build_puzzle_store(REPO_ROOT))
    puzzle = loader.load_puzzle(args.puzzle_id)
    adapter = HeuristicRuntimeAdapter(REPO_ROOT)
    grid_state = json.loads((REPO_ROOT / "samples" / args.puzzle_id / "grid_state.json").read_text(encoding="utf-8"))
    placed_answers = {key.upper(): value.upper() for key, value in grid_state.get("placed_answers", {}).items()}
    session = build_reference_session(puzzle, placed_answers)

    cases = load_cases(args.cases_file)
    wrapper = REPO_ROOT / "backend" / "runtime_wrappers" / "codex_runtime.py"

    profiles = build_profiles(args.include_codex_53)
    results = []

    for case in cases:
        clue_id = case["clue_id"].upper()
        clue = puzzle.clues[clue_id]
        pattern = "." * clue.answer_length
        analysis = adapter._analyze_clue(clue, pattern)
        answer = placed_answers.get(clue_id, "")
        hint_request = build_next_hint_request(puzzle, session, clue, pattern, 1, analysis)
        semantic_request = build_semantic_judgement_request(
            puzzle,
            session,
            clue,
            analysis,
            answer,
            {
                "result": "confirmed",
                "reason": "Mechanical parse looks strong.",
                "confidence": 0.9,
            },
        )
        results.append(
            {
                "clueId": clue_id,
                "clue": clue.clue,
                "enumeration": clue.enum,
                "family": case["family"],
                "note": case["note"],
                "answer": answer,
                "heuristic": {
                    "clueType": analysis.clue_type,
                    "definitionSide": analysis.definition_side,
                    "definitionText": analysis.definition_text,
                    "indicator": analysis.indicator,
                    "fodderText": analysis.fodder_text,
                    "solverCandidates": analysis.solver_candidates[:5],
                },
                "profiles": {
                    profile["name"]: {
                        "hint": asdict(invoke_wrapper(wrapper, hint_request, profile["env"])),
                        "semantic": asdict(invoke_wrapper(wrapper, semantic_request, profile["env"])),
                    }
                    for profile in profiles
                },
            }
        )

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(render_markdown(results, profiles))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate runtime behavior on a small edge-case crossword suite.")
    parser.add_argument("--puzzle-id", default="cryptic-2026-03-03")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--cases-file", help="Optional JSON file containing case objects with clue_id/family/note.")
    parser.add_argument("--include-codex-53", action="store_true", help="Include gpt-5.3-codex low as a third profile.")
    return parser


def load_cases(cases_file: str | None) -> list[dict[str, str]]:
    if not cases_file:
        return DEFAULT_CASES
    path = Path(cases_file)
    return json.loads(path.read_text(encoding="utf-8"))


def build_profiles(include_codex_53: bool) -> list[dict[str, Any]]:
    profiles = [
        {
            "name": "mini",
            "env": {
                "CODEX_MODEL": "gpt-5-codex-mini",
            },
        },
        {
            "name": "reasoner-low",
            "env": {
                "CODEX_MODEL": "gpt-5.4",
                "CODEX_REASONING_EFFORT": "low",
            },
        },
    ]
    if include_codex_53:
        profiles.append(
            {
                "name": "codex-53-low",
                "env": {
                    "CODEX_MODEL": "gpt-5.3-codex",
                    "CODEX_REASONING_EFFORT": "low",
                },
            }
        )
    return profiles


def build_reference_session(puzzle, placed_answers: dict[str, str]):
    os.environ.setdefault("CROSSWORD_SESSION_STORE", "filesystem")
    os.environ.setdefault("CROSSWORD_SESSION_FILESYSTEM_ROOT", str(REPO_ROOT / "backend_data" / "edge-case-eval"))
    service = SessionService(build_session_store(REPO_ROOT), GridEngine(), StubRuntimeAdapter())
    session = service.create_session(puzzle)
    for clue_id, answer in placed_answers.items():
        if clue_id not in puzzle.clues:
            continue
        session.entries[clue_id] = service.grid_engine.make_entry_record(answer, "confirmed")
    rebuilt_cells = service.grid_engine.rebuild_cells_from_entries(puzzle, session)
    service.grid_engine.update_session_from_cells(puzzle, session, rebuilt_cells)
    return session


def resolve_codex_runtime_executable(env: dict[str, str]) -> str | None:
    explicit = env.get("CODEX_RUNTIME_EXECUTABLE", "").strip()
    if explicit:
        return explicit
    return None


def invoke_wrapper(wrapper: Path, payload: Any, env_patch: dict[str, str]) -> RuntimeCallResult:
    env = os.environ.copy()
    env.update(env_patch)
    runtime_executable = resolve_codex_runtime_executable(env)
    if not runtime_executable:
        return RuntimeCallResult(
            returncode=127,
            stdout="",
            stderr="Codex runtime executable not configured. Set CODEX_RUNTIME_EXECUTABLE to enable wrapper evaluation.",
            parsed=None,
        )
    env["CODEX_RUNTIME_EXECUTABLE"] = runtime_executable
    env.setdefault("CODEX_RUNTIME_TIMEOUT_SECONDS", "10")
    completed = subprocess.run(
        [sys.executable, str(wrapper)],
        input=payload.model_dump_json(),
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        check=False,
    )
    parsed = None
    stdout = completed.stdout.strip()
    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            parsed = None
    return RuntimeCallResult(
        returncode=completed.returncode,
        stdout=stdout,
        stderr=completed.stderr.strip(),
        parsed=parsed,
    )


def render_markdown(results: list[dict[str, Any]], profiles: list[dict[str, Any]]) -> str:
    lines = [
        "# Edge-Case Runtime Evaluation",
        "",
        "Profiles:",
    ]
    for profile in profiles:
        model = profile["env"]["CODEX_MODEL"]
        effort = profile["env"].get("CODEX_REASONING_EFFORT", "default")
        lines.append(f"- `{profile['name']}`: model=`{model}`, reasoning_effort=`{effort}`")
    lines.append("")

    for result in results:
        lines.extend(
            [
                f"## {result['clueId']} {result['family']}",
                "",
                f"- Clue: {result['clue']} {result['enumeration']}",
                f"- Answer: `{result['answer']}`",
                f"- Note: {result['note']}",
                f"- Heuristic: clueType=`{result['heuristic']['clueType']}`, "
                f"definitionSide=`{result['heuristic']['definitionSide']}`, "
                f"indicator=`{result['heuristic']['indicator']}`",
                "",
            ]
        )
        for profile in profiles:
            name = profile["name"]
            profile_result = result["profiles"][name]
            lines.append(f"### {name}")
            lines.append("")
            lines.append(f"- Hint: {summarize_call(profile_result['hint'])}")
            lines.append(f"- Semantic: {summarize_call(profile_result['semantic'])}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def summarize_call(call: dict[str, Any]) -> str:
    if call["returncode"] != 0:
        return f"FAILED rc={call['returncode']}"
    parsed = call["parsed"]
    if parsed is None:
        return "No structured JSON returned."
    if "hints" in parsed:
        hints = parsed.get("hints") or []
        if hints:
            highlight = hints[min(1, len(hints) - 1)]
            return f"{highlight['kind']}: {highlight['text']}"
        return "Hint response contained no hints."
    return f"{parsed['result']}: {parsed['reason']}"


if __name__ == "__main__":
    raise SystemExit(main())
