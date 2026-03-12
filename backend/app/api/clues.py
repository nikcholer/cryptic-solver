from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_puzzle_loader, get_session_service
from app.models.api import CheckAnswerRequest, CheckAnswerResponse, NextHintRequest, NextHintResponse
from app.services.puzzle_loader import PuzzleLoader
from app.services.session_service import SessionService

router = APIRouter(prefix="/api/sessions/{session_id}/clues", tags=["clues"])


@router.post("/{clue_id}/check", response_model=CheckAnswerResponse)
def check_answer(
    session_id: str,
    clue_id: str,
    request: CheckAnswerRequest,
    puzzle_loader: PuzzleLoader = Depends(get_puzzle_loader),
    session_service: SessionService = Depends(get_session_service),
):
    try:
        session = session_service.get_session(session_id)
        puzzle = puzzle_loader.load_puzzle(session.puzzle_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="session_not_found") from exc
    result = session_service.check_answer(puzzle, session_id, clue_id, request.answer, request.justification)
    return CheckAnswerResponse(clueId=clue_id, result=result["result"], reason=result["reason"])


@router.post("/{clue_id}/next-hint", response_model=NextHintResponse)
def next_hint(
    session_id: str,
    clue_id: str,
    request: NextHintRequest,
    puzzle_loader: PuzzleLoader = Depends(get_puzzle_loader),
    session_service: SessionService = Depends(get_session_service),
):
    try:
        session = session_service.get_session(session_id)
        puzzle = puzzle_loader.load_puzzle(session.puzzle_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="session_not_found") from exc
    updated_session, result = session_service.next_hint(puzzle, session_id, clue_id)
    history = [
        {"level": hint.level, "kind": hint.kind.value, "source": hint.source}
        for hint in updated_session.clue_states[clue_id].hints
    ]
    return NextHintResponse(
        clueId=clue_id,
        hintLevel=result["hintLevel"],
        kind=result["kind"],
        text=result["text"],
        source=result.get("source", "agent"),
        updatedHintHistory=history,
    )