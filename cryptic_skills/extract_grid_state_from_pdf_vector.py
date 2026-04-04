#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import ContentStream

GRID_TRANSFORM = (0.9375, 0.0, 0.0, 0.9375, 540.625, 262.5)
TEXT_TRANSFORM = (3.1250002, 0.0, 0.0, 3.1250002, 540.625, 262.5)
GRID_SIZE = 15
CELL_UNITS = 100
WHITE = (1.0, 1.0, 1.0)
GLYPH_TO_DIGIT = {'>': '1', '?': '2', '@': '3', 'A': '4', 'B': '5', 'C': '6', 'D': '7', 'E': '8', 'F': '9', '=': '0'}


def extract_white_cells(page) -> set[tuple[int, int]]:
    stream = ContentStream(page.get_contents(), page.pdf)
    stack: list[tuple[tuple[float, ...], tuple[float, float, float]]] = []
    cm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    fill = (0.0, 0.0, 0.0)
    last_rect: tuple[float, float, float, float] | None = None
    white_cells: set[tuple[int, int]] = set()

    for operands, operator in stream.operations:
        op = operator.decode('latin1') if isinstance(operator, bytes) else str(operator)
        values = []
        for operand in operands:
            try:
                values.append(float(operand.as_numeric()))
            except Exception:
                values.append(str(operand))

        if op == 'q':
            stack.append((cm, fill))
        elif op == 'Q':
            cm, fill = stack.pop()
        elif op == 'cm':
            cm = tuple(round(value, 4) for value in values)
        elif op == 'rg':
            fill = tuple(round(value, 4) for value in values)
        elif op == 're' and len(values) == 4:
            last_rect = tuple(values)
        elif op == 'f' and last_rect is not None:
            x, y, w, h = last_rect
            if w == CELL_UNITS and h == CELL_UNITS and cm == GRID_TRANSFORM and fill == WHITE:
                white_cells.add((int(x // CELL_UNITS), int(y // CELL_UNITS)))
            last_rect = None

    return white_cells


def extract_number_positions(page) -> dict[int, tuple[int, int]]:
    stream = ContentStream(page.get_contents(), page.pdf)
    current_size: float | None = None
    current_tm: tuple[float, ...] | None = None
    cm: tuple[float, ...] | None = None
    glyphs_by_pos: dict[tuple[float, float], list[str]] = {}

    for operands, operator in stream.operations:
        op = operator.decode('latin1') if isinstance(operator, bytes) else str(operator)
        values = []
        for operand in operands:
            try:
                values.append(float(operand.as_numeric()))
            except Exception:
                values.append(str(operand))

        if op == 'cm':
            cm = tuple(values)
        elif op == 'Tf':
            current_size = float(values[1])
        elif op == 'Tm':
            current_tm = tuple(values)
        elif op == 'Tj' and current_size == 7.5 and current_tm is not None and cm == TEXT_TRANSFORM:
            glyph = str(values[0])
            digit = GLYPH_TO_DIGIT.get(glyph)
            if digit is None:
                continue
            pos = (float(current_tm[4]), float(current_tm[5]))
            glyphs_by_pos.setdefault(pos, []).append(digit)

    positions: dict[int, tuple[int, int]] = {}
    for (x, y), digits in glyphs_by_pos.items():
        number = int(''.join(digits))
        col = int(round((x - 1.5) / 30.0))
        row = int(round((y - 8.09375) / 30.0))
        positions[number] = (col, row)
    return positions


def build_grid_state(white_cells: set[tuple[int, int]], number_positions: dict[int, tuple[int, int]]) -> dict[str, object]:
    black = [[(col, row) not in white_cells for col in range(GRID_SIZE)] for row in range(GRID_SIZE)]
    clues: dict[str, dict[str, object]] = {}

    for number, (col, row) in sorted(number_positions.items()):
        if black[row][col]:
            continue

        starts_across = (col + 1 < GRID_SIZE and not black[row][col + 1]) and (col == 0 or black[row][col - 1])
        if starts_across:
            length = 1
            scan = col + 1
            while scan < GRID_SIZE and not black[row][scan]:
                length += 1
                scan += 1
            if length > 1:
                clues[f"{number}A"] = {
                    "x": col,
                    "y": row,
                    "length": length,
                    "direction": "Across",
                }

        starts_down = (row + 1 < GRID_SIZE and not black[row + 1][col]) and (row == 0 or black[row - 1][col])
        if starts_down:
            length = 1
            scan = row + 1
            while scan < GRID_SIZE and not black[scan][col]:
                length += 1
                scan += 1
            if length > 1:
                clues[f"{number}D"] = {
                    "x": col,
                    "y": row,
                    "length": length,
                    "direction": "Down",
                }

    return {
        "width": GRID_SIZE,
        "height": GRID_SIZE,
        "clues": clues,
        "_debug": {
            "source": "pdf-vector",
            "grid_transform": list(GRID_TRANSFORM),
            "white_cell_count": len(white_cells),
            "numbered_cells": len(number_positions),
        },
    }


def extract_grid_state_from_pdf(pdf_path: Path, page_number: int = 1) -> dict[str, object]:
    reader = PdfReader(str(pdf_path))
    page_index = page_number - 1
    if page_index < 0 or page_index >= len(reader.pages):
        raise ValueError(f'Page {page_number} is out of range for {pdf_path}')

    page = reader.pages[page_index]
    white_cells = extract_white_cells(page)
    number_positions = extract_number_positions(page)
    return build_grid_state(white_cells, number_positions)


def write_grid_state_json(payload: dict[str, object], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Telegraph-style crossword grid metadata from a born-digital PDF vector page.")
    parser.add_argument('--pdf', required=True, help='Path to the source PDF')
    parser.add_argument('--out', required=True, help='Path to write grid_state.json')
    parser.add_argument('--page', type=int, default=1, help='1-based page number to inspect')
    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()
    try:
        payload = extract_grid_state_from_pdf(pdf_path, args.page)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    write_grid_state_json(payload, out_path)
    across_count = sum(1 for clue_id in payload['clues'] if clue_id.endswith('A'))
    down_count = sum(1 for clue_id in payload['clues'] if clue_id.endswith('D'))
    print(f'Wrote {out_path}')
    print(f'Across clues: {across_count}')
    print(f'Down clues: {down_count}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
