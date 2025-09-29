from __future__ import annotations
import json
from typing import List, Dict
from app.providers.llm_vlm import make_llm_client
from app.config import load_settings

async def select_reference(target_desc: str, refs: List[Dict]) -> Dict:
    """
    refs: [{id, caption, env, character, tags, style}]
    return: {"ref_id": "...", "reason": "..."}
    """
    cfg = load_settings()
    provider = cfg.providers.llm
    model = cfg.model_ids.llm.modelscope if provider=="modelscope" else cfg.model_ids.llm.bailian
    client = make_llm_client(provider)
    system = "你是一个图像参考选择助手。请从候选参考图里选出与目标描述最贴近的一张，仅输出JSON：{ref_id, reason}。"
    content = f"目标描述：{target_desc}\n候选：{json.dumps(refs, ensure_ascii=False)}\n仅输出JSON：{{\"ref_id\":\"...\",\"reason\":\"...\"}}"
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":system},{"role":"user","content":content}],
        stream=False
    )
    text = resp.choices[0].message.content
    try:
        return json.loads(text)
    except Exception:
        # 回退：简单规则选第一条
        return {"ref_id": refs[0]["id"], "reason": "fallback_first"}