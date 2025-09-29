from __future__ import annotations
import os, httpx, json
from typing import Optional

DASH_BASE = "https://dashscope.aliyuncs.com/api/v1"
API_KEY = os.getenv("DASHSCOPE_API_KEY")
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

async def bl_text2img(model: str, prompt: str, size: str | None, negative: str | None, prompt_extend: bool = False) -> dict:
    body = {
        "model": model,
        "input": { "messages": [ { "role": "user", "content": [ { "text": prompt } ] } ] },
        "parameters": {
            "watermark": False,
            "prompt_extend": bool(prompt_extend)
        }
    }
    if size:
        body["parameters"]["size"] = size
    if negative:
        body["parameters"]["negative_prompt"] = negative

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{DASH_BASE}/services/aigc/multimodal-generation/generation", headers=HEADERS, json=body)
        r.raise_for_status()
        return r.json()

async def bl_img2img(model: str, prompt: str, image_url_or_data_uri: str, negative: str | None, prompt_extend: bool = False) -> dict:
    body = {
        "model": model,
        "input": { "messages": [ { "role": "user", "content": [ { "image": image_url_or_data_uri }, { "text": prompt } ] } ] },
        "parameters": {
            "watermark": False
        }
    }
    if negative:
        body["parameters"]["negative_prompt"] = negative
    # prompt_extend 对图编无效或未公开，按需添加
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{DASH_BASE}/services/aigc/multimodal-generation/generation", headers=HEADERS, json=body)
        r.raise_for_status()
        return r.json()