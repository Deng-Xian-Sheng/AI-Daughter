#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import base64
import argparse
import logging
import time
from typing import Any, Dict, Optional
from openai import OpenAI

DEFAULT_BASE_URL = "https://api-inference.modelscope.cn/v1"
DEFAULT_MODEL = "Qwen/Qwen2.5-VL-72B-Instruct"


def build_prompt(image_filename: str, path_prefix: str) -> str:
    """
    生成给 VLM 的强提示词（中文），包含字段释义、取值建议、映射小抄和强约束。
    """
    return f"""
你是一个图像理解到结构化 JSON 的专家。请根据下图内容，生成一个描述性 JSON，用于后续图像编辑参考。

务必严格遵循以下要求：
- 仅输出一段纯 JSON（不要包含任何解释、Markdown 代码块标记、语言标签、注释或多余文本）。
- 字段名和层级必须与给定结构完全一致。
- caption、env.*、character.*、tags 用中文；style 列表用英文短语（如 realistic, soft lighting）。
- 布尔值必须为 true/false（不要使用“是/否”“True/False”字符串）。
- id 命名规则：全小写、snake_case、有语义（如 ref_bedroom_reading），不要包含空格或中文。
- path 字段固定为: {path_prefix}/{image_filename}
- 如果画面中无人物，character.gender 设为 "none"，其余可用 "none" 或 "无"。
- 如果存在多人物，请以画面主角为准填写 character，并在 tags 中补充“多人”“配角”等。

目标 JSON 结构（字段和类型必须匹配）：
{{
    "id": "<由你命名的语义化ID>",
    "path": "{path_prefix}/{image_filename}",
    "caption": "<一句话中文描述（简洁有画面感）>",
    "env": {{
        "location": "<场景位置>",
        "lighting": "<光线>",
        "style": "<整体画风>",
        "color_palette": ["<主色1>", "<主色2>", "<主色3>"]
    }},
    "character": {{
        "gender": "<female|male|unisex|none>",
        "age": "<child|teen|young|adult|middle|senior|none>",
        "hair": "<发型与颜色或 none>",
        "face": "<脸型与气质或 none>",
        "clothing": "<穿着或 none>",
        "accessories": "<配饰或 无明显饰品 或 none>"
    }},
    "editable": {{
        "pose": true,
        "action": true,
        "props": true,
        "background": true
    }},
    "tags": ["<中文关键词>", "..."],
    "style": ["<英文风格关键词>", "..."]
}}

字段释义与常见取值建议（非枚举，仅帮助你更稳定输出）：
- env.location（场景位置）：卧室、客厅、厨房、书房、教室、办公室、街道、公园、餐厅、咖啡馆、阳台、花园、浴室、车内、车站、舞台、海边、山间等。
- env.lighting（光线氛围）：自然光、逆光、侧逆光、顶光、窗边柔光、暖色台灯、冷色日光、金色夕阳、夜景霓虹、阴天漫反射、强对比、柔和等。
- env.style（整体画风）：写实、纪实、复古、胶片、油画、水彩、黑白、极简、赛博朋克、蒸汽波、二次元、像素风、商业时尚等。
- color_palette（主色）：从画面主色/辅色提炼：暖黄、米白、浅木色、灰蓝、橄榄绿、玫瑰粉、酒红、青绿、木炭灰、墨黑等。
- character.gender：female、male、unisex、none（无人物时）。
- character.age：child、teen、young、adult、middle、senior、none（无人物时）。
- editable.*：根据画面简洁度与主体分离度判断：主体清晰、遮挡少、背景简洁通常更易编辑（true）。

“从图片中看到什么 -> 填到哪”小抄（示例）：
- 看到卧室/床/窗帘 -> env.location = 卧室；tags += 卧室、床
- 看到台灯暖黄光 -> env.lighting = 暖色台灯，柔和；style += soft lighting
- 看到女孩/长发/家居服 -> character.gender = female；hair = 黑色长发；clothing = 家居服
- 看到在读书 -> caption/ tags += 阅读；若姿势清晰 -> editable.pose = true
- 看到木色家具/米白墙面 -> env.color_palette 包含 浅木色、米白
- 画面无人 -> character.gender = none；其它 character 字段填 "none"/"无"

命名 id 的建议：
- 语义化、下划线分词、全小写：如 ref_bedroom_reading、street_cafe_rainy
- 结构可用：<类别/主题>_<场景/主体>_<动作/特征>

当前图片文件名：{image_filename}
请仅输出最终 JSON。记住：不要输出额外文字、不要使用代码块标记。
    """.strip()


def data_url_from_image(file_path: str) -> str:
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def list_pngs_one_level(input_dir: str):
    for name in os.listdir(input_dir):
        if name.lower().endswith(".png"):
            yield os.path.join(input_dir, name)


def strip_code_fences(text: str) -> str:
    # 去掉 ```json ... ``` 或 ``` ... ```
    text = re.sub(r"^\s*```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def extract_first_braced_json(text: str) -> Optional[str]:
    # 从文本中提取第一个平衡的 {...} 片段
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def remove_trailing_commas(s: str) -> str:
    # 粗暴移除对象/数组结尾多余逗号
    prev = None
    cur = s
    while prev != cur:
        prev = cur
        cur = re.sub(r",(\s*[}```])", r"\1", cur)
    return cur


def parse_json_safely(text: str) -> Dict[str, Any]:
    """
    解析模型返回文本中的 JSON。容错：去代码块、提取花括号、去尾逗号。
    """
    candidate = strip_code_fences(text)
    try:
        return json.loads(candidate)
    except Exception:
        pass

    braced = extract_first_braced_json(candidate)
    if not braced:
        raise ValueError("未在模型响应中找到 JSON 对象。")
    try:
        return json.loads(braced)
    except Exception:
        fixed = remove_trailing_commas(braced)
        return json.loads(fixed)


def sanitize_filename(name: str) -> str:
    # 文件名安全化：去掉路径分隔符和不可见字符
    name = name.replace(os.sep, "_").replace("/", "_").strip()
    # 仅保留常见安全字符
    name = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._\-()]+", "_", name)
    # 去除连续下划线
    name = re.sub(r"_+", "_", name)
    return name


def call_vlm(
    client: OpenAI,
    model: str,
    prompt: str,
    data_url: str,
    temperature: float = 0.2,
    max_retries: int = 2,
    try_json_mode: bool = True,
) -> str:
    """
    调用 VLM（ModelScope OpenAI 兼容接口）。尽量让其输出 JSON。
    """
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]

    last_err = None
    for attempt in range(max_retries + 1):
        try:
            kwargs = dict(
                model=model,
                messages=messages,
                temperature=temperature,
                stream=False,
            )
            if try_json_mode:
                # 某些服务可能不支持 response_format；失败则自动降级
                kwargs["response_format"] = {"type": "json_object"}

            resp = client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content
            if isinstance(content, list):
                # 兼容性：某些实现可能返回富内容
                # 仅拼接 text 部分
                texts = [c.get("text", "") for c in content if isinstance(c, dict)]
                content = "\n".join(texts)
            return content
        except Exception as e:
            last_err = e
            if try_json_mode:
                # 降级：去掉 response_format 再试
                try_json_mode = False
            if attempt < max_retries:
                time.sleep(0.8 * (attempt + 1))
            else:
                raise e
    raise last_err


def process_one_image(
    client: OpenAI,
    model: str,
    img_path: str,
    out_dir: str,
    path_prefix: str,
    temperature: float,
    max_retries: int,
) -> Optional[str]:
    fname = os.path.basename(img_path)
    stem, _ = os.path.splitext(fname)
    logging.info(f"Processing: {fname}")

    prompt = build_prompt(image_filename=fname, path_prefix=path_prefix)
    data_url = data_url_from_image(img_path)

    raw = call_vlm(
        client=client,
        model=model,
        prompt=prompt,
        data_url=data_url,
        temperature=temperature,
        max_retries=max_retries,
        try_json_mode=True,
    )

    try:
        data = parse_json_safely(raw)
    except Exception as e:
        logging.error(f"JSON 解析失败 [{fname}]: {e}")
        return None

    # 读取模型生成的 id
    model_id_value = str(data.get("id", "ref_" + stem)).strip()
    if not model_id_value:
        model_id_value = "ref_" + stem

    # 保存文件名遵循：模型取值_图片原始文件名.json（原始文件名不含扩展名）
    out_name = f"{model_id_value}_{stem}.json"
    out_name = sanitize_filename(out_name)
    out_path = os.path.join(out_dir, out_name)

    # 确保目录存在
    os.makedirs(out_dir, exist_ok=True)

    # 直接保存模型原样 JSON（不强改字段），仅确保缩进和中文不转义
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    logging.info(f"Saved: {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="遍历目录中的 PNG 图片，调用 VLM 生成描述 JSON，并按规则保存。"
    )
    parser.add_argument("--input-dir", required=True, help="输入图片目录（仅遍历一层）")
    parser.add_argument("--output-dir", required=True, help="JSON 输出目录")
    parser.add_argument(
        "--path-prefix",
        default="images/refs",
        help="写入 JSON 的 path 字段前缀，例如 images/refs",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("MODELSCOPE_TOKEN", ""),
        help="ModelScope Token（可用环境变量 MODELSCOPE_TOKEN 传入）",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"OpenAI 兼容接口 Base URL（默认 {DEFAULT_BASE_URL}）",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"模型 ID（默认 {DEFAULT_MODEL}）",
    )
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if not args.api_key:
        raise SystemExit("请通过 --api-key 或环境变量 MODELSCOPE_TOKEN 提供访问 Token。")

    client = OpenAI(base_url=args.base_url, api_key=args.api_key)

    pngs = list(list_pngs_one_level(args.input_dir))
    if not pngs:
        logging.warning("未在输入目录找到 .png 文件。")
        return

    logging.info(f"发现 {len(pngs)} 张图片。开始处理...")
    for p in pngs:
        try:
            process_one_image(
                client=client,
                model=args.model,
                img_path=p,
                out_dir=args.output_dir,
                path_prefix=args.path_prefix,
                temperature=args.temperature,
                max_retries=args.max_retries,
            )
        except Exception as e:
            logging.error(f"处理失败 [{os.path.basename(p)}]: {e}")


if __name__ == "__main__":
    main()