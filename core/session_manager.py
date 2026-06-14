import logging
import asyncio
import gc # Garbage Collector
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH, ADMIN_ID
from database import get_user_session, is_subscribed, get_user_plan_type, set_bot_status
from core.plugin_loader import load_all_modules

log = logging.getLogger(__name__)

# Dictionary format: {user_id: {"client": client_instance, "module": "module_name"}}
ACTIVE_CLIENTS = {}

# 🔥 MASTER INTERNAL MAP: Sync with all existing and new modules
INTERNAL_MAP = {
    "info": "info_tools",
    "info_tools": "info_tools",
    "group": "group_tools",
    "admin": "group_tools",
    "management": "group_tools",
    "clone": "clone",
    "afk": "afk",
    "stickers": "stickers",
    "reaction": "reaction",
    "stealth": "stealth"
}

class SessionManager:
    @staticmethod
    async def start_userbot(user_id, module_name):
        """Starts a userbot session with Turbo Memory Optimization."""
        
        # 🛡️ 1. Security & Subscription
        if not await is_subscribed(user_id):
            return "❌ Your subscription has expired."

        plan = await get_user_plan_type(user_id)
        current_plan = str(plan).strip().lower()
        trigger_raw = str(module_name).strip().lower()
        is_all_request = trigger_raw in ["all", "all modules", "all_modules", "force_start_all"]

        # 🛡️ 2. Plan Enforcement
        if is_all_request and "empire" not in current_plan and user_id != ADMIN_ID:
            return "❌ **Access Denied!**\nUpgrade to **Empire Plan** to load all modules."
        
        # 🛡️ 3. Instant Instance Check (Zombie Protection)
        if user_id in ACTIVE_CLIENTS:
            old_client = ACTIVE_CLIENTS[user_id]["client"]
            if old_client.is_connected():
                if "empire" not in current_plan and user_id != ADMIN_ID:
                    running = ACTIVE_CLIENTS[user_id]["module"]
                    return f"⚠️ **Standard Plan Limit:**\nModule `{running}` is already active. Stop it first."
                
                # Empire users ke liye agar 'all' chalu hai toh naya mat chalao
                if is_all_request and ACTIVE_CLIENTS[user_id]["module"] == "ALL_MODULES":
                    return "✅ **Empire Mode** is already running with all features."

        # 🛡️ 4. Session Retrieval
        string_session = await get_user_session(user_id)
        if not string_session:
            return "❌ Session not found. Login again."

        # 🚀 5. Client Setup (Memory Optimized)
        client = TelegramClient(
            StringSession(string_session), 
            API_ID, 
            API_HASH,
            sequential_updates=True, # Low RAM par True zyada stable hai
            flood_sleep_threshold=60,
            device_model="Empire-Userbot v2"
        )

        try:
            # Timeout connect taaki bot hang na ho
            await asyncio.wait_for(client.connect(), timeout=20)
            
            if not await client.is_user_authorized():
                return "❌ Invalid Session! Please relogin."

            # 🛠️ 6. Load Modules
            load_target = "all modules" if is_all_request else INTERNAL_MAP.get(trigger_raw, trigger_raw)
            await load_all_modules(client, target_module=load_target)

            # State Management
            display_name = "ALL_MODULES" if is_all_request else load_target.upper()
            
            # Agar purana client memory me hai toh usey disconnect karo
            if user_id in ACTIVE_CLIENTS:
                try: await ACTIVE_CLIENTS[user_id]["client"].disconnect()
                except: pass

            ACTIVE_CLIENTS[user_id] = {"client": client, "module": display_name}
            
            # Database Sync
            await set_bot_status(user_id, True, display_name)
            
            # Run Task
            client.loop.create_task(client.run_until_disconnected())
            
            log.info(f"🚀 Bot Started: {user_id} | Module: {display_name}")
            return f"✅ **Userbot Online!**\n📦 **Module:** `{display_name}`\n💎 **Plan:** `{plan.upper()}`"

        except asyncio.TimeoutError:
            return "❌ **Connection Timeout:** Telegram servers are responding slow. Try again."
        except Exception as e:
            log.error(f"Startup Error: {e}")
            return f"❌ **Error:** `{str(e)}`"

    @staticmethod
    async def stop_userbot(user_id):
        """Cleanly disconnects and PURGES memory."""
        if user_id in ACTIVE_CLIENTS:
            try:
                client = ACTIVE_CLIENTS[user_id]["client"]
                
                # 1. Disconnect
                if client.is_connected():
                    await client.disconnect()
                
                # 2. Update DB
                await set_bot_status(user_id, False, None)
                
                # 3. Nuke from Dictionary
                del ACTIVE_CLIENTS[user_id]
                
                # 4. 🔥 FORCE GARBAGE COLLECTION
                # Ye line Railway ki RAM turant khali karegi
                gc.collect()
                
                return "🛑 **Userbot Stopped & RAM Cleared.**"
            except Exception as e:
                return f"❌ **Stop Error:** `{e}`"
        return "⚠️ Userbot is not running."
