from __future__ import annotations

NEGATIVE_COMMON = "低分辨率, 最差质量, 模糊, 过曝, 过暗, 变形, 畸形, bad hands, 文字, logo, 水印, 涂抹痕迹, 不自然皮肤, 夸张滤镜, 版权标记, 暧昧或性化, gore, injury"

def decide_size(aspect_policy: str = "auto", scene_hint: str | None = None) -> str:
    # portrait: 1140x1472; square: 1328x1328; landscape: 1664x928
    if aspect_policy == "portrait":
        return "1140x1472"
    if aspect_policy == "square":
        return "1328x1328"
    if aspect_policy == "landscape":
        return "1664x928"
    # auto: heuristic by scene
    if scene_hint and any(k in scene_hint for k in ["卧室", "肖像", "近景"]):
        return "1140x1472"
    if scene_hint and any(k in scene_hint for k in ["广角", "街道", "市场", "风景", "叙事"]):
        return "1664x928"
    return "1328x1328"

def build_text2img_prompt(desc: dict) -> tuple[str, str]:
    """
    desc: {who?, where, action, props?, lighting?, framing?, style?}
    """
    who = desc.get("who", "")
    where = desc.get("where", "")
    action = desc.get("action", "")
    props = desc.get("props", "")
    lighting = desc.get("lighting", "自然光/暖光，柔和")
    framing = desc.get("framing", "中景")
    style = desc.get("style", "写实风格，画面干净，高分辨率")
    pos = f"{who} 在 {where}，正在 {action}，包含 {props}。构图为{framing}，光线为{lighting}，{style}。"
    return pos, NEGATIVE_COMMON

def build_img2img_edit_prompt(edit: dict) -> tuple[str, str]:
    """
    edit: {keep_identity: True, change_action, change_env?, props?, lighting?, framing?}
    """
    keep = "保持人物身份、五官、发色、发型不变；"
    action = f"将人物动作改为 {edit.get('change_action','')}; "
    env = f"背景调整为 {edit.get('change_env','原环境微调')}; "
    props = f"添加/替换道具为 {edit.get('props','按需保持')}; "
    lighting = f"光线 {edit.get('lighting','自然柔和')}; "
    framing = f"构图以 {edit.get('framing','中景')} 为主；"
    style = "整体风格与参考图一致；无文字与水印；高分辨率。"
    pos = keep + action + env + props + lighting + framing + style
    return pos, NEGATIVE_COMMON

def build_avatar_prompts(constraints: dict, n: int = 4) -> list[tuple[str, str]]:
    """
    constraints: {gender, age, hairstyle?, vibe?}
    """
    g = constraints.get("gender","female")
    age = constraints.get("age","teen")
    hair = constraints.get("hairstyle","黑色长发，自然垂落")
    vibe = constraints.get("vibe","清秀自然、干净")
    base = f"写实风格的人像头像，{g}/{age}，{hair}，气质{vibe}。五官自然清晰，肤色均匀，简洁纯净背景，柔和自然光，高分辨率，无文字与水印。"
    return [(base, NEGATIVE_COMMON) for _ in range(n)]