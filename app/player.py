import asyncio
from typing import Optional, Tuple, Dict
from pyrogram import Client
import pyrogram.errors as py_errors
if not hasattr(py_errors, "GroupcallForbidden") and hasattr(py_errors, "GroupCallInvalid"):
    py_errors.GroupcallForbidden = py_errors.GroupCallInvalid
from pytgcalls import PyTgCalls
from pytgcalls.types.stream import MediaStream, AudioQuality
from pytgcalls.exceptions import NotInCallError
try:
    from .music_queue import MusicQueue, Track
except Exception:
    import os, sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from app.music_queue import MusicQueue, Track

class Player:
    def __init__(self, user_client: Client) -> None:
        self.user_client = user_client
        self.tgcalls = PyTgCalls(user_client)
        self.queue = MusicQueue()
        self._started = False
        self._lock = asyncio.Lock()
        self.on_track_start = None
        self._flag_queues = {}  # Track flag queues per chat

        self._bind_events()

    def _ensure_flag_queue(self, chat_id: int) -> asyncio.Queue:
        """Ensure a flag queue exists for this chat_id"""
        if chat_id not in self._flag_queues:
            self._flag_queues[chat_id] = asyncio.Queue()
        return self._flag_queues[chat_id]

    def _bind_events(self) -> None:
        @self.tgcalls.on_update()
        async def _(client, update) -> None:
            try:
                from pytgcalls.types.stream import StreamEnded
            except Exception:
                StreamEnded = None
            if StreamEnded is None or not isinstance(update, StreamEnded):
                return
            chat_id = getattr(update, "chat_id", None)
            if chat_id is None:
                chat = getattr(update, "chat", None)
                chat_id = getattr(chat, "id", None)
            if chat_id is None:
                return
            nxt = await self.queue.next(chat_id)
            if nxt:
                await self._play(chat_id, nxt, is_video=False)
            else:
                try:
                    await self.tgcalls.leave_call(chat_id)
                except Exception:
                    pass

    async def start(self) -> None:
        if not self._started:
            await self.tgcalls.start()
            self._started = True

    async def enqueue(self, chat_id: int, track: Track) -> int:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"📥 Enqueue request for chat {chat_id}: {track[1]}")
        
        async with self._lock:
            # Always add the track to the queue first
            await self.queue.add(chat_id, track)
            logger.info(f"   Added to queue for chat {chat_id}")
            
            fq = self._ensure_flag_queue(chat_id)
            await fq.put(False)
            
            # Check if there's currently playing music in this chat
            cur = self.queue.current(chat_id)
            logger.info(f"   Current playing: {cur is not None}")
            
            if not cur:
                # If no music is currently playing, play the newly added track directly
                logger.info(f"   No music playing, starting playback...")
                nxt = await self.queue.next(chat_id)
                if nxt:
                    # consume flag queued above
                    try:
                        _ = fq.get_nowait()
                    except Exception:
                        pass
                    logger.info(f"   Calling _play with: {nxt[1]}")
                    await self._play(chat_id, nxt, is_video=False)
                # Return 0 to indicate it's playing immediately (as first in queue)
                return 0
        
        # If there was music playing, return the number of pending items in queue
        return len(self.queue.pending(chat_id))

    async def play_direct(self, chat_id: int, track: Track) -> int:
        """Play a track directly without adding to queue, regardless of current state"""
        async with self._lock:
            await self._play(chat_id, track)
        return 0  # Return 0 to indicate direct play


    async def _play(self, chat_id: int, track: Track, is_video: bool = False) -> None:
        src = track[0]
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Attempting to play: {track[1]} | Source: {src[:80] if src else 'None'}")
        
        # Only handle audio playback
        try:
            stream = MediaStream(
                media_path=src,
                audio_parameters=AudioQuality.HIGH,
            )
            await self.tgcalls.play(chat_id, stream)
            logger.info(f"✅ Successfully started playback for chat {chat_id}")
        except Exception as e:
            logger.error(f"❌ Failed to play: {e.__class__.__name__}: {e}")
            logger.error(f"Source URL: {src}")
            raise
        
        cb = getattr(self, "on_track_start", None)
        if cb:
            try:
                await cb(chat_id, track)
            except Exception:
                pass

    async def skip(self, chat_id: int) -> Optional[Track]:
        async with self._lock:
            nxt = await self.queue.next(chat_id)
            if nxt:
                fq = self._ensure_flag_queue(chat_id)
                is_video = False
                try:
                    is_video = fq.get_nowait()
                except Exception:
                    is_video = False
                await self._play(chat_id, nxt, is_video=is_video)
                return nxt
            try:
                await self.tgcalls.leave_call(chat_id)
            except Exception:
                pass
            return None

    async def stop(self, chat_id: int) -> None:
        async with self._lock:
            self.queue.clear(chat_id)
            try:
                await self.tgcalls.leave_call(chat_id)
            except Exception:
                pass

    async def pause(self, chat_id: int) -> None:
        try:
            await self.tgcalls.pause(chat_id)
        except Exception:
            pass

    async def resume(self, chat_id: int) -> None:
        try:
            await self.tgcalls.resume(chat_id)
        except Exception:
            pass

    async def replay(self, chat_id: int) -> None:
        cur = self.queue.current(chat_id)
        if cur:
            fq = self._ensure_flag_queue(chat_id)
            is_video = False
            try:
                is_video = fq.get_nowait()
            except Exception:
                is_video = False
            await self._play(chat_id, cur, is_video=is_video)

    def current(self, chat_id: int) -> Optional[Track]:
        return self.queue.current(chat_id)

    def pending(self, chat_id: int) -> int:
        return len(self.queue.pending(chat_id))
