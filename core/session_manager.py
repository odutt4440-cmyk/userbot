import logging
import asyncio
import gc
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH, ADMIN_ID
from database import get_user_session, is_subscribed, get_user_plan_type, set_bot_status
from core.plugin_loader import load_all_modules

log = logging.getLogger(__name__)

# Dictionary: {user_id: {"client": client, "module": "name", "task": background_task}}
ACTIVE_CLIENTS = {}
# USER LOCKS: To prevent race conditions
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
        """Starts a userbot with Hard Instance Killing to prevent double response."""
        
        if user_id not in USER_LOCKS:
            USER_LOCKS[user_id] = asyncio.Lock()
        
        async with USER_LOCKS[user_id]:
            # 🛡️ 1. Plan & Subscription Check
            if not await is_subscribed(user_id):
                return "❌ Subscription Expired."

            plan = await get_user_plan_type(user_id)
            current_plan = str(plan).strip().lower()
            trigger_raw = str(module_name).strip().lower()
            is_all = trigger_raw in ["all", "all modules", "all_modules", "force_start_all"]

            if is_all and "empire" not in current_plan and user_id != ADMIN_ID:
                return "❌ Empire Plan Required for this feature."

            # 🛠️ 2. HARD CLEANUP (Ghost Killer)
            if user_id in ACTIVE_CLIENTS:
                log.info(f"💀 Killing existing zombie bot for {user_id}...")
                try:
                    old_data = ACTIVE_CLIENTS[user_id]
                    # Disconnect client
                    await old_data["client"].disconnect()
                    # Cancel the background listening task
                    if "task" in old_data and old_data["task"]:
                        old_data["task"].cancel()
                    
                    await asyncio.sleep(1) # Gap to release resources
                except Exception as e:
                    log.error(f"Cleanup Error: {e}")
                
                del ACTIVE_CLIENTS[user_id]
                gc.collect()

            # 🚀 3. Session Retrieval
            string_session = await get_user_session(user_id)
            if not string_session: return "❌ Session not found."

            # 🚀 4. Client Initialization
            client = TelegramClient(
                StringSession(string_session), 
                API_ID, 
                API_HASH,
                sequential_updates=True, # 🔥 Lag Fix: One by one processing
                flood_sleep_threshold=60,
                device_model="Empire-Userbot v2"
            )

            try:
                await asyncio.wait_for(client.connect(), timeout=30)
                if not await client.is_user_authorized():
                    return "❌ Invalid Session. relogin required."

                # 🔥 Clear any internal handlers before loading new ones
                client._event_builders.clear()

                # Load Plugins
                load_target = "all modules" if is_all else INTERNAL_MAP.get(trigger_raw, trigger_raw)
                await load_all_modules(client, target_module=load_target)

                display_name = "ALL_MODULES" if is_all else load_target.upper()
                
                # 🔥 5. Start Listening Task and Track it
                task = client.loop.create_task(client.run_until_disconnected())
                
                # Final assignment with task tracking
                ACTIVE_CLIENTS[user_id] = {
                    "client": client, 
                    "module": display_name,
                    "task": task 
                }
                
                await set_bot_status(user_id, True, display_name)
                log.info(f"🚀 Bot fully online for {user_id}")
                
                return f"🚀 **Userbot Online!**\n📦 **Module:** `{display_name}`"

            except Exception as e:
                log.error(f"Startup Error for {user_id}: {e}")
                return f"❌ **Error:** `{str(e)}`"

    @staticmethod
    async def stop_userbot(user_id):
        """Strictly kills the process and cancels all background tasks."""
        if user_id in ACTIVE_CLIENTS:
            try:
                data = ACTIVE_CLIENTS[user_id]
                # 1. Disconnect
                await data["client"].disconnect()
                # 2. Kill Task
                if "task" in data and data["task"]:
                    data["task"].cancel()
                
                await set_bot_status(user_id, False, None)
                del ACTIVE_CLIENTS[user_id]
                gc.collect() 
                return "🛑 **Userbot Stopped & Tasks Cancelled.**"
            except Exception as e:
                return f"❌ **Stop Error:** {e}"
        return "⚠️ Userbot not running."
