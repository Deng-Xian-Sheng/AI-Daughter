from __future__ import annotations
import os, time, base64
import httpx
from pathlib import Path
from typing import Optional

MS_BASE = "https://api-inference.modelscope.cn/"
API_KEY = os.getenv("MODELSCOPE_API_KEY")

HEADERS_JSON = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

async def ms_text2img(model: str, prompt: str, negative: str | None, size: str | None, seed: Optional[int] = None) -> str:
    """Return task_id. Caller should poll /v1/tasks/{task_id} with X-ModelScope-Task-Type=image_generation"""
    import json
    payload = {"model": model, "prompt": prompt}
    if negative:
        payload["negative_prompt"] = negative
    if size:
        payload["size"] = size
    if seed is not None:
        payload["seed"] = seed
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{MS_BASE}v1/images/generations",
            headers={**HEADERS_JSON, "X-ModelScope-Async-Mode": "true"},
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )
        r.raise_for_status()
        return r.json()["task_id"]

async def ms_img2img(model: str, prompt: str, image_url_or_data_uri: str, negative: str | None, size: str | None, seed: Optional[int] = None) -> str:
    """Same endpoint; Qwen-Image-Edit expects image_url field. We'll try data URI if configured."""
    import json
    payload = {"model": model, "prompt": prompt, "image_url": image_url_or_data_uri}
    if negative:
        payload["negative_prompt"] = negative
    if size:
        payload["size"] = size
    if seed is not None:
        payload["seed"] = seed
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{MS_BASE}v1/images/generations",
            headers={**HEADERS_JSON, "X-ModelScope-Async-Mode": "true"},
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )
        r.raise_for_status()
        return r.json()["task_id"]

async def ms_poll_task(task_id: str) -> dict:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(
            f"{MS_BASE}v1/tasks/{task_id}",
            headers={**HEADERS_JSON, "X-ModelScope-Task-Type": "image_generation"},
        )
        r.raise_for_status()
        return r.json()