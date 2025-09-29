from __future__ import annotations
from fastapi import APIRouter
from app.services.timeline_engine import get_slice, tick

router = APIRouter(prefix="/api", tags=["timeline"])

@router.get("/timeline.slice")
def timeline_slice():
    return get_slice()

@router.post("/timeline.tick")
def timeline_tick(mode: str = "dialogue"):
    return tick(mode=mode)