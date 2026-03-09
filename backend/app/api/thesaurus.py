from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_thesaurus_service
from app.models.api import ThesaurusLookupResponse
from app.services.thesaurus_service import ThesaurusService

router = APIRouter(prefix="/api/thesaurus", tags=["thesaurus"])


@router.get("", response_model=ThesaurusLookupResponse)
def lookup_thesaurus(
    term: str = Query(..., min_length=1),
    length: int | None = Query(default=None, ge=1),
    thesaurus_service: ThesaurusService = Depends(get_thesaurus_service),
):
    candidates = thesaurus_service.lookup(term, length=length)
    return ThesaurusLookupResponse(term=term, length=length, candidates=candidates)
