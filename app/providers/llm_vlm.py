from __future__ import annotations
import os
from openai import OpenAI

MODELSCOPE_BASE = "https://api-inference.modelscope.cn/v1"
BAILIAN_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"

def make_llm_client(provider: str) -> OpenAI:
    if provider == "modelscope":
        return OpenAI(api_key=os.getenv("MODELSCOPE_API_KEY"), base_url=MODELSCOPE_BASE)
    elif provider == "bailian":
        return OpenAI(api_key=os.getenv("DASHSCOPE_API_KEY"), base_url=BAILIAN_BASE)
    raise ValueError(f"Unknown provider {provider}")

def call_llm(provider: str, model: str, system: str, messages: list[dict], stream: bool = True):
    client = make_llm_client(provider)
    return client.chat.completions.create(
        model=model,
        messages=([{"role": "system", "content": system}] + messages),
        stream=stream,
    )

def call_vlm(provider: str, model: str, prompt: str, image_url: str, stream: bool = False):
    client = make_llm_client(provider)
    return client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }],
        stream=stream
    )