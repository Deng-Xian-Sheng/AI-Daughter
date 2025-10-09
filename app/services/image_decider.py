# app/services/image_decider.py
from __future__ import annotations
import json
from typing import Dict, Any
from app.config import load_settings
from app.providers.llm_vlm import make_llm_client

SYSTEM = """你是对话中的“图像生成决策器”。根据本轮用户输入与AI回复、上下文时间线，判断是否需要生成图片，并决定模式：
- generate: true/false
- mode: "img2img" 或 "text2img"
- target: 用中文简洁描述要生成的内容（1-2句）
- reason: 简要理由
- confidence: 0~1
硬性规则：
1) recent_image_count >= limit_per_10min → generate=false
2) 用户明确拒绝（例如“不要图”“别生成”）→ generate=false
3) 若与AI女儿/她/琪琪/卧室/房间等强相关，且 has_ref=true → mode=img2img；若 has_ref=false → mode=text2img
4) 需求与AI女儿/其房间无关的场景图（例如市场摊位、路人、风景）→ mode=text2img
只输出JSON，不要多余文本。"""

def decide_image_llm(
    user_text: str,
    reply_text: str,
    timeline: Dict[str, Any],
    has_ref: bool,
    recent_image_count: int,
    limit_per_10min: int
) -> Dict[str, Any]:
    cfg = load_settings()
    provider = cfg.providers.llm
    model = cfg.model_ids.llm.modelscope if provider == "modelscope" else cfg.model_ids.llm.bailian
    client = make_llm_client(provider)

    tl_now = timeline.get("now", {})
    tl_env = timeline.get("environment", {})
    tl_brief = f"时间段:{tl_now.get('time_of_day','')}, 星期:{tl_now.get('weekday','')}, 天气:{tl_env.get('weather','')}, 城市:{tl_env.get('city','')}"

    user = (
        f"用户：{user_text}\n"
        f"AI回复：{reply_text}\n"
        f"时间线：{tl_brief}\n"
        f"has_ref: {str(has_ref).lower()}, recent_image_count: {recent_image_count}, limit_per_10min: {limit_per_10min}\n"
        "请只输出JSON：{\"generate\":true/false,\"mode\":\"img2img|text2img\",\"target\":\"...\",\"reason\":\"...\",\"confidence\":0.xx}"
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user}
        ],
        stream=False
    )
    text = resp.choices[0].message.content
    try:
        data = json.loads(text)
    except Exception:
        data = {"generate": False, "mode": "text2img", "target": "", "reason": "parse-fallback", "confidence": 0.0}
    # 兜底与规范化
    if not isinstance(data.get("generate"), bool):
        data["generate"] = False
    if data["generate"] is False:
        data["mode"] = "text2img"
        data["target"] = data.get("target", "")
        return data
    if data.get("mode") not in ("img2img", "text2img"):
        data["mode"] = "text2img"
    data["target"] = data.get("target", f"{user_text}；参考回复：{reply_text}")[:200]
    return data