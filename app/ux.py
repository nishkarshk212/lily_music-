import asyncio
from typing import Dict, Optional
from .config import STICKER_RANDOM_ENABLED

class PandaUltraUX:
    def __init__(self, sticker_pool=None) -> None:
        self.active_stickers: Dict[int, object] = {}
        self.active_text: Dict[int, object] = {}
        self.pool = sticker_pool

    async def start_stage(self, client, message, sticker_id: str, text: Optional[str] = None, prefer_animated: bool = False):
        await self.cleanup(message)
        sticker = None
        try:
            sid = sticker_id
            if STICKER_RANDOM_ENABLED and self.pool:
                rid = await self.pool.random_id(client, animated_only=prefer_animated)
                sid = rid or sticker_id
            if sid:
                sticker = await message.reply_sticker(sid)
        except Exception:
            sticker = None
        status = None
        if text:
            status = await message.reply_text(text)
        elif sticker is None:
            status = await message.reply_text("Searching…")
        self.active_stickers[message.id] = sticker
        if status:
            self.active_text[message.id] = status

    async def update_text(self, message, text: str):
        msg = self.active_text.get(message.id)
        if msg:
            try:
                await msg.edit_text(text)
            except Exception:
                pass

    async def switch_sticker(self, client, message, sticker_id: str, new_text: Optional[str] = None, prefer_animated: bool = False):
        old_sticker = self.active_stickers.get(message.id)
        new_sticker = None
        try:
            sid = sticker_id
            if STICKER_RANDOM_ENABLED and self.pool:
                rid = await self.pool.random_id(client, animated_only=prefer_animated)
                sid = rid or sticker_id
            if sid:
                new_sticker = await message.reply_sticker(sid)
        except Exception:
            new_sticker = None
        if new_sticker:
            if old_sticker:
                try:
                    await old_sticker.delete()
                except Exception:
                    pass
            self.active_stickers[message.id] = new_sticker
        else:
            # If we couldn't create a new sticker, keep the existing one
            if old_sticker:
                self.active_stickers[message.id] = old_sticker
            else:
                self.active_stickers[message.id] = None
        if new_text:
            try:
                status = await message.reply_text(new_text)
                self.active_text[message.id] = status
            except Exception:
                pass

    async def cleanup(self, message):
        sticker = self.active_stickers.pop(message.id, None)
        text = self.active_text.pop(message.id, None)
        if sticker:
            try:
                await sticker.delete()
            except Exception:
                pass
        if text:
            try:
                await text.delete()
            except Exception:
                pass
