# app/services/ref_registry.py
from __future__ import annotations
from pathlib import Path
import json, uuid
from typing import Optional
from PIL import Image

from app.config import IMAGES_DIR, UPLOADS_DIR, DATA_DIR

REFS_IMG_DIR = IMAGES_DIR / "refs"
MAP_PATH = DATA_DIR / "refs_map.json"

def _load_map() -> dict:
    if MAP_PATH.exists():
        return json.loads(MAP_PATH.read_text(encoding="utf-8"))
    return {}

def _save_map(mp: dict):
    MAP_PATH.write_text(json.dumps(mp, ensure_ascii=False, indent=2), encoding="utf-8")

def _find_ref_path(ref_id: str) -> Path:
    exts = [".png", ".jpg", ".jpeg", ".webp"]
    for ext in exts:
        p = REFS_IMG_DIR / f"{ref_id}{ext}"
        if p.exists():
            return p
    raise FileNotFoundError(f"ref image not found for id={ref_id} (tried {exts})")

def register_ref_image(ref_id: str) -> dict:
    """
    将 data/images/refs/{ref_id}.{ext} 复制并转换为 PNG 存到 uploads，返回 {ref_id, image_id}
    幂等：若已存在映射且目标文件仍在，则直接复用。
    """
    mp = _load_map()

    # 映射已存在且文件还在 → 直接复用
    old = mp.get(ref_id)
    if old:
        target = UPLOADS_DIR / f"{old}.png"
        if target.exists():
            return {"ref_id": ref_id, "image_id": old}

    # 否则重新注册
    src = _find_ref_path(ref_id)
    image_id = str(uuid.uuid4())
    dst = UPLOADS_DIR / f"{image_id}.png"

    # 统一转 PNG 保存（避免后续按 .png 路径读取失败）
    img = Image.open(src).convert("RGB")
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, format="PNG")

    mp[ref_id] = image_id
    _save_map(mp)
    return {"ref_id": ref_id, "image_id": image_id}