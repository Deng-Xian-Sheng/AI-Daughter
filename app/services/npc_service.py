from __future__ import annotations
import uuid
from typing import Optional
from app.services.memory_store import add_npc
from app.services.image_service import run_image_task
from app.services.prompt_writer import build_avatar_prompts

async def create_npc(name: Optional[str] = None, role: Optional[str] = None, gender: str = "male") -> dict:
    npc_id = f"npc_{uuid.uuid4().hex[:8]}"
    display_name = name or "路人"
    desc = {"gender": "male" if gender=="male" else "female", "age": "adult", "hairstyle": "短发", "vibe": f"{role or '普通'}"}
    prompts = build_avatar_prompts(desc, n=1)
    pos, neg = prompts[0]
    task_id = await run_image_task(
        mode="text2img",
        prompt=pos,
        negative=neg,
        aspect_policy="square",
        size_hint="1328x1328",
        ref_image_id=None,
        provider_override=None
    )
    npc = {
        "id": npc_id,
        "name": display_name,
        "role": role or "",
        "avatar_image_id": None,
        "avatar_task_id": task_id
    }
    add_npc(npc)
    return npc