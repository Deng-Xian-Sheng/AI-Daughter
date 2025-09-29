from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Literal

class ImageGenerateRequest(BaseModel):
    mode: Literal["text2img","img2img"]
    prompt: str
    negative: Optional[str] = None
    aspect_policy: Literal["auto","square","portrait","landscape"] = "auto"
    size: Optional[str] = None
    ref_image_id: Optional[str] = None
    provider_override: Optional[Literal["modelscope","bailian"]] = None

class ImageTaskResponse(BaseModel):
    task_id: str

class ImageTaskStatus(BaseModel):
    status: str
    result: Optional[dict] = None