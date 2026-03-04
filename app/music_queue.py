import asyncio
from typing import Dict, List, Optional, Tuple

Track = Tuple[str, str, Optional[str], Optional[str]]

class MusicQueue:
    def __init__(self) -> None:
        self.queues: Dict[int, asyncio.Queue[Track]] = {}
        self.now_playing: Dict[int, Track] = {}

    def ensure(self, chat_id: int) -> asyncio.Queue:
        if chat_id not in self.queues:
            self.queues[chat_id] = asyncio.Queue()
        return self.queues[chat_id]

    async def add(self, chat_id: int, track: Track) -> None:
        q = self.ensure(chat_id)
        await q.put(track)

    async def next(self, chat_id: int) -> Optional[Track]:
        q = self.ensure(chat_id)
        if q.empty():
            self.now_playing.pop(chat_id, None)
            return None
        t = await q.get()
        self.now_playing[chat_id] = t
        return t

    def current(self, chat_id: int) -> Optional[Track]:
        return self.now_playing.get(chat_id)

    def pending(self, chat_id: int) -> List[Track]:
        q = self.ensure(chat_id)
        return list(q._queue)

    def clear(self, chat_id: int) -> None:
        if chat_id in self.queues:
            q = self.queues[chat_id]
            while not q.empty():
                q.get_nowait()
        self.now_playing.pop(chat_id, None)
