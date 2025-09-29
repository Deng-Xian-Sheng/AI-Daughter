from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.relationships import set_relationship

router = APIRouter(prefix="/api", tags=["relationships"])

class RelReq(BaseModel):
    subject_id: str
    object_id: str
    title: str

@router.post("/relationship.set")
def relationship_set(req: RelReq):
    set_relationship(req.subject_id, req.object_id, req.title)
    return {"ok": True}