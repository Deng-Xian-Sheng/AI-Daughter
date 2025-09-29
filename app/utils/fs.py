from __future__ import annotations
from pathlib import Path
from app.config import DATA_DIR, IMAGES_DIR, UPLOADS_DIR, GENERATED_DIR, REFS_IMG_DIR, IMAGE_META_DIR

SESSIONS_DIR = DATA_DIR / "sessions"

def ensure_dirs():
    for p in [DATA_DIR, IMAGES_DIR, UPLOADS_DIR, GENERATED_DIR, REFS_IMG_DIR, IMAGE_META_DIR, SESSIONS_DIR]:
        p.mkdir(parents=True, exist_ok=True)