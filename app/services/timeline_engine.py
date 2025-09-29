from __future__ import annotations
from pathlib import Path
import json, random
from datetime import datetime
from app.config import DATA_DIR

TL_PATH = DATA_DIR / "timeline.json"

DEFAULT_TL = {
    "now": {"day": 1, "weekday": "周六", "time_of_day": "上午"},
    "environment": {"city": "云港城", "weather": "晴", "temp": "22°C"},
    "beats": []
}

SEGMENTS = ["清晨", "上午", "午后", "傍晚", "夜间"]

def _load():
    if TL_PATH.exists():
        return json.loads(TL_PATH.read_text(encoding="utf-8"))
    TL_PATH.write_text(json.dumps(DEFAULT_TL, ensure_ascii=False, indent=2), encoding="utf-8")
    return DEFAULT_TL

def _save(obj):
    TL_PATH.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def get_slice() -> dict:
    return _load()

def tick(mode: str = "dialogue") -> dict:
    tl = _load()
    seg = tl["now"]["time_of_day"]
    i = SEGMENTS.index(seg) if seg in SEGMENTS else 1
    i = (i + 1) % len(SEGMENTS)
    tl["now"]["time_of_day"] = SEGMENTS[i]
    # 随机微调天气
    if random.random() < 0.2:
        tl["environment"]["weather"] = random.choice(["晴","多云","微风","小雨"])
    # 生成一个简单beat：西瓜摊（周末+上午/午后）
    wd = tl["now"]["weekday"]
    if wd in ["周六","周日"] and tl["now"]["time_of_day"] in ["上午","午后"]:
        tl["beats"] = [{
            "id": "beat_watermelon_vendor_morning",
            "status": "suggest",
            "trigger": "周末+白天",
            "participants": ["player", "agent", "npc_watermelon_01?"],
            "suggested_session": "market_stall_01",
            "npc_spawn": {"name_hint": "老王", "role": "卖西瓜的"}
        }]
    else:
        tl["beats"] = []
    _save(tl)
    return tl