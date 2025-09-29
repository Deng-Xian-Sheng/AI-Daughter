from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.schemas.images import ImageGenerateRequest, ImageTaskResponse, ImageTaskStatus
from app.services.image_service import run_image_task, get_task

router = APIRouter(prefix="/api", tags=["images"])

@router.post("/image.generate", response_model=ImageTaskResponse)
async def image_generate(req: ImageGenerateRequest):
    if req.mode == "img2img" and not req.ref_image_id:
        raise HTTPException(400, "img2img requires ref_image_id")
    task_id = await run_image_task(req.mode, req.prompt, req.negative, req.aspect_policy, req.size, req.ref_image_id, req.provider_override)
    return ImageTaskResponse(task_id=task_id)

@router.get("/tasks/{task_id}", response_model=ImageTaskStatus)
async def task_status(task_id: str):
    return ImageTaskStatus(**get_task(task_id))