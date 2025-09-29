from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import load_settings, IMAGES_DIR
from app.utils.fs import ensure_dirs
from app.routers import images as images_router
from app.routers import settings as settings_router
from app.routers import sessions as sessions_router
from app.routers import timeline as timeline_router
from app.routers import relationships as relationships_router
from app.routers import npc as npc_router

ensure_dirs()
app = FastAPI(title="AI Daughter Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

cfg = load_settings()
app.mount(cfg.image_transport.static_path_prefix, StaticFiles(directory=str(IMAGES_DIR)), name="images")

app.include_router(images_router.router)
app.include_router(settings_router.router)
app.include_router(sessions_router.router)
app.include_router(timeline_router.router)
app.include_router(relationships_router.router)
app.include_router(npc_router.router)

@app.get("/health")
def health():
    return {"ok": True}