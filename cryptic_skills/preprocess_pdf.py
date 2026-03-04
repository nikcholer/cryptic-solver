#!/usr/bin/env python3
"""Render a crossword PDF to image files for downstream vision-based extraction.

Why:
- Agent runtimes vary in how well they can "see" PDFs directly.
- Converting to high-DPI PNGs makes grid/clue extraction far more reliable.

This script intentionally has **no third-party Python deps**.
It shells out to Poppler's `pdftoppm`, which is commonly available on Linux.

Example:
  python cryptic_skills/preprocess_pdf.py \
    --pdf ./puzzle_12345/crossword.pdf \
    --outdir ./puzzle_12345 \
    --dpi 450

Outputs (by default):
  page-1.png, page-2.png, ...
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, help="Path to input PDF")
    ap.add_argument("--outdir", required=True, help="Directory to write images")
    ap.add_argument("--dpi", type=int, default=450, help="Render DPI (300-600 typical)")
    ap.add_argument("--first-page", type=int, default=None, help="First page number (1-indexed)")
    ap.add_argument("--last-page", type=int, default=None, help="Last page number (1-indexed)")
    ap.add_argument(
        "--prefix",
        default="page",
        help="Output filename prefix (default: page -> page-1.png)",
    )
    args = ap.parse_args()

    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise SystemExit(
            "pdftoppm not found on PATH. Install poppler-utils (Debian/Ubuntu) or poppler (brew)."
        )

    pdf = Path(args.pdf).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    # pdftoppm writes to <outprefix>-1.png etc
    outprefix = outdir / args.prefix

    cmd = [pdftoppm, "-r", str(args.dpi), "-png"]
    if args.first_page is not None:
        cmd += ["-f", str(args.first_page)]
    if args.last_page is not None:
        cmd += ["-l", str(args.last_page)]
    cmd += [str(pdf), str(outprefix)]

    print("Running:", " ".join(cmd))
    run(cmd)

    # Friendly hint for downstream tools
    produced = sorted(outdir.glob(f"{args.prefix}-*.png"))
    if produced:
        print(f"Wrote {len(produced)} image(s) to {outdir}")
        print("First:", produced[0].name)
        print("Last: ", produced[-1].name)
    else:
        print("No images produced (unexpected).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
