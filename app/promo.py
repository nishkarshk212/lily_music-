import asyncio
import os
from typing import Dict, List, Optional
from pyrogram import Client
try:
    from .config import PROMO_ENABLED, PROMO_INTERVAL, PROMO_MESSAGES, PROMO_CHANNEL
except Exception:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from app.config import PROMO_ENABLED, PROMO_INTERVAL, PROMO_MESSAGES, PROMO_CHANNEL

class PromoManager:
    def __init__(self) -> None:
        self._tasks: Dict[int, asyncio.Task] = {}
        self._index: Dict[int, int] = {}
        self._channel = PROMO_CHANNEL or ""
        default_msg = (
            "𝐇𝐞𝐥𝐥𝐨 𝐅𝐫𝐢𝐞𝐧𝐝𝐬🌷🤌\n"
            "𝐀𝐫𝐞 𝐘𝐨𝐮 𝐋𝐨𝐨𝐤𝐢𝐧𝐠 𝐅𝐨𝐫 𝗧𝗛𝗘 𝗕𝗘𝗦𝗧 𝐂𝐇𝐀𝐓𝐈𝐍𝐆 𝗚𝗥𝗢𝗨𝗣..??👀\n"
            "𝐇𝐞𝐫𝐞 𝐘𝐨𝐮 𝐂𝐚𝐧 𝐌𝐞𝐞𝐭 𝐍𝐞𝐰 𝐅𝐫𝐢𝐞𝐧𝐝𝐬...🌚✨👃\n\n"
            "𝐀𝐬 𝐰𝐞𝐥𝐥 𝐚𝐬 :-\n"
            "✨ 𝟐𝟒 𝐱 𝟕 𝐀ᴄᴛɪᴠᴇ 𝐂ʜᴀᴛᴛɪɴɢ\n"
            "🧸 𝐌ᴀᴋᴇ 𝐍ᴇᴡ 𝐅ʀɪᴇɴᴅs\n"
            "❄️ 𝐄ɴᴊᴏʏ 𝐕𝐂 (𝐕ᴏɪᴄᴇ 𝐂ʜᴀᴛ+𝐒ᴏɴɢ)\n"
            "🎀 𝐑ᴇsᴘᴇᴄᴛғᴜʟʟ 𝐄ɴᴠɪʀᴏɴᴍᴇɴᴛ 𝐅ᴏʀ 𝐄ᴠᴇʀʏᴏɴ𝐄\n\n"
            "💌 𝐀ʙᴜsᴇ/ 𝐍ᴏ 👠 𝐂ᴏɴᴛᴇɴᴛ\n\n"
            "ʜᴜʀʀʏ ᴜᴘ ᴛᴏ ᴍᴀᴋᴇ ɴᴇᴡ ғʀɪᴇɴᴅs\n"
            "    🌷 Jᴏɪɴ ʀɪɢʜᴛ ɴᴏᴡ\n"
            f"{self._channel}"
        )
        self._messages: List[str] = [m.strip() for m in (PROMO_MESSAGES or "").split("|") if m.strip()] or [default_msg]
        self._interval: int = PROMO_INTERVAL
        self._enabled: bool = PROMO_ENABLED

    async def _loop(self, client: Client, chat_id: int) -> None:
        while True:
            await asyncio.sleep(self._interval)
            if not self._enabled:
                continue
            msgs = self._messages
            if not msgs:
                continue
            i = self._index.get(chat_id, 0) % len(msgs)
            text = msgs[i]
            ch = self._channel or ""
            if ch and ch not in text:
                if ch.startswith("@"):
                    text = f"{text}\n\n{ch}"
                else:
                    text = f"{text}\n\n{ch}"
            self._index[chat_id] = i + 1
            try:
                await client.send_message(chat_id, text)
            except Exception:
                pass

    def start(self, client: Client, chat_id: int) -> None:
        if chat_id in self._tasks:
            return
        self._tasks[chat_id] = asyncio.create_task(self._loop(client, chat_id))

    def stop(self, chat_id: int) -> None:
        t = self._tasks.pop(chat_id, None)
        if t:
            try:
                t.cancel()
            except Exception:
                pass

    async def send_once(self, client: Client, chat_id: int) -> None:
        msgs = self._messages
        if not msgs:
            return
        i = self._index.get(chat_id, 0) % len(msgs)
        text = msgs[i]
        ch = self._channel or ""
        if ch and ch not in text:
            if ch.startswith("@"):
                text = f"{text}\n\n{ch}"
            else:
                text = f"{text}\n\n{ch}"
        self._index[chat_id] = i + 1
        try:
            await client.send_message(chat_id, text)
        except Exception:
            pass
