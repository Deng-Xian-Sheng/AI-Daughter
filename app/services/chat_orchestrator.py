from __future__ import annotations
import asyncio, re, uuid, threading
from typing import List, Dict, Tuple, Optional
from app.providers.llm_vlm import call_llm
from app.config import load_settings
from app.services.memory_store import load_messages, append_message, get_entities, get_session
from app.services.relationships import title_of
from app.services.sse_hub import hub
from app.services.timeline_engine import get_slice, tick as tl_tick
from app.services.image_service import run_image_task
from app.services.ref_selector import select_reference
from app.services.ref_registry import register_ref_image
from app.services.edit_planner import plan_img2img_edit
from datetime import datetime, timedelta
import re, json
from pathlib import Path
from app.services.image_decider import decide_image_llm
from app.services.memory_store import load_messages
from app.config import load_settings, DATA_DIR

MAX_CONTEXT = 12

def _recent_images_count(session_id: str, minutes: int = 10) -> int:
    try:
        msgs = load_messages(session_id)
        now = datetime.utcnow()
        dt = timedelta(minutes=minutes)
        c = 0
        for m in reversed(msgs):
            if m.get("type") == "image":
                created = m.get("created_at")
                if not created: continue
                t = datetime.fromisoformat(created)
                if now - t <= dt:
                    c += 1
                else:
                    break
        return c
    except Exception:
        return 0

def _need_image_regex(user_text: str, reply_text: str):
    kw = "发图|看看|给我看|画一个|拍一张|起床|揉眼睛|刷牙|看书|买西瓜|西瓜|市场|户外|野外|卧室|房间"
    if re.search(kw, user_text) or re.search(kw, reply_text):
        if re.search("她|你|琪琪|女儿|卧室|房间", user_text + reply_text):
            return True, "img2img", f"{user_text}；若不明确则依据回复内容：{reply_text}"
        return True, "text2img", f"{user_text}；参考回复：{reply_text}"
    return False, "text2img", ""

def _has_refs() -> bool:
    ref_dir = Path(DATA_DIR / "refs")
    return ref_dir.exists() and any(ref_dir.glob("*.json"))

def _need_image_llm_decision(user_text: str, reply_text: str, session_id: str):
    cfg = load_settings()
    tl = get_slice()
    has_ref = _has_refs()
    recent = _recent_images_count(session_id, minutes=10)
    limit = cfg.limits.images_per_session_per_10min

    try:
        data = decide_image_llm(user_text, reply_text, tl, has_ref, recent, limit)
        if not data.get("generate"):
            return False, "text2img", ""
        mode = data.get("mode", "text2img")
        target = data.get("target", f"{user_text}；参考回复：{reply_text}")
        return True, mode, target
    except Exception:
        # 回退正则
        return _need_image_regex(user_text, reply_text)

def _render_name(sender_id: str) -> str:
    ents = get_entities()
    if sender_id == "player":
        return ents["users"]["player"]["name"]
    if sender_id == "agent":
        return ents["agents"]["agent"]["name"]
    if sender_id.startswith("npc_"):
        return ents["npcs"].get(sender_id, {}).get("name", sender_id)
    return sender_id

def _build_system_prompt(session_id: str) -> str:
    tl = get_slice()
    sess = get_session(session_id)
    participants = sess["participants"]
    names = {pid: _render_name(pid) for pid in participants}
    # 称谓映射
    titles = []
    for a in participants:
        for b in participants:
            if a == b: continue
            t = title_of(a, b)
            if t:
                titles.append(f"{_render_name(a)}称呼{_render_name(b)}为“{t}”")
    titles_text = "；".join(titles) if titles else "参与者间称谓已知。"

    sys = f"""
你是AI女儿“{_render_name('agent')}”，家庭向、温柔关心、幽默克制，避免任何暧昧或不当暗示。
以中文自然交流，内容具体、生活化，避免太书面。必要时主动提出合理的小建议或小行动。

当前时间线：
- 日期进度：第{tl['now']['day']}天，{tl['now']['weekday']}，时段：{tl['now']['time_of_day']}
- 大环境：城市：{tl['environment']['city']}，天气：{tl['environment']['weather']}，气温：{tl['environment']['temp']}
- 事件提示：{[b['id'] for b in tl.get('beats',[])]}

参与者：{[names[p] for p in participants]}
称谓：{titles_text}

安全边界：未成年设定，避免性化或敏感话题；若用户请求不当内容，委婉拒绝并转移话题。
回复要求：简洁自然（50~120字为宜），如需确认或推进，给出清晰选项或提问。
"""
    return sys.strip()

def _gather_context(sess_id: str) -> List[Dict]:
    msgs = load_messages(sess_id)[-MAX_CONTEXT:]
    ctx: List[Dict] = []
    for m in msgs:
        if m["type"] == "text" and m["text"]:
            role = "assistant" if m["sender_id"] == "agent" else "user"
            ctx.append({"role": role, "content": m["text"]})
        elif m["type"] == "image":
            # 将图片的VLM摘要拼成一条user说明，避免塞图
            image_id = m.get("image_id")
            if image_id:
                # 这里采用同步缓存读取（调用时机：图片刚上传后会触发describe）
                # 若未解析完成，此处跳过也可
                from pathlib import Path
                from app.config import IMAGE_META_DIR
                meta_file = IMAGE_META_DIR / f"{image_id}.json"
                if meta_file.exists():
                    import json
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    cap = meta.get("summary", {}).get("caption", "")
                    if cap:
                        ctx.append({"role":"user","content": f"[图片摘要] {cap}"})
    return ctx

async def _watch_and_publish_task(session_id: str, task_id: str):
    from app.services.image_service import get_task
    for _ in range(180):
        st = get_task(task_id)
        if st["status"] in ("SUCCEEDED","FAILED"):
            if st["status"] == "SUCCEEDED" and st.get("result",{}).get("image_id"):
                image_id = st["result"]["image_id"]
                # 关键：meta.kind=generated
                mid = append_message(session_id, "agent", "image", image_id=image_id, meta={"kind": "generated"})
                await hub.publish(session_id, {
                    "type":"message_new",
                    "message": {
                        "id": mid, "session_id": session_id,
                        "sender_id":"agent", "type":"image",
                        "image_id": image_id,
                        "meta": {"kind":"generated"}
                    }
                })
            # 保留任务事件（前端将忽略，不再造临时气泡）
            await hub.publish(session_id, {"type":"image_task_done", "task_id": task_id, "status": st["status"], "result": st.get("result")})
            break
        await asyncio.sleep(2)

async def handle_user_message(session_id: str, user_text: Optional[str]):
    cfg = load_settings()
    system = _build_system_prompt(session_id)
    context = _gather_context(session_id)
    msgs = context + [{"role": "user", "content": user_text or ""}]

    provider = cfg.providers.llm
    model = cfg.model_ids.llm.modelscope if provider=="modelscope" else cfg.model_ids.llm.bailian

    loop = asyncio.get_running_loop()
    q: asyncio.Queue[dict] = asyncio.Queue()
    temp_id = f"tmp-{uuid.uuid4().hex[:8]}"
    full_text_parts: List[str] = []
    got_any = {"v": False}

    def worker():
        try:
            resp = call_llm(provider, model, system, msgs, stream=True)
            for chunk in resp:
                piece = None
                try:
                    # OpenAI SDK 风格
                    piece = getattr(chunk.choices[0].delta, "content", None)
                except Exception:
                    try:
                        # 兼容某些实现
                        piece = chunk.choices[0].delta.get("content") if hasattr(chunk.choices[0], "delta") else None
                    except Exception:
                        piece = None
                if piece:
                    got_any["v"] = True
                    loop.call_soon_threadsafe(q.put_nowait, {"t": "delta", "s": piece})
        except Exception:
            pass
        finally:
            loop.call_soon_threadsafe(q.put_nowait, {"t": "done", "got": got_any["v"]})

    threading.Thread(target=worker, daemon=True).start()

    # 通知前端开始
    await hub.publish(session_id, {"type":"text_start", "temp_id": temp_id})

    # 消费分片
    while True:
        item = await q.get()
        if item["t"] == "delta":
            s = item["s"]
            full_text_parts.append(s)
            await hub.publish(session_id, {"type":"text_delta", "temp_id": temp_id, "delta": s})
        elif item["t"] == "done":
            break

    full_text = "".join(full_text_parts).strip()

    # 无分片回退：走非流式拿完整文本，而不是“嗯嗯，我在的～”
    if not full_text:
        try:
            non_stream = call_llm(provider, model, system, msgs, stream=False)
            if hasattr(non_stream, "choices"):
                full_text = non_stream.choices[0].message.content or ""
        except Exception:
            pass
    if not full_text:
        full_text = "嗯嗯，我在的～"

    # 落库最终消息
    final_id = append_message(session_id, "agent", "text", text=full_text)

    # 通知流式结束（前端用 text_done 把临时气泡替换为最终气泡）
    await hub.publish(session_id, {"type":"text_done", "temp_id": temp_id, "final_id": final_id, "text": full_text})

    # 注意：不再重复发送 agent 文本的 message_new，避免出现两条

    # 时间线推进 + 提示
    tl = tl_tick(mode="dialogue")
    await hub.publish(session_id, {"type":"timeline_hint", "slice": tl})

    # 图像决定与任务（img2img 优先，使用LLM决策）
    if user_text:
        need, mode, target = _need_image_llm_decision(user_text, full_text, session_id)
        if need:
            from app.services.prompt_writer import build_text2img_prompt, build_img2img_edit_prompt
            try:
                if mode == "img2img":
                    # refs 读取
                    REF_DIR = Path(__file__).resolve().parents[2] / "data" / "refs"
                    refs = []
                    if REF_DIR.exists():
                        for f in REF_DIR.glob("*.json"):
                            try:
                                refs.append(json.loads(f.read_text(encoding="utf-8")))
                            except Exception:
                                pass
                    if not refs:
                        # 回退 text2img
                        pos2, neg2 = build_text2img_prompt({
                            "who":"女孩","where":"卧室或对话相关场所",
                            "action":"与描述相符的动作","props":"家居小物或相关道具",
                            "lighting":"暖光/自然光","framing":"中景","style":"写实"
                        })
                        task_id = await run_image_task("text2img", pos2, neg2, "auto", None, None, None)
                        await hub.publish(session_id, {"type":"image_task_queued", "task_id": task_id})
                        asyncio.create_task(_watch_and_publish_task(session_id, task_id))
                    else:
                        # 选择参考图
                        ref_choice = await select_reference(target, refs)
                        ref_id = ref_choice.get("ref_id")
                        if not ref_id:
                            pos2, neg2 = build_text2img_prompt({
                                "who":"女孩","where":"卧室或对话相关场所",
                                "action":"与描述相符的动作","props":"家居小物或相关道具",
                                "lighting":"暖光/自然光","framing":"中景","style":"写实"
                            })
                            task_id = await run_image_task("text2img", pos2, neg2, "auto", None, None, None)
                            await hub.publish(session_id, {"type":"image_task_queued", "task_id": task_id})
                            asyncio.create_task(_watch_and_publish_task(session_id, task_id))
                        else:
                            # 注册ref并计划编辑
                            reg = register_ref_image(ref_id)
                            ref_image_id = reg["image_id"]

                            # 读取参考图JSON，带入planner
                            ref_json = None
                            try:
                                rf = REF_DIR / f"{ref_id}.json"
                                if rf.exists():
                                    ref_json = json.loads(rf.read_text(encoding="utf-8"))
                            except Exception:
                                pass

                            plan = plan_img2img_edit(
                                target_text=target, ref_meta=ref_json, timeline=tl
                            )
                            pos, neg = build_img2img_edit_prompt(plan)

                            task_id = await run_image_task("img2img", pos, neg, "auto", None, ref_image_id, None)
                            await hub.publish(session_id, {"type":"image_task_queued", "task_id": task_id})
                            asyncio.create_task(_watch_and_publish_task(session_id, task_id))
                else:
                    # text2img
                    pos, neg = build_text2img_prompt({
                        "who":"场景元素或路人","where":"与对话相关地点",
                        "action":"关键行为","props":"相关道具",
                        "lighting":"自然","framing":"中景","style":"写实"
                    })
                    task_id = await run_image_task("text2img", pos, neg, "auto", None, None, None)
                    await hub.publish(session_id, {"type":"image_task_queued", "task_id": task_id})
                    asyncio.create_task(_watch_and_publish_task(session_id, task_id))
            except Exception:
                # 安全回退：不打断主对话
                pass