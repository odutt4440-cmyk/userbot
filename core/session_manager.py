import logging
import asyncio
import gc
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH, ADMIN_ID
from database import get_user_session, is_subscribed, get_user_plan_type, set_bot_status
from core.plugin_loader import load_all_modules

log = logging.getLogger(__name__)

# Dictionary: {user_id: {"client": client, "module": "name"}}
ACTIVE_CLIENTS = {}
# 🔥 USER LOCKS: To prevent multiple simultaneous login attempts for one user
USER_LOCKS = {}

INTERNAL_MAP = {
    "info": "info_tools", "info_tools": "info_tools",
    "group": "group_tools", "admin": "group_tools",
    "management": "group_tools", "clone": "clone",
    "afk": "afk", "stickers": "stickers",
    "reaction": "reaction", "stealth": "stealth"
}

class SessionManager:
    @staticmethod
    async def start_userbot(user_id, module_name):
        """Starts a userbot with Hard Instance Locking to prevent double response."""
        
        # 1. Lock check: User ko ek waqt me ek hi execution allow karo
        if user_id not in USER_LOCKS:
            USER_LOCKS[user_id] = asyncio.Lock()
        
        async with USER_LOCKS[user_id]:
            # 🛡️ Security & Plan Check
            if not await is_subscribed(user_id):
                return "❌ Plan Expired."

            plan = await get_user_plan_type(user_id)
            current_plan = str(plan).strip().lower()
            trigger_raw = str(module_name).strip().lower()
            is_all = trigger_raw in ["all", "all modules", "all_modules", "force_start_all"]

            if is_all and "empire" not in current_plan and user_id != ADMIN_ID:
                return "❌ Empire Plan Required for 'All' features."

            # 🛠️ HARD CLEANUP: Agar bot pehle se list me hai, toh usey marna hi padega
            if user_id in ACTIVE_CLIENTS:
                log.info(f"♻️ Disconnecting existing zombie bot for {user_id}...")
                try:
                    old_client = ACTIVE_CLIENTS[user_id]["client"]
                    await old_client.disconnect()
                except: pass
                del ACTIVE_CLIENTS[user_id]
                gc.collect()

            # 🚀 Session retrieval
            string_session = await get_user_session(user_id)
            if not string_session: return "❌ No Session Found."

            # 🚀 Initialize Client (Optimized for Low RAM)
            client = TelegramClient(
                StringSession(string_session), 
                API_ID, 
                API_HASH,
                sequential_updates=True, # Process messages one by one (No Lag)
                flood_sleep_threshold=60,
                device_model="Empire-Userbot v2"
            )

            try:
                await asyncio.wait_for(client.connect(), timeout=30)
                if not await client.is_user_authorized():
                    return "❌ Invalid Session. Relogin."

                # Plugin Target
                load_target = "all modules" if is_all else INTERNAL_MAP.get(trigger_raw, trigger_raw)
                await load_all_modules(client, target_module=load_target)

                display_name = "ALL_MODULES" if is_all else load_target.upper()
                
                # Double Safety Check
                if user_id in ACTIVE_CLIENTS:
                    try: await ACTIVE_CLIENTS[user_id]["client"].disconnect()
                    except: pass

                ACTIVE_CLIENTS[user_id] = {"client": client, "module": display_name}
                await set_bot_status(user_id, True, display_name)
                
                # Start Background Task
                client.loop.create_task(client.run_until_disconnected())
                
                log.info(f"✅ Bot Successfully Online: {user_id}")
                return f"🚀 **Userbot Online!**\n📦 **Module:** `{display_name}`"

            except Exception as e:
                log.error(f"Startup Error for {user_id}: {e}")
                return f"❌ **Error:** `{str(e)}`"

    @staticmethod
    async def stop_userbot(user_id):
        """Strictly kills the process and frees memory."""
        if user_id in ACTIVE_CLIENTS:
            try:
                client = ACTIVE_CLIENTS[user_id]["client"]
                if client.is_connected():
                    await client.disconnect()
                
                await set_bot_status(user_id, False, None)
                del ACTIVE_CLIENTS[user_id]
                gc.collect() # 🔥 Clear RAM
                return "🛑 **Stopped & Memory Purged.**"
            except Exception as e:
                return f"❌ **Stop Error:** {e}"
        return "⚠️ Bot was not running."
