from __future__ import annotations
import json, uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.config import DATA_DIR
from app.utils.fs import SESSIONS_DIR

USERS_PATH = DATA_DIR / "users.json"
AGENTS_PATH = DATA_DIR / "agents.json"
NPCS_PATH = DATA_DIR / "npcs.json"
REL_PATH = DATA_DIR / "relationships.json"
SESS_INDEX_PATH = DATA_DIR / "sessions_index.json"

def _load_json(path: Path, default: Any):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")
    return default

def _save_json(path: Path, obj: Any):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def ensure_entities():
    users = _load_json(USERS_PATH, {"player": {"id": "player", "name": "爸爸", "avatar": None}})
    agents = _load_json(AGENTS_PATH, {"agent": {"id": "agent", "name": "琪琪", "avatar": None}})
    npcs = _load_json(NPCS_PATH, {})
    rels = _load_json(REL_PATH, {
        "player->agent": {"title": "琪琪"},
        "agent->player": {"title": "爸爸"}
    })
    _load_json(SESS_INDEX_PATH, {"sessions": []})
    return users, agents, npcs, rels

def list_sessions() -> List[Dict]:
    idx = _load_json(SESS_INDEX_PATH, {"sessions": []})
    return idx["sessions"]

def create_session(participants: List[str], title: Optional[str] = None, type_: str = "direct") -> str:
    sess_id = str(uuid.uuid4())
    session_dir = SESSIONS_DIR / sess_id
    session_dir.mkdir(parents=True, exist_ok=True)
    _save_json(session_dir / "messages.json", [])
    idx = _load_json(SESS_INDEX_PATH, {"sessions": []})
    idx["sessions"].append({
        "id": sess_id,
        "participants": participants,
        "title": title or "",
        "type": type_,
        "created_at": _now_iso(),
        "unread_count": 0
    })
    _save_json(SESS_INDEX_PATH, idx)
    return sess_id

def get_session(sess_id: str) -> Dict:
    for s in list_sessions():
        if s["id"] == sess_id:
            return s
    raise KeyError("session not found")

def load_messages(sess_id: str) -> List[Dict]:
    return _load_json(SESSIONS_DIR / sess_id / "messages.json", [])

def save_messages(sess_id: str, msgs: List[Dict]):
    _save_json(SESSIONS_DIR / sess_id / "messages.json", msgs)

def append_message(sess_id: str, sender_id: str, type_: str, text: Optional[str] = None, image_id: Optional[str] = None, meta: Optional[Dict]=None) -> str:
    msgs = load_messages(sess_id)
    mid = str(uuid.uuid4())
    msg = {
        "id": mid,
        "session_id": sess_id,
        "sender_id": sender_id,
        "type": type_,
        "text": text,
        "image_id": image_id,
        "created_at": _now_iso(),
        "meta": meta or {}
    }
    msgs.append(msg)
    save_messages(sess_id, msgs)
    return mid

def list_npcs() -> Dict:
    return _load_json(NPCS_PATH, {})

def save_npcs(npcs: Dict):
    _save_json(NPCS_PATH, npcs)

def add_npc(npc: Dict) -> str:
    npcs = list_npcs()
    nid = npc["id"]
    npcs[nid] = npc
    save_npcs(npcs)
    return nid

def get_entities() -> Dict[str, Dict]:
    users = _load_json(USERS_PATH, {"player": {"id": "player", "name": "爸爸", "avatar": None}})
    agents = _load_json(AGENTS_PATH, {"agent": {"id": "agent", "name": "琪琪", "avatar": None}})
    npcs = _load_json(NPCS_PATH, {})
    return {"users": users, "agents": agents, "npcs": npcs}

def get_relationship(subject_id: str, object_id: str) -> Optional[str]:
    rels = _load_json(REL_PATH, {})
    key = f"{subject_id}->{object_id}"
    return rels.get(key, {}).get("title")

def set_relationship(subject_id: str, object_id: str, title: str):
    rels = _load_json(REL_PATH, {})
    rels[f"{subject_id}->{object_id}"] = {"title": title}
    _save_json(REL_PATH, rels)