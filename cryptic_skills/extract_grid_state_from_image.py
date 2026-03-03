#!/usr/bin/env python3
"""Extract a `grid_state.json`-compatible structure from a grid-only image.

Goal
----
Provide a deterministic path for generating `grid_state.json` from *any* reasonably
cropped image of a standard NxN crossword grid (default 15x15).

This intentionally does **not** attempt to OCR clue numbers.
Instead it uses standard crossword numbering rules:
- Number a white cell if it begins an Across entry and/or a Down entry.
- Across entry start: cell is white; (left is border/black); (right is white)
- Down entry start: cell is white; (above is border/black); (below is white)

Inputs
------
- A grid-only image (PNG/JPG) where black squares are filled and grid lines are dark.
  A small perimeter margin is OK.

Outputs
-------
- JSON containing:
  {
    "width": N,
    "height": N,
    "clues": {
      "1A": {"x":0,"y":0,"length":7,"direction":"Across"},
      "1D": {"x":0,"y":0,"length":7,"direction":"Down"},
      ...
    }
  }

By default we do not include extra debug keys (to keep the artifact clean).
Use --debug to include inferred grid lines to aid troubleshooting.

Usage
-----
  python cryptic_skills/extract_grid_state_from_image.py \
    --image ./puzzle_12345/grid_only.png \
    --out   ./puzzle_12345/grid_state.json

"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def _smooth(vals: list[int], k: int = 11) -> list[float]:
    k = max(1, k)
    half = k // 2
    out: list[float] = []
    for i in range(len(vals)):
        s = 0
        cnt = 0
        for j in range(i - half, i + half + 1):
            if 0 <= j < len(vals):
                s += vals[j]
                cnt += 1
        out.append(s / max(1, cnt))
    return out


def _find_grid_lines(profile: list[int], n: int, min_sep: int) -> list[int]:
    """Pick (n+1) strongest peaks in a dark-pixel profile with min separation."""
    sm = _smooth(profile, k=11)

    # Candidate peaks = local maxima
    peaks: list[tuple[float, int]] = []
    for i in range(1, len(sm) - 1):
        if sm[i] >= sm[i - 1] and sm[i] >= sm[i + 1]:
            peaks.append((sm[i], i))

    peaks.sort(reverse=True)

    chosen: list[int] = []
    for _, idx in peaks:
        if all(abs(idx - c) >= min_sep for c in chosen):
            chosen.append(idx)
        if len(chosen) >= (n + 1):
            break

    chosen.sort()

    # Fallback: evenly spaced if peak picking fails
    if len(chosen) < (n + 1):
        step = (len(profile) - 1) / n
        chosen = [int(round(i * step)) for i in range(n + 1)]

    return chosen


def _classify_cells(im: Image.Image, vlines: list[int], hlines: list[int], thr: int) -> list[list[bool]]:
    """Return black[r][c] for n x n cells."""
    n = len(vlines) - 1
    pix = im.load()
    W, H = im.size

    black = [[False] * n for _ in range(n)]
    for r in range(n):
        y0, y1 = hlines[r], hlines[r + 1]
        for c in range(n):
            x0, x1 = vlines[c], vlines[c + 1]

            # Sample inside the cell to avoid grid lines.
            mx = max(2, int((x1 - x0) * 0.18))
            my = max(2, int((y1 - y0) * 0.18))
            sx0 = min(max(x0 + mx, 0), W - 1)
            sx1 = min(max(x1 - mx, 0), W)
            sy0 = min(max(y0 + my, 0), H - 1)
            sy1 = min(max(y1 - my, 0), H)

            if sx1 <= sx0 + 1 or sy1 <= sy0 + 1:
                cx = int((x0 + x1) / 2)
                cy = int((y0 + y1) / 2)
                avg = pix[cx, cy]
            else:
                s = 0
                samples = 0
                stepx = max(1, (sx1 - sx0) // 6)
                stepy = max(1, (sy1 - sy0) // 6)
                for yy in range(sy0, sy1, stepy):
                    for xx in range(sx0, sx1, stepx):
                        s += pix[xx, yy]
                        samples += 1
                avg = s / max(1, samples)

            black[r][c] = avg < thr

    return black


def _entries_from_black(black: list[list[bool]]):
    n = len(black)

    # standard numbering
    num = 0
    cell_number = [[0] * n for _ in range(n)]

    for r in range(n):
        for c in range(n):
            if black[r][c]:
                continue
            starts_across = (c == 0 or black[r][c - 1]) and (c + 1 < n and not black[r][c + 1])
            starts_down = (r == 0 or black[r - 1][c]) and (r + 1 < n and not black[r + 1][c])
            if starts_across or starts_down:
                num += 1
                cell_number[r][c] = num

    clues: dict[str, dict] = {}

    # across entries
    for r in range(n):
        c = 0
        while c < n:
            if black[r][c]:
                c += 1
                continue
            if c > 0 and not black[r][c - 1]:
                c += 1
                continue
            start_c = c
            length = 0
            while c < n and not black[r][c]:
                length += 1
                c += 1
            number = cell_number[r][start_c]
            if number:
                clues[f"{number}A"] = {"x": start_c, "y": r, "length": length, "direction": "Across"}

    # down entries
    for c in range(n):
        r = 0
        while r < n:
            if black[r][c]:
                r += 1
                continue
            if r > 0 and not black[r - 1][c]:
                r += 1
                continue
            start_r = r
            length = 0
            while r < n and not black[r][c]:
                length += 1
                r += 1
            number = cell_number[start_r][c]
            if number:
                clues[f"{number}D"] = {"x": c, "y": start_r, "length": length, "direction": "Down"}

    return clues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="Path to a grid-only image")
    ap.add_argument("--out", required=True, help="Path to write grid_state.json")
    ap.add_argument("--size", type=int, default=15, help="Grid size N for NxN (default 15)")
    ap.add_argument("--thr", type=int, default=160, help="Black/white threshold (0-255)")
    ap.add_argument("--debug", action="store_true", help="Include debug line positions in output")
    args = ap.parse_args()

    img_path = Path(args.image).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()

    im = Image.open(img_path).convert("L")
    W, H = im.size
    pix = im.load()

    # dark pixel profiles
    thr_line = min(200, args.thr)
    col = [0] * W
    row = [0] * H
    for y in range(H):
        for x in range(W):
            if pix[x, y] < thr_line:
                col[x] += 1
                row[y] += 1

    # min separation between grid lines (roughly >= half a cell)
    min_sep_x = max(10, int(W / args.size * 0.55))
    min_sep_y = max(10, int(H / args.size * 0.55))

    vlines = _find_grid_lines(col, n=args.size, min_sep=min_sep_x)
    hlines = _find_grid_lines(row, n=args.size, min_sep=min_sep_y)

    black = _classify_cells(im, vlines=vlines, hlines=hlines, thr=args.thr)
    clues = _entries_from_black(black)

    grid_state: dict = {
        "width": args.size,
        "height": args.size,
        "clues": clues,
    }

    if args.debug:
        grid_state["_debug"] = {
            "image": str(img_path),
            "image_size": [W, H],
            "vlines": vlines,
            "hlines": hlines,
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(grid_state, indent=2) + "\n")
    print(f"Wrote {out_path} ({len(clues)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
