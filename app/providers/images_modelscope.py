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

def check_string_type(input_str):
    """
    判断字符串类型：图片base64还是HTTP链接
    
    Args:
        input_str (str): 输入的字符串
        
    Returns:
        str: 返回类型标识
            - "base64": 图片base64编码
            - "http": HTTP/HTTPS链接
            - "unknown": 未知类型
    """
    import re
    if not input_str or not isinstance(input_str, str):
        return "unknown"
    
    # 转换为小写便于判断
    lower_str = input_str.lower().strip()
    
    # 检查是否是HTTP/HTTPS链接
    http_pattern = r'^https?://'
    if re.match(http_pattern, lower_str):
        return "http"
    
    # 检查是否是base64图片编码
    base64_pattern = r'^data:image/(png|jpeg|jpg|gif|bmp|webp);base64,'
    if re.match(base64_pattern, lower_str):
        return "base64"
    
    # 如果是纯base64字符串（没有data:image前缀）
    if len(input_str) > 100 and re.match(r'^[A-Za-z0-9+/]*={0,2}$', input_str):
        return "base64"
    
    return "unknown"

async def ms_img2img(model: str, prompt: str, image_url_or_data_uri: str, negative: str | None, size: str | None, seed: Optional[int] = None) -> str:
    """Same endpoint; Qwen-Image-Edit expects image_url field. We'll try data URI if configured."""
    import json
    img_key_name = ""
    if check_string_type(image_url_or_data_uri) == "http":
        img_key_name = "image_url"
    elif check_string_type(image_url_or_data_uri) == "base64":
        img_key_name = "image"
    else:
        print(f"❌❌❌以图生图参考图有问题：{image_url_or_data_uri}")
        print("❌❌❌以图生图参考图有问题，打印结束")
    payload = {"model": model, "prompt": prompt, img_key_name: image_url_or_data_uri}
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