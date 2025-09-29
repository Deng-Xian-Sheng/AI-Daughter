from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.services.npc_service import create_npc

router = APIRouter(prefix="/api", tags=["npc"])

class NPCCreateReq(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    gender: Optional[str] = "male"

@router.post("/npc.create")
async def npc_create(req: NPCCreateReq):
    npc = await create_npc(req.name, req.role, req.gender or "male")
    return {"npc": npc}