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

MAX_CONTEXT = 12

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

def _need_image(user_text: str, reply_text: str) -> Tuple[bool, str, str]:
    """
    返回: (是否生成图, 模式 text2img|img2img, 目标描述)
    """
    kw = "发图|看看|给我看|画一个|拍一张|起床|揉眼睛|刷牙|看书|买西瓜|西瓜|市场|户外|野外|卧室|房间"
    if re.search(kw, user_text) or re.search(kw, reply_text):
        # 若涉及“AI女儿/卧室/她/房间” 更倾向img2img
        if re.search("她|你|琪琪|女儿|卧室|房间", user_text + reply_text):
            return True, "img2img", f"{user_text}；若不明确则依据回复内容：{reply_text}"
        return True, "text2img", f"{user_text}；参考回复：{reply_text}"
    return False, "text2img", ""

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

    # 图像决定与任务（img2img 优先）
    print(f"🔍 DEBUG: 开始图像决策流程，user_text='{user_text}', full_text='{full_text}'")
    
    if user_text:
        print(f"🔍 DEBUG: 调用 _need_image 分析文本需求")
        need, mode, target = _need_image(user_text, full_text)
        print(f"🔍 DEBUG: _need_image 返回: need={need}, mode={mode}, target='{target}'")
        
        if need:
            print(f"🔍 DEBUG: 需要生成图像，模式: {mode}")
            from app.services.prompt_writer import build_text2img_prompt, build_img2img_edit_prompt
            try:
                if mode == "img2img":
                    print(f"🔍 DEBUG: 进入 img2img 分支")
                    
                    # 1) 读取参考图库
                    print(f"🔍 DEBUG: 开始读取参考图库")
                    import json
                    from pathlib import Path
                    REF_DIR = Path(__file__).resolve().parents[2] / "data" / "refs"
                    print(f"🔍 DEBUG: 参考图目录: {REF_DIR}")
                    
                    refs = []
                    if REF_DIR.exists():
                        print(f"🔍 DEBUG: 参考图目录存在，开始扫描JSON文件")
                        json_files = list(REF_DIR.glob("*.json"))
                        print(f"🔍 DEBUG: 找到 {len(json_files)} 个JSON文件")
                        
                        for f in json_files:
                            try:
                                print(f"🔍 DEBUG: 读取文件: {f.name}")
                                ref_data = json.loads(f.read_text(encoding="utf-8"))
                                refs.append(ref_data)
                                print(f"🔍 DEBUG: 成功加载参考数据，ref_id: {ref_data.get('ref_id', 'unknown')}")
                            except Exception as e:
                                print(f"❌ DEBUG: 读取参考文件失败 {f.name}: {e}")
                                pass
                    else:
                        print(f"⚠️ DEBUG: 参考图目录不存在: {REF_DIR}")

                    print(f"🔍 DEBUG: 总共加载了 {len(refs)} 个参考图数据")

                    # 2) 无参考图则回退 text2img
                    if not refs:
                        print(f"⚠️ DEBUG: 无参考图可用，回退到 text2img")
                        pos2, neg2 = build_text2img_prompt({
                            "who":"女孩","where":"卧室或对话相关场所",
                            "action":"与描述相符的动作","props":"家居小物或相关道具",
                            "lighting":"暖光/自然光","framing":"中景","style":"写实"
                        })
                        print(f"🔍 DEBUG: text2img 提示词 - 正面: {pos2}")
                        print(f"🔍 DEBUG: text2img 提示词 - 负面: {neg2}")
                        
                        task_id = await run_image_task("text2img", pos2, neg2, "auto", None, None, None)
                        print(f"🔍 DEBUG: text2img 任务已创建，task_id: {task_id}")
                        
                        await hub.publish(session_id, {"type":"image_task_queued", "task_id": task_id})
                        asyncio.create_task(_watch_and_publish_task(session_id, task_id))
                        print(f"🔍 DEBUG: text2img 任务已发布和监视")
                    else:
                        # 3) LLM 选择最匹配参考图
                        print(f"🔍 DEBUG: 开始选择最匹配的参考图，目标: '{target}'")
                        ref_choice = await select_reference(target, refs)
                        print(f"🔍 DEBUG: select_reference 返回: {ref_choice}")
                        
                        ref_id = ref_choice.get("ref_id")
                        print(f"🔍 DEBUG: 选择的参考图 ID: {ref_id}")

                        if not ref_id:
                            # 安全回退
                            print(f"⚠️ DEBUG: 未选择到参考图，安全回退到 text2img")
                            pos2, neg2 = build_text2img_prompt({
                                "who":"女孩","where":"卧室或对话相关场所",
                                "action":"与描述相符的动作","props":"家居小物或相关道具",
                                "lighting":"暖光/自然光","framing":"中景","style":"写实"
                            })
                            print(f"🔍 DEBUG: 安全回退提示词 - 正面: {pos2}")
                            print(f"🔍 DEBUG: 安全回退提示词 - 负面: {neg2}")
                            
                            task_id = await run_image_task("text2img", pos2, neg2, "auto", None, None, None)
                            print(f"🔍 DEBUG: 安全回退任务已创建，task_id: {task_id}")
                            
                            await hub.publish(session_id, {"type":"image_task_queued", "task_id": task_id})
                            asyncio.create_task(_watch_and_publish_task(session_id, task_id))
                            print(f"🔍 DEBUG: 安全回退任务已发布和监视")
                        else:
                            # 4) 注册参考图为可用 ref_image_id（复制到 uploads/）
                            print(f"🔍 DEBUG: 开始注册参考图，ref_id: {ref_id}")
                            reg = register_ref_image(ref_id)
                            print(f"🔍 DEBUG: register_ref_image 返回: {reg}")
                            
                            ref_image_id = reg["image_id"]
                            print(f"🔍 DEBUG: 注册后的图像ID: {ref_image_id}")

                            # 5) 生成 img2img 编辑提示词（强调"保持身份/五官/发色不变"）
                            print(f"🔍 DEBUG: 生成 img2img 编辑提示词")
                            pos, neg = build_img2img_edit_prompt({
                                "change_action": "根据本轮描述进行的具体动作/姿态/道具变化",
                                "change_env": "如需从卧室切到目标环境则调整，否则保留原环境并轻微微调",
                                "props": "按描述增减",
                                "lighting": "自然/暖光，柔和",
                                "framing": "中景"
                            })
                            print(f"🔍 DEBUG: img2img 编辑提示词 - 正面: {pos}")
                            print(f"🔍 DEBUG: img2img 编辑提示词 - 负面: {neg}")

                            # 6) 触发 img2img，完成后落库由 _watch_and_publish_task 负责
                            print(f"🔍 DEBUG: 开始创建 img2img 任务")
                            task_id = await run_image_task("img2img", pos, neg, "auto", None, ref_image_id, None)
                            print(f"🔍 DEBUG: img2img 任务已创建，task_id: {task_id}")
                            
                            await hub.publish(session_id, {"type":"image_task_queued", "task_id": task_id})
                            asyncio.create_task(_watch_and_publish_task(session_id, task_id))
                            print(f"🔍 DEBUG: img2img 任务已发布和监视")

                else:
                    # 纯场景/非女儿/非卧室 → 文生图
                    print(f"🔍 DEBUG: 进入 text2img 分支 (非img2img模式)")
                    pos, neg = build_text2img_prompt({
                        "who":"场景元素或路人","where":"与对话相关地点",
                        "action":"关键行为","props":"相关道具",
                        "lighting":"自然","framing":"中景","style":"写实"
                    })
                    print(f"🔍 DEBUG: text2img 提示词 - 正面: {pos}")
                    print(f"🔍 DEBUG: text2img 提示词 - 负面: {neg}")
                    
                    task_id = await run_image_task("text2img", pos, neg, "auto", None, None, None)
                    print(f"🔍 DEBUG: text2img 任务已创建，task_id: {task_id}")
                    
                    await hub.publish(session_id, {"type":"image_task_queued", "task_id": task_id})
                    asyncio.create_task(_watch_and_publish_task(session_id, task_id))
                    print(f"🔍 DEBUG: text2img 任务已发布和监视")

            except Exception as e:
                print(f"❌ DEBUG: 图像生成主流程异常: {e}")
                import traceback
                print(f"❌ DEBUG: 异常堆栈: {traceback.format_exc()}")
                
                # 失败安全回退：避免影响对话体验
                try:
                    print(f"🔄 DEBUG: 开始安全回退流程")
                    pos2, neg2 = build_text2img_prompt({
                        "who":"场景元素或女孩","where":"与对话相关地点",
                        "action":"关键行为","props":"相关道具",
                        "lighting":"自然/暖光","framing":"中景","style":"写实"
                    })
                    print(f"🔍 DEBUG: 安全回退提示词 - 正面: {pos2}")
                    print(f"🔍 DEBUG: 安全回退提示词 - 负面: {neg2}")
                    
                    task_id = await run_image_task("text2img", pos2, neg2, "auto", None, None, None)
                    print(f"🔍 DEBUG: 安全回退任务已创建，task_id: {task_id}")
                    
                    await hub.publish(session_id, {"type":"image_task_queued", "task_id": task_id})
                    asyncio.create_task(_watch_and_publish_task(session_id, task_id))
                    print(f"🔍 DEBUG: 安全回退任务已发布和监视")
                except Exception as inner_e:
                    print(f"❌ DEBUG: 安全回退也失败: {inner_e}")
                    # 最终忽略（不打断主对话）
                    print(f"⚠️ DEBUG: 图像生成完全失败，但继续对话流程")
        else:
            print(f"🔍 DEBUG: 不需要生成图像，跳过图像处理")
    else:
        print(f"🔍 DEBUG: user_text 为空，跳过图像处理")