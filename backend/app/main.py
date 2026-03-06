from __future__ import annotations

from fastapi import FastAPI

from app.api.clues import router as clues_router
from app.api.puzzles import router as puzzles_router
from app.api.sessions import router as sessions_router

app = FastAPI(title="Cryptic Tutor Backend", version="0.1.0")
app.include_router(puzzles_router)
app.include_router(sessions_router)
app.include_router(clues_router)


@app.get('/health')
def healthcheck():
    return {"status": "ok"}