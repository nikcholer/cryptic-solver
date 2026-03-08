from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_puzzle_loader, get_session_service
from app.models.api import (
    AcceptEntryRequest,
    AcceptEntryResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    ClearEntryResponse,
    ReanalyzeAffectedRequest,
    ReanalyzeAffectedResponse,
    SelectClueRequest,
    SelectClueResponse,
    SessionResponse,
    SubmitEntryRequest,
    SubmitEntryResponse,
)
from app.services.puzzle_loader import PuzzleLoader
from app.services.session_service import SessionService

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=CreateSessionResponse)
def create_session(
    request: CreateSessionRequest,
    puzzle_loader: PuzzleLoader = Depends(get_puzzle_loader),
    session_service: SessionService = Depends(get_session_service),
):
    try:
        puzzle = puzzle_loader.load_puzzle(request.puzzle_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="puzzle_not_found") from exc
    session = session_service.create_session(puzzle)
    return CreateSessionResponse(sessionId=session.session_id, puzzle=puzzle, sessionState=session_service.snapshot(session))


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    puzzle_loader: PuzzleLoader = Depends(get_puzzle_loader),
    session_service: SessionService = Depends(get_session_service),
):
    try:
        session = session_service.get_session(session_id)
        puzzle = puzzle_loader.load_puzzle(session.puzzle_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="session_not_found") from exc
    return SessionResponse(sessionId=session.session_id, puzzle=puzzle, sessionState=session_service.snapshot(session))


@router.post("/{session_id}/select-clue", response_model=SelectClueResponse)
def select_clue(
    session_id: str,
    request: SelectClueRequest,
    session_service: SessionService = Depends(get_session_service),
):
    try:
        session = session_service.select_clue(session_id, request.clue_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="session_not_found") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="clue_not_found") from exc
    return SelectClueResponse(selectedClueId=session.selected_clue_id)


@router.post("/{session_id}/entries", response_model=SubmitEntryResponse)
def submit_entry(
    session_id: str,
    request: SubmitEntryRequest,
    puzzle_loader: PuzzleLoader = Depends(get_puzzle_loader),
    session_service: SessionService = Depends(get_session_service),
):
    try:
        session = session_service.get_session(session_id)
        puzzle = puzzle_loader.load_puzzle(session.puzzle_id)
        updated_session, affected_clues, patterns, changed_cells = session_service.submit_entry(
            puzzle, session_id, request.clue_id, request.answer, request.justification
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="session_not_found") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="clue_not_found") from exc
    return SubmitEntryResponse(
        clueId=request.clue_id,
        validation=updated_session.clue_states[request.clue_id].validation,
        sessionDelta={
            "updatedCells": changed_cells,
            "updatedPatterns": {clue_id: patterns[clue_id] for clue_id in affected_clues},
            "affectedClues": affected_clues,
        },
    )


@router.post("/{session_id}/reanalyze-affected", response_model=ReanalyzeAffectedResponse)
def reanalyze_affected(
    session_id: str,
    request: ReanalyzeAffectedRequest,
    puzzle_loader: PuzzleLoader = Depends(get_puzzle_loader),
    session_service: SessionService = Depends(get_session_service),
):
    try:
        session = session_service.get_session(session_id)
        puzzle = puzzle_loader.load_puzzle(session.puzzle_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="session_not_found") from exc
    updates = session_service.reanalyze_affected(puzzle, session_id, request.clue_ids)
    return ReanalyzeAffectedResponse(clueUpdates=updates)

@router.delete("/{session_id}/entries/{clue_id}", response_model=ClearEntryResponse)
def clear_entry(
    session_id: str,
    clue_id: str,
    puzzle_loader: PuzzleLoader = Depends(get_puzzle_loader),
    session_service: SessionService = Depends(get_session_service),
):
    try:
        session = session_service.get_session(session_id)
        puzzle = puzzle_loader.load_puzzle(session.puzzle_id)
        updated_session, affected_clues, patterns, changed_cells = session_service.clear_entry(puzzle, session_id, clue_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="session_not_found") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="clue_not_found") from exc
    return ClearEntryResponse(
        clueId=clue_id,
        sessionDelta={
            "updatedCells": changed_cells,
            "updatedPatterns": {current_clue_id: patterns[current_clue_id] for current_clue_id in affected_clues},
            "affectedClues": affected_clues,
        },
    )


@router.post("/{session_id}/entries/{clue_id}/accept", response_model=AcceptEntryResponse)
def accept_entry(
    session_id: str,
    clue_id: str,
    request: AcceptEntryRequest,
    puzzle_loader: PuzzleLoader = Depends(get_puzzle_loader),
    session_service: SessionService = Depends(get_session_service),
):
    try:
        session = session_service.get_session(session_id)
        puzzle = puzzle_loader.load_puzzle(session.puzzle_id)
        updated_session, affected_clues, patterns, changed_cells = session_service.accept_entry(
            puzzle, session_id, clue_id, request.answer, request.justification
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="session_not_found") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="clue_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AcceptEntryResponse(
        clueId=clue_id,
        validation=updated_session.clue_states[clue_id].validation,
        sessionDelta={
            "updatedCells": changed_cells,
            "updatedPatterns": {current_clue_id: patterns[current_clue_id] for current_clue_id in affected_clues},
            "affectedClues": affected_clues,
        },
    )
