from __future__ import annotations
from fastapi import Request
from fastapi.responses import StreamingResponse
import asyncio, json

async def sse_stream(generator):
    async def event_gen():
        async for ev in generator:
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)
    return StreamingResponse(event_gen(), media_type="text/event-stream")