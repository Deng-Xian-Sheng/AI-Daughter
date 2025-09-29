from __future__ import annotations
from app.services.memory_store import get_relationship, set_relationship as _set

def title_of(subject_id: str, object_id: str) -> str:
    return get_relationship(subject_id, object_id) or ""

def set_relationship(subject_id: str, object_id: str, title: str):
    _set(subject_id, object_id, title)