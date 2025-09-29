from __future__ import annotations
import asyncio
from typing import Dict, Set, Any, AsyncGenerator

class SSEHub:
    def __init__(self):
        self._subs: Dict[str, Set[asyncio.Queue]] = {}

    def _get_set(self, session_id: str) -> Set[asyncio.Queue]:
        return self._subs.setdefault(session_id, set())

    async def publish(self, session_id: str, event: dict):
        qs = list(self._get_set(session_id))
        for q in qs:
            try:
                await q.put(event)
            except Exception:
                pass

    async def subscribe(self, session_id: str) -> AsyncGenerator[dict, None]:
        q: asyncio.Queue = asyncio.Queue()
        self._get_set(session_id).add(q)
        try:
            while True:
                ev = await q.get()
                yield ev
        finally:
            self._get_set(session_id).discard(q)

hub = SSEHub()