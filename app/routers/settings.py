from __future__ import annotations
from fastapi import APIRouter
from app.config import load_settings, save_settings, Settings

router = APIRouter(prefix="/api", tags=["settings"])

@router.get("/settings", response_model=Settings)
def get_settings():
    return load_settings()

@router.post("/settings", response_model=Settings)
def update_settings(cfg: Settings):
    save_settings(cfg)
    return cfg