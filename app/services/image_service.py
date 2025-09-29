from __future__ import annotations
import asyncio, uuid, base64
from pathlib import Path
from typing import Optional
import httpx

from app.config import load_settings, GENERATED_DIR, IMAGES_DIR
from app.providers.images_modelscope import ms_text2img, ms_img2img, ms_poll_task
from app.providers.images_bailian import bl_text2img, bl_img2img
from app.services.prompt_writer import decide_size

TASKS: dict[str, dict] = {}

def build_public_url(rel_path: str) -> str:
    cfg = load_settings()
    return f"{cfg.image_transport.public_base_url}{cfg.image_transport.static_path_prefix}/{rel_path}"

def build_data_uri(path: Path) -> str:
    mime = "image/png" if path.suffix.lower()==".png" else "image/jpeg"
    b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

async def run_image_task(mode: str, prompt: str, negative: Optional[str], aspect_policy: str, size_hint: Optional[str], ref_image_id: Optional[str], provider_override: Optional[str]) -> str:
    """
    mode: text2img|img2img
    returns task_id (internal)
    """
    cfg = load_settings()
    provider = provider_override or (cfg.providers.text2img if mode=="text2img" else cfg.providers.img2img)
    ms_model = cfg.model_ids.text2img.modelscope if mode=="text2img" else cfg.model_ids.img2img.modelscope
    bl_model = cfg.model_ids.text2img.bailian if mode=="text2img" else cfg.model_ids.img2img.bailian

    internal_task_id = str(uuid.uuid4())
    TASKS[internal_task_id] = {"status":"PENDING", "result":None}

    async def _work():
        try:
            TASKS[internal_task_id]["status"] = "RUNNING"
            size = size_hint or decide_size(aspect_policy, scene_hint=None)

            if provider == "modelscope":
                if mode == "text2img":
                    ms_task_id = await ms_text2img(ms_model, prompt, negative, size)
                    # poll
                    while True:
                        data = await ms_poll_task(ms_task_id)
                        st = data.get("task_status")
                        if st == "SUCCEED":
                            # download first image
                            url = data["output_images"][0]
                            img_id = str(uuid.uuid4())
                            out_path = GENERATED_DIR / f"{img_id}.png"
                            async with httpx.AsyncClient(timeout=60) as client:
                                r = await client.get(url)
                                r.raise_for_status()
                                out_path.write_bytes(r.content)
                            rel = f"generated/{img_id}.png"
                            TASKS[internal_task_id]["status"] = "SUCCEEDED"
                            TASKS[internal_task_id]["result"] = {
                                "image_id": img_id,
                                "url": build_public_url(rel)
                            }
                            break
                        elif st == "FAILED":
                            TASKS[internal_task_id]["status"] = "FAILED"
                            TASKS[internal_task_id]["result"] = {"error": data}
                            break
                        await asyncio.sleep(3)

                else:  # img2img
                    # build reference input
                    ref_rel = f"generated/{ref_image_id}.png"
                    ref_path = IMAGES_DIR / ref_rel
                    if not ref_path.exists():
                        ref_rel = f"uploads/{ref_image_id}.png"
                        ref_path = IMAGES_DIR / ref_rel
                    if cfg.image_transport.modelscope == "public_url":
                        ref_input = build_public_url(ref_rel)
                    else:
                        ref_input = build_data_uri(ref_path)

                    ms_task_id = await ms_img2img(ms_model, prompt, ref_input, negative, size)
                    while True:
                        data = await ms_poll_task(ms_task_id)
                        st = data.get("task_status")
                        if st == "SUCCEED":
                            url = data["output_images"][0]
                            img_id = str(uuid.uuid4())
                            out_path = GENERATED_DIR / f"{img_id}.png"
                            async with httpx.AsyncClient(timeout=60) as client:
                                r = await client.get(url)
                                r.raise_for_status()
                                out_path.write_bytes(r.content)
                            rel = f"generated/{img_id}.png"
                            TASKS[internal_task_id]["status"] = "SUCCEEDED"
                            TASKS[internal_task_id]["result"] = {"image_id": img_id, "url": build_public_url(rel)}
                            break
                        elif st == "FAILED":
                            TASKS[internal_task_id]["status"] = "FAILED"
                            TASKS[internal_task_id]["result"] = {"error": data}
                            break
                        await asyncio.sleep(3)

            else:  # bailian
                if mode == "text2img":
                    data = await bl_text2img(bl_model, prompt, size, negative, prompt_extend=cfg.prompt.prompt_extend)
                else:
                    # ref
                    ref_rel = f"generated/{ref_image_id}.png"
                    ref_path = IMAGES_DIR / ref_rel
                    if not ref_path.exists():
                        ref_rel = f"uploads/{ref_image_id}.png"
                        ref_path = IMAGES_DIR / ref_rel
                    # bailian支持base64或URL：我们优先data URI以避免公网暴露
                    ref_input = build_data_uri(ref_path)
                    data = await bl_img2img(bl_model, prompt, ref_input, negative, prompt_extend=False)

                # extract image url -> download
                try:
                    image_url = data["output"]["choices"][0]["message"]["content"][0]["image"]
                except Exception:
                    TASKS[internal_task_id]["status"] = "FAILED"
                    TASKS[internal_task_id]["result"] = {"error": data}
                    return

                img_id = str(uuid.uuid4())
                out_path = GENERATED_DIR / f"{img_id}.png"
                async with httpx.AsyncClient(timeout=60) as client:
                    r = await client.get(image_url)
                    r.raise_for_status()
                    out_path.write_bytes(r.content)
                rel = f"generated/{img_id}.png"
                TASKS[internal_task_id]["status"] = "SUCCEEDED"
                TASKS[internal_task_id]["result"] = {"image_id": img_id, "url": build_public_url(rel)}

        except Exception as e:
            TASKS[internal_task_id]["status"] = "FAILED"
            TASKS[internal_task_id]["result"] = {"error": str(e)}

    asyncio.create_task(_work())
    return internal_task_id

def get_task(task_id: str) -> dict:
    return TASKS.get(task_id, {"status": "UNKNOWN"})