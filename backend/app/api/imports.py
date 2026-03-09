from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.dependencies import get_puzzle_import_service, get_puzzle_loader, get_session_service
from app.models.api import SessionResponse
from app.services.puzzle_import_service import PuzzleImportService
from app.services.puzzle_loader import PuzzleLoader
from app.services.session_service import SessionService

router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.post("/pdf", response_model=SessionResponse)
async def import_pdf(
    file: UploadFile = File(...),
    page: int = Form(1),
    import_service: PuzzleImportService = Depends(get_puzzle_import_service),
    puzzle_loader: PuzzleLoader = Depends(get_puzzle_loader),
    session_service: SessionService = Depends(get_session_service),
):
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail='pdf_required')
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail='empty_file')
    try:
        puzzle_id = import_service.import_pdf(file.filename, content, page=page)
        puzzle = puzzle_loader.load_puzzle(puzzle_id)
        session = session_service.create_session(puzzle)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SessionResponse(sessionId=session.session_id, puzzle=puzzle, sessionState=session_service.snapshot(session))
