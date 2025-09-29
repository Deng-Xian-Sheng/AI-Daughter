from __future__ import annotations
from pathlib import Path
import json, base64
from app.config import load_settings, IMAGE_META_DIR, IMAGES_DIR
from app.providers.llm_vlm import call_vlm

SUMMARY_PROMPT = "请用简洁结构化JSON总结图片：{caption, scene, actions, objects, faces, clothing, tags}，中文输出。"

def image_public_or_data_uri(image_rel_path: str) -> str:
    cfg = load_settings()
    mode = cfg.image_transport.modelscope  # image transport policy for modelscope VLM也可用
    if mode == "public_url":
        return f"{cfg.image_transport.public_base_url}{cfg.image_transport.static_path_prefix}/{image_rel_path}"
    # data uri
    p = IMAGES_DIR / image_rel_path
    mime = "image/png" if p.suffix.lower()==".png" else "image/jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def _extract_json(text: str) -> dict | None:
    import json, re
    if not text:
        return None
    # 优先提取```json ... ``` 或 ``` ... ```
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    raw = fence.group(1) if fence else None
    if not raw:
        # 回退：截取第一个 { 到最后一个 } 之间尝试解析
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw = text[start:end+1]
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None

async def describe_image(image_id: str, provider: str | None = None) -> dict:
    """Run VLM once and cache."""
    meta_path = IMAGE_META_DIR / f"{image_id}.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))

    cfg = load_settings()
    prov = provider or cfg.providers.vlm
    model = cfg.model_ids.vlm.modelscope if prov=="modelscope" else cfg.model_ids.vlm.bailian
    # our images are in generated/ or uploads/
    # try generated first
    rel = f"generated/{image_id}.png"
    p = IMAGES_DIR / rel
    if not p.exists():
        rel = f"uploads/{image_id}.png"
        p = IMAGES_DIR / rel
    url_or_data = image_public_or_data_uri(rel)
    resp = call_vlm(prov, model, SUMMARY_PROMPT, url_or_data, stream=False)
    if hasattr(resp, "choices"):
        text = resp.choices[0].message.content
    else:
        text = ""
    data = _extract_json(text) or {"caption": text, "tags": []}
    meta = {"id": image_id, "summary": data}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta