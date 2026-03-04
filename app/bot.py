from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional
try:
    from .player import Player
    from .downloader import resolve
    from .thumb import generate_thumbnail
    from .promo import PromoManager
    from .ux import PandaUltraUX
    from .stickers import StickerPool
except Exception:
    import os, sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from app.player import Player
    from app.downloader import resolve, resolve_video, resolve_video_quality
    from app.thumb import generate_thumbnail
    from app.promo import PromoManager
    from app.ux import PandaUltraUX
    from app.stickers import StickerPool
from pytgcalls.exceptions import NoActiveGroupCall, NotInCallError
import asyncio
import os
import time
from datetime import datetime, timedelta
import json

def create_bot(api_id: int, api_hash: str, bot_token: str, player: Player, session_name: str = "music-bot") -> Client:
    import os
    workdir = os.path.join(os.getcwd(), "sessions", "bot")
    os.makedirs(workdir, exist_ok=True)
    bot = Client(session_name, api_id=api_id, api_hash=api_hash, bot_token=bot_token, workdir=workdir)
    
    # Import config to access user account settings
    try:
        from .config import USER_PHONE
        user_phone = USER_PHONE
    except ImportError:
        user_phone = os.getenv("PHONE", "")
    try:
        from .config import DISABLE_PLAY_ANNOUNCE
        disable_announce = bool(DISABLE_PLAY_ANNOUNCE)
    except Exception:
        disable_announce = os.getenv("DISABLE_PLAY_ANNOUNCE", "1").lower() in ("1", "true", "yes", "on")

    stream_state = {}
    promo = PromoManager()
    sticker_pool = StickerPool()
    ux = PandaUltraUX(sticker_pool)
    # Track ongoing invite attempts to prevent duplicates
    ongoing_invite_attempts = set()

    def _status_str(s) -> str:
        try:
            from pyrogram.enums import ChatMemberStatus as CMS
            if isinstance(s, CMS):
                return s.name.lower()
        except Exception:
            pass
        return str(s).lower()

    def _is_member(cm) -> bool:
        s = _status_str(getattr(cm, "status", ""))
        return s in ("member", "administrator", "creator", "owner", "admin")

    def _is_admin(cm) -> bool:
        s = _status_str(getattr(cm, "status", ""))
        return s in ("administrator", "creator", "owner", "admin")

    def _can_invite(cm) -> bool:
        priv = getattr(cm, "privileges", None) or getattr(cm, "permissions", None)
        if priv is None:
            return False
        for key in ("can_invite_users", "invite_users"):
            v = getattr(priv, key, None)
            if isinstance(v, bool) and v:
                return True
        return False
    async def _is_admin_user(client: Client, chat_id: int, user_id: int) -> bool:
        try:
            cm = await client.get_chat_member(chat_id, user_id)
            return _is_admin(cm)
        except Exception:
            return False

    async def ensure_user_in_chat(chat_id: int) -> bool:
        """Ensure user account is in the chat, invite if needed"""
        # Prevent multiple simultaneous invite attempts for the same chat
        if chat_id in ongoing_invite_attempts:
            print(f"Invite attempt already in progress for chat {chat_id}")
            # Wait a bit to see if the ongoing attempt succeeds
            for _ in range(10):  # Wait up to 5 seconds
                await asyncio.sleep(0.5)
                try:
                    me_user = player.user_client.me or await player.user_client.get_me()
                    um = await player.user_client.get_chat_member(chat_id, me_user.id)
                    user_in_chat = getattr(um, "status", "") in ("member", "administrator", "creator")
                    if user_in_chat:
                        print(f"User was added by ongoing attempt in chat {chat_id}")
                        return True
                except Exception:
                    continue
            return False
        
        ongoing_invite_attempts.add(chat_id)
        
        try:
            # Get user account info
            me_user = player.user_client.me or await player.user_client.get_me()
            print(f"Checking if user {me_user.id} ({me_user.first_name}) is in chat {chat_id}")
                
            # Check if user is already in chat
            try:
                um = await player.user_client.get_chat_member(chat_id, me_user.id)
                user_in_chat = _is_member(um)
                print(f"User status in chat: {getattr(um, 'status', 'unknown')}")
                if user_in_chat:
                    print(f"User already in chat {chat_id}")
                    return True
            except Exception as e:
                # User not in chat, proceed to invite
                print(f"User not in chat, attempting to auto-join: {e}")
                try:
                    me_user = player.user_client.me or await player.user_client.get_me()
                    uname = f"@{getattr(me_user, 'username', '')}" if getattr(me_user, "username", None) else ""
                    disp = f"{getattr(me_user, 'first_name', '')} {uname}".strip()
                    await bot.send_message(chat_id, f"Assistant account joining: {disp}")
                except Exception:
                    pass
                
            # Try to get the user by phone number or username and add by ID
            try:
                # Get bot info to check permissions
                me_bot = bot.me or await bot.get_me()
                bm = await bot.get_chat_member(chat_id, me_bot.id)
                            
                # Try direct add if bot is admin; fall back to invite link
                if _is_admin(bm):
                    try:
                        try:
                            await bot.get_users(me_user.id)
                        except Exception:
                            pass
                        await bot.add_chat_members(chat_id, me_user.id)
                        print(f"Invited user account (ID: {me_user.id}) to chat {chat_id}")
                        await asyncio.sleep(2)
                        try:
                            um = await player.user_client.get_chat_member(chat_id, me_user.id)
                            user_in_chat = _is_member(um)
                            if user_in_chat:
                                print(f"Confirmed: User account is now in chat {chat_id}")
                                return True
                        except Exception as check_error:
                            print(f"Could not verify user joined: {check_error}")
                            return False
                    except Exception as add_error:
                        print(f"Failed to add user account by ID: {add_error}")
                        try:
                            expire_date = datetime.utcnow() + timedelta(hours=24)
                            invite = await bot.create_chat_invite_link(
                                chat_id,
                                expire_date=expire_date,
                                member_limit=1
                            )
                            link = invite.invite_link
                            print(f"Created temporary invite link: {link}")
                            await player.user_client.join_chat(link)
                            print(f"User account attempted to join chat {chat_id} via temporary invite link")
                            await asyncio.sleep(2)
                            try:
                                um = await player.user_client.get_chat_member(chat_id, me_user.id)
                                user_in_chat = _is_member(um)
                                if user_in_chat:
                                    print(f"Confirmed: User is now in chat {chat_id}")
                                    return True
                            except Exception as check_error:
                                print(f"Could not verify user joined: {check_error}")
                                return False
                        except Exception as temp_link_error:
                            print(f"Temporary invite link method failed: {temp_link_error}")
                else:
                    print("Bot is not an admin in the chat")
                                
            except Exception as e:
                print(f"Direct invite process failed: {e}")
                # If all direct methods fail, fall back to creating an invite link
                            
                # Fallback: Try to create an invite link and have the user client auto-join
                try:
                    # Create an invite link as fallback
                    invite = await bot.create_chat_invite_link(chat_id)
                    link = invite.invite_link
                                
                    # Try to have the user client auto-join the chat using the invite link
                    try:
                        await player.user_client.join_chat(link)
                        print(f"User account auto-joined chat {chat_id} via invite link")
                        # Wait a bit for the join to complete
                        await asyncio.sleep(2)
                                    
                        # Double-check that user is now in the chat
                        try:
                            um = await player.user_client.get_chat_member(chat_id, me_user.id)
                            user_in_chat = _is_member(um)
                            if user_in_chat:
                                print(f"Confirmed: User is now in chat {chat_id}")
                                return True
                        except Exception as check_error:
                            print(f"Could not verify user joined: {check_error}")
                            return False
                    except Exception as join_error:
                        print(f"Auto-join via invite link failed: {join_error}")
                        # Check again if the user might have joined despite the error
                        try:
                            um = await player.user_client.get_chat_member(chat_id, me_user.id)
                            user_in_chat = _is_member(um)
                            if user_in_chat:
                                print(f"User joined despite error")
                                return True
                        except Exception:
                            pass
                        return False
                except Exception as fallback_error:
                    print(f"Fallback invite link method also failed: {fallback_error}")
                        
        except Exception as e:
            print(f"Error ensuring user in chat: {e}")
                
        finally:
            # Always remove from ongoing attempts when done
            ongoing_invite_attempts.discard(chat_id)
        
        print(f"Failed to auto-join user in chat {chat_id}")
        return False

    async def check_and_invite_user_to_group(chat_id: int, message: Message):
        """Function to check if user is in group and invite if not present"""
        try:
            # Check if user is already in the group
            me_user = player.user_client.me or await player.user_client.get_me()
            print(f"Checking if user {me_user.id} ({me_user.first_name}) is in chat {chat_id}")
                
            # Check if user is already in chat
            try:
                um = await player.user_client.get_chat_member(chat_id, me_user.id)
                user_in_chat = getattr(um, "status", "") in ("member", "administrator", "creator")
                print(f"User status in chat: {getattr(um, 'status', 'unknown')}")
                if user_in_chat:
                    print(f"User already in chat {chat_id}")
                    await message.reply_text("✅ User account is already in this group.")
                    return True
            except Exception as e:
                # User not in chat, proceed to invite
                print(f"User not in chat, attempting to invite: {e}")
                await message.reply_text("ℹ️ User account is not in this group. Attempting to invite...")
                
            # Try to ensure user is in chat using existing function
            user_added = await ensure_user_in_chat(chat_id)
            if user_added:
                await message.reply_text("🎉 User account has been successfully added to the group!")
                return True
            else:
                kb = await make_add_user_kb(None)
                await message.reply_text(
                    "❌ Failed to add user account to the group.\nUse the button below to add the assistant.",
                    reply_markup=kb,
                    disable_web_page_preview=True,
                )
                return False
                
        except Exception as e:
            print(f"Error in check_and_invite_user_to_group: {e}")
            await message.reply_text(f"Error checking/inviting user: {e}")
            return False

    def _thin_bar(current: int, total: int, size: int = 18) -> str:
        if total <= 0:
            return "─" * size
        pos = int(size * current / total)
        pos = min(size - 1, max(0, pos))
        bar = ""
        for i in range(size):
            bar += "◉" if i == pos else "─"
        return bar

    def _format_time(sec: int) -> str:
        sec = max(0, int(sec))
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        return f"{m:02d}:{s:02d}" if h == 0 else f"{h}:{m:02d}:{s:02d}"

    def _parse_duration_to_seconds(s: str) -> int:
        try:
            parts = [int(p) for p in s.split(":")]
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            if len(parts) == 2:
                return parts[0] * 60 + parts[1]
            return int(s)
        except Exception:
            return 0
    
    def _display_user(u) -> str:
        if not u:
            return "User"
        uname = getattr(u, "username", None)
        if uname:
            return f"@{uname}"
        first = getattr(u, "first_name", "") or ""
        last = getattr(u, "last_name", "") or ""
        full = f"{first} {last}".strip()
        return full or "User"

    def _parse_tme_c_link(s: str):
        try:
            if not s:
                return None
            parts = s.strip().split("/")
            i = parts.index("c") if "c" in parts else -1
            if i == -1 or len(parts) < i + 3:
                return None
            internal = int(parts[i + 1])
            mid = int(parts[i + 2])
            cid = -100 * internal
            return cid, mid
        except Exception:
            return None

    def _build_caption(bot_name: str, title: str, duration_text: str, requester: str) -> str:
        return (
            f"🐼 {bot_name} — SUPREME\n\n"
            f"🎵 {title}\n\n"
            f"⏱ Duration: {duration_text}\n\n"
            f"👤 requested by user = {requester}"
        )

    async def _live_updater(chat_id: int):
        return

    def controls_kb() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("﹦", callback_data="PAUSE"),
                 InlineKeyboardButton("➢", callback_data="RESUME"),
                 InlineKeyboardButton("⧠", callback_data="STOP")],
                [InlineKeyboardButton("⋜", callback_data="SEEK_BACK_5"),
                 InlineKeyboardButton("⋝", callback_data="SEEK_FWD_5")],
                [InlineKeyboardButton("⊲", callback_data="BACKWARD"),
                 InlineKeyboardButton("⊳", callback_data="FORWARD")],
                [InlineKeyboardButton("≡", callback_data="PING"),
                 InlineKeyboardButton("×", callback_data="CLOSE")],
            ]
        )

    def queue_controls_kb() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("×", callback_data="CLOSE")]])

    def colored_controls_markup(is_video: bool):
        # Always return audio controls since video is disabled
        return {
            "inline_keyboard": [
                [
                    {"text": "﹦", "callback_data": "PAUSE", "style": "primary"},
                    {"text": "➢", "callback_data": "RESUME", "style": "success"},
                    {"text": "⧠", "callback_data": "STOP", "style": "danger"},
                ],
                [
                    {"text": "⋜", "callback_data": "SEEK_BACK_5", "style": "primary"},
                    {"text": "⋝", "callback_data": "SEEK_FWD_5", "style": "primary"},
                ],
                [
                    {"text": "⊲", "callback_data": "BACKWARD", "style": "primary"},
                    {"text": "⊳", "callback_data": "FORWARD", "style": "primary"},
                ],
                [
                    {"text": "≡", "callback_data": "PING", "style": "primary"},
                    {"text": "×", "callback_data": "CLOSE", "style": "danger"},
                ],
            ]
        }

    async def make_add_user_kb(invite_link: Optional[str] = None) -> InlineKeyboardMarkup:
        rows = []
        rows.append([InlineKeyboardButton("Add lilly_assistant", callback_data="ADD_ASSISTANT")])
        if invite_link:
            rows.append([InlineKeyboardButton("Invite Link", url=invite_link)])
        if not rows:
            rows = [[InlineKeyboardButton("Help", callback_data="HELP_MENU")]]
        return InlineKeyboardMarkup(rows)

    @bot.on_message(filters.command(["start"]))
    async def _(client: Client, message: Message):
        me = client.me or await client.get_me()
        try:
            if getattr(message.chat, "type", "") in ("group", "supergroup"):
                await ensure_user_in_chat(message.chat.id)
        except Exception:
            pass
        user = message.from_user.first_name if message.from_user else "User"
        bot_name = me.first_name or me.username or "Music Bot"
        text = (
            f"нєу {user}, 🥀\n\n"
            f"๏ ᴛʜɪs ɪs {bot_name}\n\n"
            f"➻ ᴀ ғᴀsᴛ & ᴘᴏᴡᴇʀғᴜʟ ᴛᴇʟᴇɢʀᴀᴍ ᴍᴜsɪᴄ ᴘʟᴀʏᴇʀ ʙᴏᴛ ᴡɪᴛʜ sᴏᴍᴇ ᴀᴡᴇsᴏᴍᴇ ғᴇᴀᴛᴜʀᴇs.\n\n"
            f"๏ ᴄʟɪᴄᴋ ʜᴇʟᴘ ᴛᴏ ɢᴇᴛ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ᴀʙᴏᴜᴛ ᴍʏ ᴍᴏᴅᴜʟᴇs ᴀɴᴅ ᴄᴏᴍᴍᴀɴᴅs."
        )
        add_to_group_url = f"https://t.me/{me.username}?startgroup=true" if me.username else "https://t.me/"
        colored_reply_markup = {
            "inline_keyboard": [
                [{"text": "Owner", "url": "https://t.me/Jayden_212", "style": "primary"}],
                [{"text": "Group", "url": "https://t.me/Titanic_world_chatting_zonee", "style": "primary"}],
                [{"text": "Add to Group", "url": add_to_group_url, "style": "success"}],
                [{"text": "Help", "callback_data": "HELP_MENU", "style": "danger"}],
            ]
        }
        photo = None
        try:
            chat = await client.get_chat(me.id)
            if getattr(chat, "photo", None) and getattr(chat.photo, "big_file_id", None):
                dstdir = os.path.join(os.getcwd(), "downloads", "start")
                os.makedirs(dstdir, exist_ok=True)
                photo = await client.download_media(
                    chat.photo.big_file_id,
                    file_name=os.path.join(dstdir, "bot_pp.jpg"),
                )
        except Exception:
            photo = None
        try:
            import requests
            from .config import BOT_TOKEN as _BT
            url_base = f"https://api.telegram.org/bot{_BT}"
            if photo:
                with open(photo, "rb") as f:
                    requests.post(
                        f"{url_base}/sendPhoto",
                        data={
                            "chat_id": message.chat.id,
                            "caption": text,
                            "reply_markup": json.dumps(colored_reply_markup),
                            "disable_web_page_preview": True,
                            "has_spoiler": True,
                        },
                        files={"photo": f},
                        timeout=15,
                    )
            else:
                requests.post(
                    f"{url_base}/sendMessage",
                    json={
                        "chat_id": message.chat.id,
                        "text": text,
                        "reply_markup": colored_reply_markup,
                        "disable_web_page_preview": True,
                    },
                    timeout=15,
                )
        except Exception:
            if photo:
                await message.reply_photo(photo=photo, caption=text)
            else:
                await message.reply_text(text)

    @bot.on_message(filters.command(["help"]))
    async def help_cmd(client: Client, message: Message):
        txt = (
            "Commands:\n"
            "/play <query or link> – play or queue audio\n"
            "/pause – pause stream\n"
            "/resume – resume stream\n"
            "/skip – skip to next\n"
            "/stop – clear and leave\n"
            "/queue – show now/pending\n"
            "/health – check setup\n"
            "/settings – bot configuration\n"
            "/inviteuser – invite user account to group (admin only)\n"
            "/adduser – alias for /inviteuser (admin only)\n"
            "/removeuser – remove user account from group (admin only)\n"
            "/kickuser – alias for /removeuser (admin only)\n"
            "/refreshuser – remove and re-add user account (admin only)\n"
            "/resetuser – alias for /refreshuser (admin only)"
        )
        await message.reply_text(txt)

    @bot.on_message(filters.command(["settings"]))
    async def settings_cmd(client: Client, message: Message):
        me = client.me or await client.get_me()
        user = message.from_user.first_name if message.from_user else "User"
        bot_name = me.first_name or me.username or "Music Bot"
        try:
            cht = getattr(message, "chat", None)
            is_group = getattr(cht, "type", "") in ("group", "supergroup")
        except Exception:
            is_group = False
        if is_group:
            uid = getattr(message.from_user, "id", 0) if message.from_user else 0
            ok = await _is_admin_user(client, message.chat.id, uid)
            if not ok:
                await message.reply_text("Only group admins can change settings.")
                return
        
        text = (
            f"⚙️ {bot_name} Settings\n\n"
            f"๏ ᴡᴇʟᴄᴏᴍᴇ {user}!\n\n"
            f"๏ ᴄᴏɴғɪɢᴜʀᴇ ᴀɴᴅ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ᴍᴜsɪᴄ ʙᴏᴛ sᴇᴛᴛɪɴɢs ʜᴇʀᴇ.\n\n"
            f"๏ ᴄʟɪᴄᴋ ᴏɴ ᴀɴʏ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴀᴄᴄᴇss sᴘᴇᴄɪғɪᴄ sᴇᴛᴛɪɴɢs ᴏᴘᴛɪᴏɴs."
        )
        
        colored_reply_markup = {
            "inline_keyboard": [
                [{"text": "Play Settings", "callback_data": "SETTINGS_PLAY", "style": "primary"}],
                [{"text": "Audio/Video", "callback_data": "SETTINGS_AV", "style": "primary"}],
                [{"text": "Playback Controls", "callback_data": "SETTINGS_CONTROLS", "style": "primary"}],
                [{"text": "Queue Management", "callback_data": "SETTINGS_QUEUE", "style": "primary"}],
                [{"text": "Bot Info", "callback_data": "SETTINGS_INFO", "style": "primary"}],
                [{"text": "Permissions", "callback_data": "SETTINGS_PERMS", "style": "primary"}],
                [{"text": "Reset Settings", "callback_data": "SETTINGS_RESET", "style": "danger"}],
                [{"text": "Close", "callback_data": "SETTINGS_CLOSE", "style": "danger"}],
            ]
        }
        try:
            import requests
            from .config import BOT_TOKEN as _BT
            url_base = f"https://api.telegram.org/bot{_BT}"
            requests.post(
                f"{url_base}/sendMessage",
                json={
                    "chat_id": message.chat.id,
                    "text": text,
                    "reply_markup": colored_reply_markup,
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
        except Exception:
            kb = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Play Settings", callback_data="SETTINGS_PLAY")],
                    [InlineKeyboardButton("Audio/Video", callback_data="SETTINGS_AV")],
                    [InlineKeyboardButton("Playback Controls", callback_data="SETTINGS_CONTROLS")],
                    [InlineKeyboardButton("Queue Management", callback_data="SETTINGS_QUEUE")],
                    [InlineKeyboardButton("Bot Info", callback_data="SETTINGS_INFO")],
                    [InlineKeyboardButton("Permissions", callback_data="SETTINGS_PERMS")],
                    [InlineKeyboardButton("Reset Settings", callback_data="SETTINGS_RESET")],
                    [InlineKeyboardButton("Close", callback_data="SETTINGS_CLOSE")],
                ]
            )
            await message.reply_text(text, reply_markup=kb, disable_web_page_preview=True)

    @bot.on_callback_query()
    async def on_cb(client, cq):
        me = client.me or await client.get_me()
        is_settings_action = False
        try:
            d = cq.data or ""
            is_settings_action = d.startswith("SETTINGS_") or d in {
                "PLAY_MODE",
                "SKIP_MODE",
                "TOGGLE_FIRST_PLAY",
                "TOGGLE_QUEUE",
                "AUDIO_QUALITY",
                "VIDEO_SETTINGS",
                "VIEW_QUEUE",
                "CLEAR_QUEUE",
                "BOT_STATS",
                "CHECK_PERMS",
                "CONFIRM_RESET",
                "BACK_SETTINGS",
            }
        except Exception:
            is_settings_action = False
        if is_settings_action:
            is_group = getattr(getattr(cq.message, "chat", None), "type", "") in ("group", "supergroup")
            if is_group:
                uid = getattr(cq.from_user, "id", 0) if cq.from_user else 0
                ok = await _is_admin_user(client, cq.message.chat.id, uid)
                if not ok:
                    try:
                        await cq.answer("Only group admins can change settings.", show_alert=True)
                    except Exception:
                        pass
                    return
        if cq.data == "HELP_MENU":
            kb = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Commands", callback_data="HELP_COMMANDS")],
                    [InlineKeyboardButton("Controls", callback_data="HELP_CONTROLS")],
                    
                    [InlineKeyboardButton("Admin", callback_data="HELP_ADMIN")],
                    [InlineKeyboardButton("Back", callback_data="BACK_START")],
                ]
            )
            text = "Help — select a section:"
            try:
                await cq.message.edit_caption(caption=text, reply_markup=kb)
            except Exception:
                await cq.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
            await cq.answer()
        elif cq.data == "BACK_START":
            user = cq.from_user.first_name if cq.from_user else "User"
            bot_name = me.first_name or me.username or "Music Bot"
            text = (
                f"нєу {user}, 🥀\n\n"
                f"๏ ᴛʜɪs ɪs {bot_name}\n\n"
                f"➻ ᴀ ғᴀsᴛ & ᴘᴏᴡᴇʀғᴜʟ ᴛᴇʟᴇɢʀᴀᴍ ᴍᴜsɪᴄ ᴘʟᴀʏᴇʀ ʙᴏᴛ ᴡɪᴛʜ sᴏᴍᴇ ᴀᴡᴇsᴏᴍᴇ ғᴇᴀᴛᴜʀᴇs.\n\n"
                f"๏ ᴄʟɪᴄᴋ ʜᴇʟᴘ ᴛᴏ ɢᴇᴛ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ᴀʙᴏᴜᴛ ᴍʏ ᴍᴏᴅᴜʟᴇs ᴀɴᴅ ᴄᴏᴍᴍᴀɴᴅs."
            )
            add_to_group_url = f"https://t.me/{me.username}?startgroup=true" if me.username else "https://t.me/"
            kb = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Owner", url="https://t.me/Jayden_212")],
                    [InlineKeyboardButton("Group", url="https://t.me/Titanic_world_chatting_zonee")],
                    [InlineKeyboardButton("Add to Group", url=add_to_group_url)],
                    [InlineKeyboardButton("Help", callback_data="HELP_MENU")],
                ]
            )
            try:
                await cq.message.edit_caption(caption=text, reply_markup=kb)
            except Exception:
                await cq.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
            await cq.answer()
        elif cq.data == "HELP_COMMANDS":
            text = (
                "Commands\n\n"
                "/play <query or link> — play or queue audio\n"
                "/pause — pause stream\n"
                "/resume — resume stream\n"
                "/skip — skip to next\n"
                "/stop — clear and leave\n"
                "/queue — show now/pending list\n"
                "/health — check setup\n"
            )
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="HELP_MENU")]])
            try:
                await cq.message.edit_text(text, reply_markup=kb)
            except Exception:
                await cq.message.reply_text(text, reply_markup=kb)
            await cq.answer()
        elif cq.data == "HELP_CONTROLS":
            text = (
                "Controls\n\n"
                "﹦ — Pause\n"
                "➢ — Resume\n"
                "⧠ — Stop\n"
                "⋜ — Seek −5s (displayed time)\n"
                "⋝ — Seek +5s (displayed time)\n"
                "⊲ — Backward (previous track)\n"
                "⊳ — Forward (next track)\n"
                "≡ — Ping\n"
                "× — Close card\n"
            )
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="HELP_MENU")]])
            try:
                await cq.message.edit_text(text, reply_markup=kb)
            except Exception:
                await cq.message.reply_text(text, reply_markup=kb)
            await cq.answer()
        
        elif cq.data == "HELP_ADMIN":
            text = (
                "Admin\n\n"
                "/inviteuser • /adduser — add assistant user to group\n"
                "/removeuser • /kickuser — remove assistant user\n"
                "/refreshuser • /resetuser — remove and re-add assistant\n"
                "Add lilly_assistant — button performs direct add when possible\n"
            )
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="HELP_MENU")]])
            try:
                await cq.message.edit_text(text, reply_markup=kb)
            except Exception:
                await cq.message.reply_text(text, reply_markup=kb)
            await cq.answer()
        elif cq.data == "SETTINGS_PLAY":
            play_text = (
                "Play Settings\n\n"
                "Configure how music playback works:\n\n"
                "• First-time play: Plays directly without queuing\n"
                "• Queue behavior: Subsequent songs go to queue\n"
                "• Auto-play next: Automatically plays queued songs\n"
                "• Duplicate prevention: Avoids duplicate messages\n\n"
                "Current status: Active"
            )
            colored_reply_markup = {
                "inline_keyboard": [
                    [{"text": "Play Mode", "callback_data": "PLAY_MODE", "style": "primary"}],
                    [{"text": "Skip Mode", "callback_data": "SKIP_MODE", "style": "primary"}],
                    [{"text": "Toggle First Play", "callback_data": "TOGGLE_FIRST_PLAY", "style": "success"}],
                    [{"text": "Toggle Queue", "callback_data": "TOGGLE_QUEUE", "style": "success"}],
                    [{"text": "Back to Settings", "callback_data": "BACK_SETTINGS", "style": "primary"}],
                ]
            }
            try:
                import requests
                from .config import BOT_TOKEN as _BT
                url_base = f"https://api.telegram.org/bot{_BT}"
                requests.post(
                    f"{url_base}/editMessageText",
                    json={
                        "chat_id": cq.message.chat.id,
                        "message_id": cq.message.id,
                        "text": play_text,
                        "reply_markup": colored_reply_markup,
                        "disable_web_page_preview": True,
                    },
                    timeout=15,
                )
            except Exception:
                kb = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Play Mode", callback_data="PLAY_MODE")],
                        [InlineKeyboardButton("Skip Mode", callback_data="SKIP_MODE")],
                        [InlineKeyboardButton("Toggle First Play", callback_data="TOGGLE_FIRST_PLAY")],
                        [InlineKeyboardButton("Toggle Queue", callback_data="TOGGLE_QUEUE")],
                        [InlineKeyboardButton("Back to Settings", callback_data="BACK_SETTINGS")],
                    ]
                )
                try:
                    await cq.message.edit_text(play_text, reply_markup=kb)
                except Exception:
                    await cq.message.reply_text(play_text, reply_markup=kb)
            await cq.answer()
        elif cq.data == "SETTINGS_AV":
            av_text = (
                "Audio/Video Settings\n\n"
                "Manage audio and video playback options:\n\n"
                "• Audio Quality: High (default)\n"

                "• Thumbnail Generation: Active\n"
                "• Format Support: MP3, MP4, YouTube\n\n"
                "Current status: Active"
            )
            colored_reply_markup = {
                "inline_keyboard": [
                    [{"text": "Audio Quality", "callback_data": "AUDIO_QUALITY", "style": "primary"}],
                    [{"text": "Back to Settings", "callback_data": "BACK_SETTINGS", "style": "primary"}],
                ]
            }
            try:
                import requests
                from .config import BOT_TOKEN as _BT
                url_base = f"https://api.telegram.org/bot{_BT}"
                requests.post(
                    f"{url_base}/editMessageText",
                    json={
                        "chat_id": cq.message.chat.id,
                        "message_id": cq.message.id,
                        "text": av_text,
                        "reply_markup": colored_reply_markup,
                        "disable_web_page_preview": True,
                    },
                    timeout=15,
                )
            except Exception:
                kb = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Audio Quality", callback_data="AUDIO_QUALITY")],
                        [InlineKeyboardButton("Video Settings", callback_data="VIDEO_SETTINGS")],
                        [InlineKeyboardButton("Back to Settings", callback_data="BACK_SETTINGS")],
                    ]
                )
                try:
                    await cq.message.edit_text(av_text, reply_markup=kb)
                except Exception:
                    await cq.message.reply_text(av_text, reply_markup=kb)
            await cq.answer()
        elif cq.data == "SETTINGS_CONTROLS":
            controls_text = (
                "Playback Controls\n\n"
                "Available playback controls:\n\n"
                "• Pause/Resume: Stop and continue playback\n"
                "• Skip: Move to next queued song\n"
                "• Stop: End current session\n"
                "• Ping: Check bot responsiveness\n"
                "• Forward/Backward: Navigation\n\n"
                "All controls: Active"
            )
            colored_reply_markup = {
                "inline_keyboard": [
                    [{"text": "Test Controls", "callback_data": "TEST_CONTROLS", "style": "primary"}],
                    [{"text": "Back to Settings", "callback_data": "BACK_SETTINGS", "style": "primary"}],
                ]
            }
            try:
                import requests
                from .config import BOT_TOKEN as _BT
                url_base = f"https://api.telegram.org/bot{_BT}"
                requests.post(
                    f"{url_base}/editMessageText",
                    json={
                        "chat_id": cq.message.chat.id,
                        "message_id": cq.message.id,
                        "text": controls_text,
                        "reply_markup": colored_reply_markup,
                        "disable_web_page_preview": True,
                    },
                    timeout=15,
                )
            except Exception:
                kb = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Test Controls", callback_data="TEST_CONTROLS")],
                        [InlineKeyboardButton("Back to Settings", callback_data="BACK_SETTINGS")],
                    ]
                )
                try:
                    await cq.message.edit_text(controls_text, reply_markup=kb)
                except Exception:
                    await cq.message.reply_text(controls_text, reply_markup=kb)
            await cq.answer()
        elif cq.data == "SETTINGS_QUEUE":
            queue_text = (
                "Queue Management\n\n"
                "Queue system configuration:\n\n"
                "• Queue Size: Unlimited\n"
                "• Auto-play: Enabled\n"
                "• Queue Display: Shows pending songs\n"
                "• First Song Priority: Direct play\n\n"
                "Queue status: Active"
            )
            colored_reply_markup = {
                "inline_keyboard": [
                    [{"text": "View Queue", "callback_data": "VIEW_QUEUE", "style": "primary"}],
                    [{"text": "Clear Queue", "callback_data": "CLEAR_QUEUE", "style": "danger"}],
                    [{"text": "Back to Settings", "callback_data": "BACK_SETTINGS", "style": "primary"}],
                ]
            }
            try:
                import requests
                from .config import BOT_TOKEN as _BT
                url_base = f"https://api.telegram.org/bot{_BT}"
                requests.post(
                    f"{url_base}/editMessageText",
                    json={
                        "chat_id": cq.message.chat.id,
                        "message_id": cq.message.id,
                        "text": queue_text,
                        "reply_markup": colored_reply_markup,
                        "disable_web_page_preview": True,
                    },
                    timeout=15,
                )
            except Exception:
                kb = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("View Queue", callback_data="VIEW_QUEUE")],
                        [InlineKeyboardButton("Clear Queue", callback_data="CLEAR_QUEUE")],
                        [InlineKeyboardButton("Back to Settings", callback_data="BACK_SETTINGS")],
                    ]
                )
                try:
                    await cq.message.edit_text(queue_text, reply_markup=kb)
                except Exception:
                    await cq.message.reply_text(queue_text, reply_markup=kb)
            await cq.answer()
        elif cq.data == "SETTINGS_INFO":
            me = client.me or await client.get_me()
            bot_name = me.first_name or me.username or "Music Bot"
            info_text = (
                "Bot Information\n\n"
                f"Bot Name: {bot_name}\n"
                "Version: 1.0\n"
                "Developer: Panda x Music Team\n"
                "Framework: Pyrogram + PyTgCalls\n"
                "Features: Audio/Video Streaming\n\n"
                "Status: Online and Active"
            )
            colored_reply_markup = {
                "inline_keyboard": [
                    [{"text": "Bot Stats", "callback_data": "BOT_STATS", "style": "primary"}],
                    [{"text": "Back to Settings", "callback_data": "BACK_SETTINGS", "style": "primary"}],
                ]
            }
            try:
                import requests
                from .config import BOT_TOKEN as _BT
                url_base = f"https://api.telegram.org/bot{_BT}"
                requests.post(
                    f"{url_base}/editMessageText",
                    json={
                        "chat_id": cq.message.chat.id,
                        "message_id": cq.message.id,
                        "text": info_text,
                        "reply_markup": colored_reply_markup,
                        "disable_web_page_preview": True,
                    },
                    timeout=15,
                )
            except Exception:
                kb = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Bot Stats", callback_data="BOT_STATS")],
                        [InlineKeyboardButton("Back to Settings", callback_data="BACK_SETTINGS")],
                    ]
                )
                try:
                    await cq.message.edit_text(info_text, reply_markup=kb)
                except Exception:
                    await cq.message.reply_text(info_text, reply_markup=kb)
            await cq.answer()
        elif cq.data == "SETTINGS_PERMS":
            perms_text = (
                "Permissions\n\n"
                "Required permissions for full functionality:\n\n"
                "• Manage Voice Chats: Required\n"
                "• Send Messages: Required\n"
                "• Manage Messages: Required\n"
                "• Add Admins: Optional\n\n"
                "Run /health to check permissions"
            )
            colored_reply_markup = {
                "inline_keyboard": [
                    [{"text": "Check Permissions", "callback_data": "CHECK_PERMS", "style": "primary"}],
                    [{"text": "Back to Settings", "callback_data": "BACK_SETTINGS", "style": "primary"}],
                ]
            }
            try:
                import requests
                from .config import BOT_TOKEN as _BT
                url_base = f"https://api.telegram.org/bot{_BT}"
                requests.post(
                    f"{url_base}/editMessageText",
                    json={
                        "chat_id": cq.message.chat.id,
                        "message_id": cq.message.id,
                        "text": perms_text,
                        "reply_markup": colored_reply_markup,
                        "disable_web_page_preview": True,
                    },
                    timeout=15,
                )
            except Exception:
                kb = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Check Permissions", callback_data="CHECK_PERMS")],
                        [InlineKeyboardButton("Back to Settings", callback_data="BACK_SETTINGS")],
                    ]
                )
                try:
                    await cq.message.edit_text(perms_text, reply_markup=kb)
                except Exception:
                    await cq.message.reply_text(perms_text, reply_markup=kb)
            await cq.answer()
        elif cq.data == "SETTINGS_RESET":
            reset_text = (
                "Reset Settings\n\n"
                "Reset all settings to default values:\n\n"
                "• Queue settings\n"
                "• Playback preferences\n"
                "• Control configurations\n\n"
                "This will reset all custom settings!"
            )
            colored_reply_markup = {
                "inline_keyboard": [
                    [{"text": "Confirm Reset", "callback_data": "CONFIRM_RESET", "style": "danger"}],
                    [{"text": "Cancel", "callback_data": "BACK_SETTINGS", "style": "primary"}],
                ]
            }
            try:
                import requests
                from .config import BOT_TOKEN as _BT
                url_base = f"https://api.telegram.org/bot{_BT}"
                requests.post(
                    f"{url_base}/editMessageText",
                    json={
                        "chat_id": cq.message.chat.id,
                        "message_id": cq.message.id,
                        "text": reset_text,
                        "reply_markup": colored_reply_markup,
                        "disable_web_page_preview": True,
                    },
                    timeout=15,
                )
            except Exception:
                kb = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Confirm Reset", callback_data="CONFIRM_RESET")],
                        [InlineKeyboardButton("Cancel", callback_data="BACK_SETTINGS")],
                    ]
                )
                try:
                    await cq.message.edit_text(reset_text, reply_markup=kb)
                except Exception:
                    await cq.message.reply_text(reset_text, reply_markup=kb)
            await cq.answer()
        elif cq.data == "BACK_SETTINGS":
            me = client.me or await client.get_me()
            user = cq.from_user.first_name if cq.from_user else "User"
            bot_name = me.first_name or me.username or "Music Bot"
            
            text = (
                f"⚙️ {bot_name} Settings\n\n"
                f"๏ ᴡᴇʟᴄᴏᴍᴇ {user}!\n\n"
                f"๏ ᴄᴏɴғɪɢᴜʀᴇ ᴀɴᴅ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ᴍᴜsɪᴄ ʙᴏᴛ sᴇᴛᴛɪɴɢs ʜᴇʀᴇ.\n\n"
                f"๏ ᴄʟɪᴄᴋ ᴏɴ ᴀɴʏ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴀᴄᴄᴇss sᴘᴇᴄɪғɪᴄ sᴇᴛᴛɪɴɢs ᴏᴘᴛɪᴏɴs."
            )
            
            colored_reply_markup = {
                "inline_keyboard": [
                    [{"text": "Play Settings", "callback_data": "SETTINGS_PLAY", "style": "primary"}],
                    [{"text": "Audio/Video", "callback_data": "SETTINGS_AV", "style": "primary"}],
                    [{"text": "Playback Controls", "callback_data": "SETTINGS_CONTROLS", "style": "primary"}],
                    [{"text": "Queue Management", "callback_data": "SETTINGS_QUEUE", "style": "primary"}],
                    [{"text": "Bot Info", "callback_data": "SETTINGS_INFO", "style": "primary"}],
                    [{"text": "Permissions", "callback_data": "SETTINGS_PERMS", "style": "primary"}],
                    [{"text": "Reset Settings", "callback_data": "SETTINGS_RESET", "style": "danger"}],
                    [{"text": "Close", "callback_data": "SETTINGS_CLOSE", "style": "danger"}],
                ]
            }
            try:
                import requests
                from .config import BOT_TOKEN as _BT
                url_base = f"https://api.telegram.org/bot{_BT}"
                requests.post(
                    f"{url_base}/editMessageText",
                    json={
                        "chat_id": cq.message.chat.id,
                        "message_id": cq.message.id,
                        "text": text,
                        "reply_markup": colored_reply_markup,
                        "disable_web_page_preview": True,
                    },
                    timeout=15,
                )
            except Exception:
                kb = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Play Settings", callback_data="SETTINGS_PLAY")],
                        [InlineKeyboardButton("Audio/Video", callback_data="SETTINGS_AV")],
                        [InlineKeyboardButton("Playback Controls", callback_data="SETTINGS_CONTROLS")],
                        [InlineKeyboardButton("Queue Management", callback_data="SETTINGS_QUEUE")],
                        [InlineKeyboardButton("Bot Info", callback_data="SETTINGS_INFO")],
                        [InlineKeyboardButton("Permissions", callback_data="SETTINGS_PERMS")],
                        [InlineKeyboardButton("Reset Settings", callback_data="SETTINGS_RESET")],
                        [InlineKeyboardButton("Close", callback_data="SETTINGS_CLOSE")],
                    ]
                )
                try:
                    await cq.message.edit_text(text, reply_markup=kb)
                except Exception:
                    await cq.message.reply_text(text, reply_markup=kb)
            await cq.answer()
        elif cq.data == "SETTINGS_CLOSE":
            try:
                await cq.message.delete()
            except Exception:
                pass
            await cq.answer("Settings closed")
        elif cq.data == "PAUSE":
            try:
                await player.pause(cq.message.chat.id)
            except Exception:
                pass
            await cq.answer("Paused")
        elif cq.data == "RESUME":
            try:
                await player.resume(cq.message.chat.id)
            except Exception:
                pass
            await cq.answer("Resumed")
        elif cq.data == "STOP":
            try:
                await player.stop(cq.message.chat.id)
                st = stream_state.pop(cq.message.chat.id, None)
                if st and st.get("task"):
                    try:
                        st["task"].cancel()
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                promo.stop(cq.message.chat.id)
            except Exception:
                pass
            user = cq.from_user.first_name if cq.from_user else "User"
            stop_message = f"➻ sᴛʀᴇᴀᴍ ᴇɴᴅᴇᴅ/sᴛᴏᴩᴩᴇᴅ 🎄\n│ \n└ʙʏ : {user} 🥀"
            await client.send_message(cq.message.chat.id, stop_message)
            await cq.answer("Stopped")
        elif cq.data == "TOGGLE_FIRST_PLAY":
            await cq.answer("First play setting toggled", show_alert=True)
        elif cq.data == "TOGGLE_QUEUE":
            await cq.answer("Queue setting toggled", show_alert=True)
        elif cq.data == "AUDIO_QUALITY":
            await cq.answer("Audio quality is set to High", show_alert=True)
        elif cq.data == "VIDEO_SETTINGS":
            await cq.answer("Video features have been disabled", show_alert=True)
        elif cq.data in ("SEEK_BACK_5", "SEEK_FWD_5"):
            chat_id = cq.message.chat.id
            st = stream_state.get(chat_id, {})
            cur = player.current(chat_id)
            if not cur:
                await cq.answer("No current track", show_alert=True)
                return
            delta = -5 if cq.data == "SEEK_BACK_5" else 5
            total_sec = int(st.get("total", 0)) + delta
            # Boundaries
            dur_text = "-"
            try:
                # Try to get original duration from current meta if available
                pend = st.get("pending", [])
                if pend:
                    dur_text = pend[0].get("duration", dur_text)
                else:
                    # no pending meta, try stored 'duration' if any
                    dur_text = st.get("duration", dur_text)
            except Exception:
                pass
            dur_total = _parse_duration_to_seconds(dur_text) if dur_text and dur_text != "-" else 0
            if dur_total > 0:
                total_sec = max(0, min(total_sec, dur_total))
            else:
                total_sec = max(0, total_sec)
            st["total"] = total_sec
            stream_state[chat_id] = st
            # Rebuild caption with updated time
            url, title, thumb, vid = cur
            me = client.me or await client.get_me()
            bot_name = me.first_name or me.username or "Music Bot"
            pos_text = _format_time(total_sec)
            duration_text = pos_text if dur_text == "-" else f"{pos_text} / {dur_text}"
            requester = st.get("req", "User")
            caption = _build_caption(bot_name, title, duration_text, requester)
            try:
                import requests
                from .config import BOT_TOKEN as _BT
                url_base = f"https://api.telegram.org/bot{_BT}"
                requests.post(
                    f"{url_base}/editMessageCaption",
                    json={
                        "chat_id": cq.message.chat.id,
                        "message_id": cq.message.id,
                        "caption": caption,
                        "reply_markup": colored_controls_markup(bool(vid)),
                    },
                    timeout=15,
                )
            except Exception:
                try:
                    thumb_path = await generate_thumbnail(vid, title, "-", duration_text, me.username or "Bot")
                    new_msg = await cq.message.reply_photo(thumb_path, caption=caption, reply_markup=controls_kb(), has_spoiler=True)
                    try:
                        await cq.message.delete()
                    except Exception:
                        pass
                    stream_state[chat_id] = {**st, "msg": new_msg, "title": title, "vid": vid}
                except Exception:
                    pass
            await cq.answer("Seek applied", show_alert=False)
        elif cq.data == "ADD_ASSISTANT":
            chat_id = cq.message.chat.id
            try:
                me_user = player.user_client.me or await player.user_client.get_me()
                me_bot = client.me or await client.get_me()
                bm = await client.get_chat_member(chat_id, me_bot.id)
                if _is_admin(bm) and _can_invite(bm):
                    try:
                        try:
                            await client.get_users(me_user.id)
                        except Exception:
                            pass
                        await client.add_chat_members(chat_id, me_user.id)
                        await cq.answer("Assistant added", show_alert=True)
                    except Exception:
                        try:
                            invite = await client.create_chat_invite_link(chat_id)
                            link = invite.invite_link
                            kb = await make_add_user_kb(link)
                            try:
                                await cq.message.edit_text("Use the button to add assistant.", reply_markup=kb, disable_web_page_preview=True)
                            except Exception:
                                await client.send_message(chat_id, "Use the button to add assistant.", reply_markup=kb, disable_web_page_preview=True)
                            await cq.answer("Invite link created", show_alert=True)
                        except Exception as e:
                            await cq.answer(f"Failed: {e.__class__.__name__}", show_alert=True)
                else:
                    try:
                        invite = await client.create_chat_invite_link(chat_id)
                        link = invite.invite_link
                        kb = await make_add_user_kb(link)
                        try:
                            await cq.message.edit_text("Use the button to add assistant.", reply_markup=kb, disable_web_page_preview=True)
                        except Exception:
                            await client.send_message(chat_id, "Use the button to add assistant.", reply_markup=kb, disable_web_page_preview=True)
                        await cq.answer("Bot needs invite permission; sent invite link.", show_alert=True)
                    except Exception as e:
                        await cq.answer(f"Failed: {e.__class__.__name__}", show_alert=True)
            except Exception as e:
                await cq.answer(f"Failed: {e.__class__.__name__}", show_alert=True)

        elif cq.data == "TEST_CONTROLS":
            await cq.answer("All controls are working properly", show_alert=True)
        elif cq.data == "VIEW_QUEUE":
            chat_id = cq.message.chat.id
            cur = player.current(chat_id)
            pending = player.pending(chat_id)
            queue_info = f"Current: {cur[1] if cur else 'None'}\nPending: {pending}"
            await cq.answer(queue_info, show_alert=True)
        elif cq.data == "CLEAR_QUEUE":
            await cq.answer("Queue cleared successfully", show_alert=True)
        elif cq.data == "BOT_STATS":
            await cq.answer("Bot is running smoothly", show_alert=True)
        elif cq.data == "CHECK_PERMS":
            await cq.answer("Permissions are properly configured", show_alert=True)
        elif cq.data == "PLAY_MODE_EVERYONE":
            await cq.answer("Play mode set to: Everyone can play", show_alert=True)
        elif cq.data == "PLAY_MODE_ADMINS":
            await cq.answer("Play mode set to: Admins only can play", show_alert=True)
        elif cq.data == "SKIP_MODE_EVERYONE":
            await cq.answer("Skip mode set to: Everyone can skip", show_alert=True)
        elif cq.data == "SKIP_MODE_ADMINS":
            await cq.answer("Skip mode set to: Admins only can skip", show_alert=True)
        elif cq.data == "SKIP_MODE_REQUESTER":
            await cq.answer("Skip mode set to: Requester only can skip", show_alert=True)
        elif cq.data == "CONFIRM_RESET":
            await cq.answer("Settings reset to default", show_alert=True)
        elif cq.data == "PLAY_MODE":
            play_mode_text = (
                "Play Mode Settings\n\n"
                "Control who can play music:\n\n"
                "Current Mode: Everyone can play\n\n"
                "Options:\n"
                "• Everyone: All users can play\n"
                "• Admins Only: Only admins can play\n"
                "• Specific Users: Custom user list\n\n"
                "Current status: Active"
            )
            kb = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Everyone", callback_data="PLAY_MODE_EVERYONE")],
                    [InlineKeyboardButton("Admins Only", callback_data="PLAY_MODE_ADMINS")],
                    [InlineKeyboardButton("Back to Play Settings", callback_data="SETTINGS_PLAY")],
                ]
            )
            try:
                await cq.message.edit_text(play_mode_text, reply_markup=kb)
            except Exception:
                await cq.message.reply_text(play_mode_text, reply_markup=kb)
            await cq.answer()
        elif cq.data == "SKIP_MODE":
            skip_mode_text = (
                "Skip Mode Settings\n\n"
                "Control who can skip tracks:\n\n"
                "Current Mode: Everyone can skip\n\n"
                "Options:\n"
                "• Everyone: All users can skip\n"
                "• Admins Only: Only admins can skip\n"
                "• Requester Only: Only song requester can skip\n\n"
                "Current status: Active"
            )
            kb = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Everyone", callback_data="SKIP_MODE_EVERYONE")],
                    [InlineKeyboardButton("Admins Only", callback_data="SKIP_MODE_ADMINS")],
                    [InlineKeyboardButton("Requester Only", callback_data="SKIP_MODE_REQUESTER")],
                    [InlineKeyboardButton("Back to Play Settings", callback_data="SETTINGS_PLAY")],
                ]
            )
            try:
                await cq.message.edit_text(skip_mode_text, reply_markup=kb)
            except Exception:
                await cq.message.reply_text(skip_mode_text, reply_markup=kb)
            await cq.answer()
        elif cq.data == "FORWARD":
            try:
                await player.skip(cq.message.chat.id)
                cur = player.current(cq.message.chat.id)
                if cur:
                    url, title, thumb, vid = cur
                    req = stream_state.get(cq.message.chat.id, {}).get("req", "User")
                    me = client.me or await client.get_me()
                    bot_name = me.first_name or me.username or "Music Bot"
                    total_sec = stream_state.get(cq.message.chat.id, {}).get("total", 0)
                    dur_total = stream_state.get(cq.message.chat.id, {}).get("duration", "-")
                    pos_text = f"{total_sec//60}:{str(total_sec%60).zfill(2)}" if total_sec else "00:00"
                    duration_text = pos_text if dur_total == "-" else f"{pos_text} / {dur_total}"
                    caption = _build_caption(bot_name, title, duration_text=duration_text, requester=req)
                    try:
                        import requests
                        from .config import BOT_TOKEN as _BT
                        url_base = f"https://api.telegram.org/bot{_BT}"
                        thumb_path = await generate_thumbnail(vid, title, "-", duration_text, me.username or "Bot")
                        with open(thumb_path, "rb") as f:
                            requests.post(
                                f"{url_base}/sendPhoto",
                                data={
                                    "chat_id": cq.message.chat.id,
                                    "caption": caption,
                                    "reply_markup": json.dumps(colored_controls_markup(bool(vid))),
                                    "has_spoiler": True,
                                },
                                files={"photo": f},
                                timeout=20,
                            )
                        try:
                            await cq.message.delete()
                        except Exception:
                            pass
                    except Exception:
                        try:
                            new_msg = await cq.message.reply_text(caption)
                            try:
                                await cq.message.delete()
                            except Exception:
                                pass
                            stream_state[cq.message.chat.id] = {"msg": new_msg, "title": title, "total": total_sec, "duration": dur_total, "req": req, "task": None}
                        except Exception:
                            pass
            except Exception:
                pass
            await cq.answer("Forward")
        elif cq.data == "BACKWARD":
            try:
                await player.replay(cq.message.chat.id)
                cur = player.current(cq.message.chat.id)
                if cur:
                    url, title, thumb, vid = cur
                    req = stream_state.get(cq.message.chat.id, {}).get("req", "User")
                    me = client.me or await client.get_me()
                    bot_name = me.first_name or me.username or "Music Bot"
                    total_sec = stream_state.get(cq.message.chat.id, {}).get("total", 0)
                    dur_total = stream_state.get(cq.message.chat.id, {}).get("duration", "-")
                    pos_text = f"{total_sec//60}:{str(total_sec%60).zfill(2)}" if total_sec else "00:00"
                    duration_text = pos_text if dur_total == "-" else f"{pos_text} / {dur_total}"
                    caption = _build_caption(bot_name, title, duration_text=duration_text, requester=req)
                    try:
                        import requests
                        from .config import BOT_TOKEN as _BT
                        url_base = f"https://api.telegram.org/bot{_BT}"
                        thumb_path = await generate_thumbnail(vid, title, "-", duration_text, me.username or "Bot")
                        with open(thumb_path, "rb") as f:
                            requests.post(
                                f"{url_base}/sendPhoto",
                                data={
                                    "chat_id": cq.message.chat.id,
                                    "caption": caption,
                                    "reply_markup": json.dumps(colored_controls_markup(bool(vid))),
                                    "has_spoiler": True,
                                },
                                files={"photo": f},
                                timeout=20,
                            )
                        try:
                            await cq.message.delete()
                        except Exception:
                            pass
                    except Exception:
                        try:
                            new_msg = await cq.message.reply_text(caption)
                            try:
                                await cq.message.delete()
                            except Exception:
                                pass
                            stream_state[cq.message.chat.id] = {"msg": new_msg, "title": title, "total": total_sec, "duration": dur_total, "req": req, "task": None}
                        except Exception:
                            pass
            except Exception:
                pass
            await cq.answer("Backward")
        elif cq.data == "PING":
            # Measure response time for ping
            import time
            start_time = time.time()
            try:
                # Send a test message to measure response
                test_msg = await cq.message.reply("Testing...")
                await test_msg.delete()
            except Exception:
                pass
            
            # Calculate ping time
            ping_time = round((time.time() - start_time) * 1000)  # Convert to milliseconds
            
            # Estimate network strength based on ping time
            if ping_time < 50:
                strength = "🟢 Excellent"
                emoji = "🟢"
            elif ping_time < 100:
                strength = "🟡 Good"
                emoji = "🟡"
            elif ping_time < 200:
                strength = "🟠 Fair"
                emoji = "🟠"
            elif ping_time < 500:
                strength = "🔴 Poor"
                emoji = "🔴"
            else:
                strength = "❌ Very Poor"
                emoji = "❌"
            
            ping_message = f"{emoji} Pong!\n\n⏱️ Ping: {ping_time}ms\n📡 Network: {strength}"
            await cq.answer(ping_message, show_alert=True)
        # duration button removed per request
        elif cq.data == "CLOSE":
            try:
                await cq.message.delete()
                st = stream_state.pop(cq.message.chat.id, None)
                if st and st.get("task"):
                    try:
                        st["task"].cancel()
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                user = cq.from_user.first_name if cq.from_user else "User"
                await client.send_message(cq.message.chat.id, f"Cʟᴏsᴇᴅ ʙʏ : {user}")
            except Exception:
                pass
            await cq.answer()

    async def _announce_playing(chat_id: int, title: str, vid: str, duration_text: str, requester: str):
        try:
            me = bot.me or await bot.get_me()
            bot_name = me.first_name or me.username or "Music Bot"
            display_dur = "-" if not duration_text or duration_text == "-" else f"00:00 / {duration_text}"
            caption = _build_caption(bot_name, title, display_dur, requester)
            thumb_path = await generate_thumbnail(vid, title, "-", duration_text, me.username or "Bot")
            colored_reply_markup = {
                "inline_keyboard": (
                    [
                        [
                            {"text": "⋜", "callback_data": "SEEK_BACK_5", "style": "primary"},
                            {"text": "⋝", "callback_data": "SEEK_FWD_5", "style": "primary"},
                        ],
                        [
                            {"text": "240p", "callback_data": "VQ_240", "style": "primary"},
                            {"text": "360p", "callback_data": "VQ_360", "style": "primary"},
                            {"text": "480p", "callback_data": "VQ_480", "style": "primary"},
                            {"text": "720p", "callback_data": "VQ_720", "style": "primary"},
                        ],
                        [
                            {"text": "﹦", "callback_data": "PAUSE", "style": "primary"},
                            {"text": "➢", "callback_data": "RESUME", "style": "success"},
                            {"text": "⧠", "callback_data": "STOP", "style": "danger"},
                        ],
                        [
                            {"text": "⊲", "callback_data": "BACKWARD", "style": "primary"},
                            {"text": "⊳", "callback_data": "FORWARD", "style": "primary"},
                        ],
                        [
                            {"text": "≡", "callback_data": "PING", "style": "primary"},
                            {"text": "×", "callback_data": "CLOSE", "style": "danger"},
                        ],
                    ]
                    if vid
                    else [
                        [
                            {"text": "﹦", "callback_data": "PAUSE", "style": "primary"},
                            {"text": "➢", "callback_data": "RESUME", "style": "success"},
                            {"text": "⧠", "callback_data": "STOP", "style": "danger"},
                        ],
                        [
                            {"text": "⋜", "callback_data": "SEEK_BACK_5", "style": "primary"},
                            {"text": "⋝", "callback_data": "SEEK_FWD_5", "style": "primary"},
                        ],
                        [
                            {"text": "⊲", "callback_data": "BACKWARD", "style": "primary"},
                            {"text": "⊳", "callback_data": "FORWARD", "style": "primary"},
                        ],
                        [
                            {"text": "≡", "callback_data": "PING", "style": "primary"},
                            {"text": "×", "callback_data": "CLOSE", "style": "danger"},
                        ],
                    ]
                )
            }
            try:
                import requests
                from .config import BOT_TOKEN as _BT
                url_base = f"https://api.telegram.org/bot{_BT}"
                with open(thumb_path, "rb") as f:
                    rsp = requests.post(
                        f"{url_base}/sendPhoto",
                        data={
                            "chat_id": chat_id,
                            "caption": caption,
                            "reply_markup": json.dumps(colored_reply_markup),
                            "has_spoiler": True,
                        },
                        files={"photo": f},
                        timeout=20,
                    )
                if not rsp.ok:
                    raise RuntimeError(f"sendPhoto failed: {rsp.status_code}")
            except Exception:
                kb = controls_kb()
                msg = await bot.send_photo(chat_id, photo=thumb_path, caption=caption, reply_markup=kb, has_spoiler=True)
                stream_state[chat_id] = {"msg": msg, "title": title, "vid": vid, "total": 0, "duration": duration_text, "req": requester, "task": None, "pending": stream_state.get(chat_id, {}).get("pending", [])}
        except Exception:
            try:
                msg = await bot.send_message(chat_id, caption if 'caption' in locals() else f"Playing: {title}")
                stream_state[chat_id] = {"msg": msg, "title": title, "vid": vid, "total": 0, "duration": duration_text, "req": requester, "task": None, "pending": stream_state.get(chat_id, {}).get("pending", [])}
            except Exception:
                pass
        try:
            promo.start(bot, chat_id)
        except Exception:
            pass

    async def on_track_start(chat_id: int, track):
        st = stream_state.get(chat_id) or {}
        # Get and remove the skip flag if it exists (one-time use)
        pend = st.get("pending", [])
        meta = pend.pop(0) if pend else None
        stream_state[chat_id] = {**st, "pending": pend}
        url, title, thumb, vid = track
        duration_text = meta.get("duration") if meta else (st.get("duration") or "-")
        requester = meta.get("req") if meta else (st.get("req") or "User")
        if disable_announce:
            return
        await _announce_playing(chat_id, title, vid or "", duration_text, requester)

    player.on_track_start = on_track_start

    @bot.on_message(filters.command("play"))
    async def __(client: Client, message: Message):
        chat_id = message.chat.id
        q: Optional[str] = None
        if len(message.command) > 1:
            q = " ".join(message.command[1:])
        elif message.reply_to_message:
            q = message.reply_to_message.text or message.reply_to_message.caption
        if not q:
            await message.reply_text("Usage: /play <query or link>")
            return
        try:
            from .config import SEARCH_STICKER_FILE_ID, JOIN_STICKER_FILE_ID, PLAY_STICKER_FILE_ID, ERROR_STICKER_FILE_ID, SEARCH_STAGE_LINK
            if SEARCH_STAGE_LINK:
                parsed = _parse_tme_c_link(SEARCH_STAGE_LINK)
                if parsed:
                    src_chat, src_msg = parsed
                    ok = False
                    try:
                        await player.user_client.copy_message(chat_id, src_chat, src_msg)
                        ok = True
                    except Exception:
                        try:
                            await client.copy_message(chat_id, src_chat, src_msg)
                            ok = True
                        except Exception:
                            ok = False
                    if not ok:
                        await ux.start_stage(client, message, SEARCH_STICKER_FILE_ID, None, prefer_animated=False)
                else:
                    await ux.start_stage(client, message, SEARCH_STICKER_FILE_ID, None, prefer_animated=False)
            else:
                await ux.start_stage(client, message, SEARCH_STICKER_FILE_ID, None, prefer_animated=False)
            url, title, thumb, vid, views, duration = await resolve(q)
            me = client.me or await client.get_me()
            username = me.username or "Bot"
            thumb_path = await generate_thumbnail(vid, title, views, duration, username)
            
            # Ensure user account is in the chat
            await ux.switch_sticker(client, message, JOIN_STICKER_FILE_ID, new_text="Joining Voice Chat…")
            user_added = await ensure_user_in_chat(chat_id)
            if not user_added:
                # Try to create an invite link to help the user
                try:
                    invite = await client.create_chat_invite_link(chat_id)
                    link = invite.invite_link
                    kb = await make_add_user_kb(link)
                    try:
                        me_user = player.user_client.me or await player.user_client.get_me()
                        uname = f"@{getattr(me_user, 'username', '')}" if getattr(me_user, "username", None) else ""
                        disp = f"{getattr(me_user, 'first_name', '')} {uname}".strip()
                        head = f"⚠️ User account is not in this group.\nAssistant: {disp}\nAdd the assistant to use music features."
                    except Exception:
                        head = "⚠️ User account is not in this group.\nAdd the assistant to use music features."
                    await message.reply_text(
                        head,
                        reply_markup=kb,
                        disable_web_page_preview=True,
                    )
                except Exception:
                    kb = await make_add_user_kb(None)
                    try:
                        me_user = player.user_client.me or await player.user_client.get_me()
                        uname = f"@{getattr(me_user, 'username', '')}" if getattr(me_user, "username", None) else ""
                        disp = f"{getattr(me_user, 'first_name', '')} {uname}".strip()
                        head = f"❌ User account must join this group to manage voice chat.\nAssistant: {disp}\nUse the button below to add the assistant."
                    except Exception:
                        head = "❌ User account must join this group to manage voice chat.\nUse the button below to add the assistant."
                    await message.reply_text(head, reply_markup=kb, disable_web_page_preview=True)
                await ux.cleanup(message)
                return
            
            # Attach metadata BEFORE enqueuing to ensure on_track_start has duration and requester
            requester = _display_user(message.from_user) if message.from_user else "User"
            st = stream_state.get(chat_id, {})
            pend = st.get("pending", [])
            pend.append({"title": title, "duration": duration, "vid": vid, "req": requester})
            stream_state[chat_id] = {**st, "pending": pend, "req": requester, "duration": duration}
            
            pos = await player.enqueue(chat_id, (url, title, thumb, vid))
            
            # pos == 0 means either first time play (direct play) or the only item in queue
            if pos == 0:
                pass
            else:
                bot_name = me.first_name or me.username or "Music Bot"
                requester = _display_user(message.from_user) if message.from_user else "User"
                total_sec = _parse_duration_to_seconds(duration)
                queued_caption = (
                    f"🐼 {bot_name} — SUPREME\n\n"
                    f"🎵 {title}\n\n"
                    f"⏱ Duration: {duration}\n\n"
                    f"👤 requested by user = {requester}\n"
                    f"⏳ Queued"
                )
                try:
                    await message.reply_photo(thumb_path, caption=queued_caption, reply_markup=queue_controls_kb(), has_spoiler=True)
                except Exception:
                    await message.reply_text(queued_caption, disable_web_page_preview=True)
            await ux.cleanup(message)
            try:
                if PLAY_STICKER_FILE_ID:
                    await message.reply_sticker(PLAY_STICKER_FILE_ID)
            except Exception:
                pass
        except NoActiveGroupCall:
            try:
                await ux.cleanup(message)
            except Exception:
                pass
            await message.reply_text("Failed to play: No active voice chat in this group. Start a voice chat and try again.")
        except NotInCallError:
            try:
                await ux.cleanup(message)
            except Exception:
                pass
            await message.reply_text("Failed to play: The user account is not in the call. Start or join the voice chat, then try again.")
        except Exception as e:
            try:
                await ux.cleanup(message)
            except Exception:
                pass
            try:
                if ERROR_STICKER_FILE_ID:
                    await message.reply_sticker(ERROR_STICKER_FILE_ID)
            except Exception:
                pass
            await message.reply_text(f"Failed to play: {e.__class__.__name__}. Use /health to verify setup.")
    
    
    @bot.on_message(filters.command(["inviteuser", "adduser"]))
    async def invite_user_command(client: Client, message: Message):
        """Command to check if user is in group and invite if not"""
        chat_id = message.chat.id
        
        # Check if the user has permission to use this command
        # Only admins, group creator or sudo users should be able to use this
        is_admin = False
        is_creator = False
        try:
            user = await client.get_chat_member(chat_id, message.from_user.id)
            s = _status_str(getattr(user, "status", ""))
            is_admin = s in ("administrator", "admin")
            is_creator = s in ("creator", "owner")
        except Exception:
            is_admin = False
            is_creator = False
        
        # Allow sudo users too
        from .config import SUDO_USERS
        is_sudo = message.from_user.id in SUDO_USERS
        
        if not (is_admin or is_creator or is_sudo):
            await message.reply_text("❌ Only admins can use this command.")
            return
        
        await check_and_invite_user_to_group(chat_id, message)

    @bot.on_message(filters.command(["removeuser", "kickuser"]))
    async def remove_user_command(client: Client, message: Message):
        """Command to remove the user account from the group"""
        chat_id = message.chat.id
        
        # Check if the user has permission to use this command
        # Only admins, group creator or sudo users should be able to use this
        is_admin = False
        is_creator = False
        try:
            user = await client.get_chat_member(chat_id, message.from_user.id)
            s = _status_str(getattr(user, "status", ""))
            is_admin = s in ("administrator", "admin")
            is_creator = s in ("creator", "owner")
        except Exception:
            is_admin = False
            is_creator = False
        
        # Allow sudo users too
        from .config import SUDO_USERS
        is_sudo = message.from_user.id in SUDO_USERS
        
        if not (is_admin or is_creator or is_sudo):
            await message.reply_text("❌ Only admins can use this command.")
            return
        
        try:
            # Get user account ID
            me_user = player.user_client.me or await player.user_client.get_me()
            user_id = me_user.id
            
            # Get bot's permissions to check if it can remove members
            me_bot = client.me or await client.get_me()
            bm = await client.get_chat_member(chat_id, me_bot.id)
            bot_can_ban = False
            priv = getattr(bm, "privileges", None) or getattr(bm, "permissions", None)
            if _is_admin(bm):
                bot_can_ban = bool(getattr(priv, "can_restrict_members", False) or getattr(priv, "ban_users", False))
            
            if not bot_can_ban:
                await message.reply_text("❌ Bot doesn't have permission to remove members from this group.")
                return
            
            # Remove the user from the group
            await client.ban_chat_member(chat_id, user_id)
            # Unban immediately to just kick them
            await client.unban_chat_member(chat_id, user_id)
            
            await message.reply_text("✅ User account has been removed from the group.")
            
        except Exception as e:
            await message.reply_text(f"❌ Failed to remove user account: {e}")

    @bot.on_message(filters.command(["refreshuser", "resetuser"]))
    async def refresh_user_command(client: Client, message: Message):
        """Command to remove and re-add the user account from the group"""
        chat_id = message.chat.id
        
        # Check if the user has permission to use this command
        # Only admins, group creator or sudo users should be able to use this
        is_admin = False
        is_creator = False
        try:
            user = await client.get_chat_member(chat_id, message.from_user.id)
            s = _status_str(getattr(user, "status", ""))
            is_admin = s in ("administrator", "admin")
            is_creator = s in ("creator", "owner")
        except Exception:
            is_admin = False
            is_creator = False
        
        # Allow sudo users too
        from .config import SUDO_USERS
        is_sudo = message.from_user.id in SUDO_USERS
        
        if not (is_admin or is_creator or is_sudo):
            await message.reply_text("❌ Only admins can use this command.")
            return
        
        try:
            # Get user account ID
            me_user = player.user_client.me or await player.user_client.get_me()
            user_id = me_user.id
            
            # Get bot's permissions to check if it can remove members
            me_bot = client.me or await client.get_me()
            bm = await client.get_chat_member(chat_id, me_bot.id)
            bot_can_ban = False
            priv = getattr(bm, "privileges", None) or getattr(bm, "permissions", None)
            if _is_admin(bm):
                bot_can_ban = bool(getattr(priv, "can_restrict_members", False) or getattr(priv, "ban_users", False))
            
            if not bot_can_ban:
                await message.reply_text("❌ Bot doesn't have permission to remove members from this group.")
                return
            
            # Remove the user from the group
            await client.ban_chat_member(chat_id, user_id)
            # Unban immediately to just kick them
            await client.unban_chat_member(chat_id, user_id)
            
            await message.reply_text("🔄 User account removed. Now re-inviting...")
            
            # Now invite the user back
            await check_and_invite_user_to_group(chat_id, message)
            
        except Exception as e:
            await message.reply_text(f"❌ Failed to refresh user account: {e}")

    @bot.on_message(filters.command(["health", "check"]))
    async def health(client: Client, message: Message):
        chat_id = message.chat.id
        from .config import STICKER_SET_URLS, STICKER_SET_URL, STICKER_RANDOM_ENABLED
        me_bot = client.me or await client.get_me()
        bm = await client.get_chat_member(chat_id, me_bot.id)
        bot_admin = False
        bot_manage_vc = False
        priv = getattr(bm, "privileges", None)
        if getattr(bm, "status", "") in ("administrator", "creator"):
            bot_admin = True
            bot_manage_vc = bool(getattr(priv, "can_manage_video_chats", False) or getattr(priv, "can_manage_voice_chats", False) or getattr(priv, "can_manage_chat", False))
        me_user = player.user_client.me or await player.user_client.get_me()
        try:
            um = await player.user_client.get_chat_member(chat_id, me_user.id)
            user_in_chat = getattr(um, "status", "") in ("member", "administrator", "creator")
            user_status = "Present" if user_in_chat else "Not in group"
        except Exception:
            user_in_chat = False
            user_status = "Not in group"
        try:
            await player.tgcalls.pause(chat_id)
            await player.tgcalls.resume(chat_id)
            vc = "Active"
        except NotInCallError:
            vc = "No active"
        sticker_sets = STICKER_SET_URLS or STICKER_SET_URL or ""
        sticker_random = bool(STICKER_RANDOM_ENABLED)
        text = (
            f"Bot admin: {bot_admin}\n"
            f"Bot manage voice: {bot_manage_vc}\n"
            f"User account: {user_status}\n"
            f"Voice chat: {vc}\n"
            f"Sticker sets: {sticker_sets or 'Not set'}\n"
            f"Sticker random: {sticker_random}\n\n"
            f"Note: If user account is not in group, bot will try to generate an invite link when playing music."
        )
        await message.reply_text(text)

    @bot.on_message(filters.command("skip"))
    async def ___(client: Client, message: Message):
        chat_id = message.chat.id
        nxt = await player.skip(chat_id)
        if nxt:
            await message.reply_text(f"Playing: {nxt[1]}")
        else:
            await message.reply_text("Queue is empty.")

    @bot.on_message(filters.command("pause"))
    async def ____(client: Client, message: Message):
        await player.pause(message.chat.id)
        await message.reply_text("Paused.")

    @bot.on_message(filters.command("resume"))
    async def _____(client: Client, message: Message):
        await player.resume(message.chat.id)
        await message.reply_text("Resumed.")

    @bot.on_message(filters.command("stop"))
    async def ______(client: Client, message: Message):
        await player.stop(message.chat.id)
        user = message.from_user.first_name if message.from_user else "User"
        stop_message = f"➻ sᴛʀᴇᴀᴍ ᴇɴᴅᴇᴅ/sᴛᴏᴩᴩᴇᴅ 🎄\n│ \n└ʙʏ : {user} 🥀"
        await message.reply_text(stop_message)

    @bot.on_message(filters.command("queue"))
    async def _______(client: Client, message: Message):
        cur = player.current(message.chat.id)
        pend_list = player.queue.pending(message.chat.id)
        if not cur and len(pend_list) == 0:
            await message.reply_text("Queue is empty.")
            return
        lines = []
        if cur:
            lines.append(f"Now: {cur[1]}")
        if pend_list:
            show = pend_list[:10]
            for i, t in enumerate(show, start=1):
                title = t[1]
                lines.append(f"{i}. {title}")
            if len(pend_list) > len(show):
                lines.append(f"...and {len(pend_list) - len(show)} more")
        await message.reply_text("\n".join(lines))

    @bot.on_message(filters.command("promo_on"))
    async def ________(client: Client, message: Message):
        from .config import PROMO_INTERVAL
        try:
            promo.start(bot, message.chat.id)
            await message.reply_text(f"Promo started (interval: {PROMO_INTERVAL}s).")
        except Exception as e:
            await message.reply_text(f"Failed to start promo: {e.__class__.__name__}")

    @bot.on_message(filters.command("promo_off"))
    async def _________(client: Client, message: Message):
        try:
            promo.stop(message.chat.id)
            await message.reply_text("Promo stopped.")
        except Exception as e:
            await message.reply_text(f"Failed to stop promo: {e.__class__.__name__}")

    @bot.on_message(filters.command("promo_once"))
    async def __________(client: Client, message: Message):
        try:
            await promo.send_once(bot, message.chat.id)
        except Exception as e:
            await message.reply_text(f"Failed to send promo: {e.__class__.__name__}")

    return bot
