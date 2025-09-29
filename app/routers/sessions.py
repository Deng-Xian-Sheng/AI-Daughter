from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid
from PIL import Image
from io import BytesIO

from app.services.memory_store import ensure_entities, list_sessions, create_session, load_messages, append_message
from app.services.sse_hub import hub
from app.utils.sse import sse_stream
from app.config import UPLOADS_DIR
from app.services.vision_service import describe_image
from app.services.chat_orchestrator import handle_user_message

router = APIRouter(prefix="/api", tags=["sessions"])

class SessionCreateReq(BaseModel):
    participants: List[str]
    title: Optional[str] = ""

@router.post("/session.create")
def session_create(req: SessionCreateReq):
    ensure_entities()
    if not req.participants:
        raise HTTPException(400, "participants required")
    sid = create_session(req.participants, title=req.title or "", type_="group" if len(req.participants)>2 else "direct")
    return {"session_id": sid}

@router.get("/session.list")
def session_list():
    ensure_entities()
    return {"sessions": list_sessions()}

@router.get("/session/{session_id}/messages")
def session_messages(session_id: str):
    return {"messages": load_messages(session_id)}

@router.get("/stream/{session_id}")
async def stream(session_id: str):
    async def gen():
        async for ev in hub.subscribe(session_id):
            yield ev
    return await sse_stream(gen())

# message.send：仅标准 multipart/form-data，字段名 files（保持原设计）
@router.post("/message.send")
async def message_send(
    session_id: str = Form(...),
    sender_id: str = Form(...),
    text: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None)
):
    # 文本
    if text and text.strip():
        mid = append_message(session_id, sender_id, "text", text=text.strip())
        await hub.publish(session_id, {"type":"message_new","message":{
            "id": mid, "session_id": session_id, "sender_id": sender_id, "type":"text", "text": text.strip()
        }})

    # 图片
    if files:
        for f in files:
            content = await f.read()
            try:
                img = Image.open(BytesIO(content)).convert("RGB")
            except Exception:
                raise HTTPException(400, "invalid image file")
            image_id = str(uuid.uuid4())
            out_path = UPLOADS_DIR / f"{image_id}.png"
            img.save(out_path, format="PNG")
            # 关键：meta.kind=uploads
            mid = append_message(session_id, sender_id, "image", image_id=image_id, meta={"kind": "uploads"})
            await hub.publish(session_id, {"type":"message_new","message":{
                "id": mid, "session_id": session_id, "sender_id": sender_id, "type":"image",
                "image_id": image_id, "meta": {"kind":"uploads"}
            }})
            await describe_image(image_id)

    # 玩家发言 → 触发AI回复
    if sender_id == "player" and (text and text.strip()):
        await handle_user_message(session_id, text.strip())

    return {"ok": True}