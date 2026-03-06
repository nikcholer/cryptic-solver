from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_puzzle_loader
from app.models.api import PuzzleResponse
from app.services.puzzle_loader import PuzzleLoader

router = APIRouter(prefix="/api/puzzles", tags=["puzzles"])


@router.get("/{puzzle_id}", response_model=PuzzleResponse)
def get_puzzle(
    puzzle_id: str,
    puzzle_loader: PuzzleLoader = Depends(get_puzzle_loader),
):
    try:
        puzzle = puzzle_loader.load_puzzle(puzzle_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="puzzle_not_found") from exc
    return PuzzleResponse(puzzle=puzzle)