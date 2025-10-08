from __future__ import annotations
import json
from typing import Optional, Dict
from app.config import load_settings
from app.providers.llm_vlm import make_llm_client

PLAN_SYSTEM = """你是图像编辑规划助手。根据用户本轮目标，将修改点结构化输出JSON，不要多余文字。字段：
- change_action: 简短动词短语，如“起床揉眼睛”“刷牙”“坐着看书”
- change_env: 若需要更换环境，给出如“卧室”“浴室”“厨房”“市场摊位”“户外草地”；不变则“原环境微调”
- props: 关键道具，如“牙刷、杯子、书、本子、手机”
- lighting: 如“暖光”“自然光”“侧逆光”，可结合时间线
- framing: “近景/中景/全景”之一
要求：中文输出，严格JSON，不要注释、不要多字段。
"""

def plan_img2img_edit(target_text: str, ref_meta: Optional[Dict] = None, timeline: Optional[Dict] = None) -> Dict:
    """返回: {change_action, change_env, props, lighting, framing}"""
    cfg = load_settings()
    provider = cfg.providers.llm
    model = cfg.model_ids.llm.modelscope if provider=="modelscope" else cfg.model_ids.llm.bailian
    client = make_llm_client(provider)

    ref_hint = ""
    if ref_meta:
        try:
            env = ref_meta.get("env", {})
            ch  = ref_meta.get("character", {})
            ref_hint = f"参考图环境：{env.get('location','未知')}，光线：{env.get('lighting','')}；人物特征：发型/发色：{ch.get('hair','')}，服装：{ch.get('clothing','')}。"
        except Exception:
            pass
    tl_hint = ""
    if timeline:
        tl_hint = f"当前时间线：{timeline.get('now',{}).get('time_of_day','')}；天气：{timeline.get('environment',{}).get('weather','')}。"

    user = f"目标描述：{target_text}\n{ref_hint}\n{tl_hint}\n请只输出JSON。"
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":PLAN_SYSTEM},{"role":"user","content":user}],
        stream=False
    )
    text = resp.choices[0].message.content
    try:
        data = json.loads(text)
    except Exception:
        data = {
            "change_action": "保持姿态轻微调整",
            "change_env": "原环境微调",
            "props": "按需保持",
            "lighting": "自然柔和",
            "framing": "中景"
        }
    # 兜底标准化
    data.setdefault("change_action", "保持姿态轻微调整")
    data.setdefault("change_env", "原环境微调")
    data.setdefault("props", "按需保持")
    data.setdefault("lighting", "自然柔和")
    data.setdefault("framing", "中景")
    return data