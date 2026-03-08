#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml
from pypdf import PdfReader

DATE_LINE = re.compile(r"^\d{2} \w+ \d{4}$")
GRID_NUMBERS_LINE = re.compile(r"^[\d\s]+$")
CLUE_START = re.compile(r"^(\d+(?:,\s*\d+\s+(?:Across|Down)\s+and\s+\d+\s+(?:Across|Down))?)\s*(.+)$")
ENUM_AT_END = re.compile(r"\(([^()]+)\)\s*$")
CHAIN_SPEC = re.compile(r"^(\d+),\s*(\d+)\s+Across\s+and\s+(\d+)\s+Down$", re.IGNORECASE)
SKIP_LINES = {"Across", "Down", "PRIZE CRYPTIC", "NO. 31,181", "PRIZE CRYPTIC NO. 31,181"}


def cleaned_lines(page) -> list[str]:
    lines: list[str] = []
    for raw_line in page.extract_text().splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue
        if DATE_LINE.match(line):
            continue
        if GRID_NUMBERS_LINE.match(line):
            continue
        if line in {"PRIZE CRYPTIC NO. 31,181"}:
            continue
        lines.append(line)
    return lines


def split_sections(lines: list[str]) -> tuple[list[str], list[str]]:
    try:
        across_index = lines.index("Across")
    except ValueError as exc:
        raise SystemExit("Could not find 'Across' heading in extracted PDF text") from exc

    try:
        down_index = lines.index("Down", across_index + 1)
    except ValueError:
        down_index = len(lines)

    # Telegraph export order on this sample is: Across clues, Across heading, Down clues, Down heading.
    across_lines = [line for line in lines[:across_index] if line not in SKIP_LINES]
    down_lines = [line for line in lines[across_index + 1 : down_index] if line not in SKIP_LINES]
    return across_lines, down_lines


def parse_section(lines: list[str], direction: str) -> dict[str, dict[str, object]]:
    entries: list[tuple[str, str]] = []
    current_number: str | None = None
    current_parts: list[str] = []
    for line in lines:
        match = CLUE_START.match(line)
        if match:
            if current_number is not None:
                entries.append((current_number, " ".join(current_parts).strip()))
            current_number = match.group(1)
            current_parts = [match.group(2).strip()]
        else:
            if current_number is None:
                continue
            current_parts.append(line)
    if current_number is not None:
        entries.append((current_number, " ".join(current_parts).strip()))

    parsed: dict[str, dict[str, object]] = {}
    suffix = "A" if direction == "across" else "D"
    for number_spec, body in entries:
        key_number = number_spec.split(",", 1)[0].strip()
        clue_id = f"{int(key_number)}{suffix}"
        enum_match = ENUM_AT_END.search(body)
        enum = f"({enum_match.group(1)})" if enum_match else None
        clue = body[: enum_match.start()].strip() if enum_match else body.strip()
        payload: dict[str, object] = {"clue": clue}
        chain = CHAIN_SPEC.match(number_spec)
        if chain:
            payload["linked_entries"] = [
                clue_id,
                f"{int(chain.group(2))}A",
                f"{int(chain.group(3))}D",
            ]
        if enum:
            payload["enum"] = enum
        parsed[clue_id] = payload
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Telegraph-style crossword clues from a born-digital PDF.")
    parser.add_argument("--pdf", required=True, help="Path to the source PDF")
    parser.add_argument("--out", required=True, help="Path to write clues.yaml")
    parser.add_argument("--page", type=int, default=1, help="1-based page number to extract from")
    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()
    reader = PdfReader(str(pdf_path))
    page_index = args.page - 1
    if page_index < 0 or page_index >= len(reader.pages):
        raise SystemExit(f"Page {args.page} is out of range for {pdf_path}")

    lines = cleaned_lines(reader.pages[page_index])
    across_lines, down_lines = split_sections(lines)
    payload = {
        "across": parse_section(across_lines, "across"),
        "down": parse_section(down_lines, "down"),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Across clues: {len(payload['across'])}")
    print(f"Down clues: {len(payload['down'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
