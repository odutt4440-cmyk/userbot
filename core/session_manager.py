import logging
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH, ADMIN_ID
from database import get_user_session, is_subscribed, get_user_plan_type, set_bot_status
from core.plugin_loader import load_all_modules

log = logging.getLogger(__name__)

# Dictionary format: {user_id: {"client": client_instance, "module": "module_name"}}
ACTIVE_CLIENTS = {}

# 🔥 INTERNAL SAFETY MAP: Taaki loader kabhi fail na ho
# Agar DB ya buttons se purana naam aaye toh ye sahi kar dega
INTERNAL_MAP = {
    "info": "info_tools",
    "info_tools": "info_tools",
    "group": "group_tools",
    "admin": "group_tools",
    "management": "group_tools",
    "clone": "clone",
    "afk": "afk"
}

class SessionManager:
    @staticmethod
    async def start_userbot(user_id, module_name):
        """Starts a userbot session with strict Plan enforcement and Name Fixing."""
        
        # 🛡️ 1. Security Check
        if not await is_subscribed(user_id):
            return "❌ Your subscription has expired. Please buy a plan to reactivate."

        # 🛡️ 2. Plan Retrieval & Normalization
        plan = await get_user_plan_type(user_id)
        current_plan = str(plan).strip().lower()
        
        # Input name ko saaf karo
        trigger_raw = str(module_name).strip().lower()
        is_all_request = trigger_raw in ["all", "all modules", "all_modules", "force_start_all"]

        # 🔥 GUARD: Block Standard users from 'ALL' feature
        if is_all_request and "empire" not in current_plan and user_id != ADMIN_ID:
            return (
                "❌ **Access Denied!**\n\n"
                "Your plan (**Standard**) does not support deploying all modules at once.\n"
                "👉 Please upgrade to **Empire Plan** (₹35) to unlock this."
            )
        
        # 🛡️ 3. Existing Session Handling
        if user_id in ACTIVE_CLIENTS:
            if "empire" not in current_plan and user_id != ADMIN_ID:
                running_module = ACTIVE_CLIENTS[user_id]["module"]
                if running_module == trigger_raw.upper() or running_module == INTERNAL_MAP.get(trigger_raw, "").upper():
                    return f"⚠️ Your userbot is already running the **{running_module}** module."
                
                return (
                    f"⚠️ **Access Denied:** You are on the **Standard Plan**.\n\n"
                    f"Please stop your running module **[{running_module}]** first."
                )
            
            # For Empire/Admin: Just return if they trigger 'all' again
            if ("empire" in current_plan or user_id == ADMIN_ID) and is_all_request:
                return f"✅ **Empire Mode Active:** Your userbot is already running with all modules enabled!"

        # 🛡️ 4. Session Retrieval
        string_session = await get_user_session(user_id)
        if not string_session:
            return "❌ No session found. Please login first."

        # 🚀 5. Initialize Telegram Client
        client = TelegramClient(
            StringSession(string_session), 
            API_ID, 
            API_HASH,
            sequential_updates=False, 
            flood_sleep_threshold=240 
        )

        try:
            await client.connect()
            if not await client.is_user_authorized():
                return "❌ Invalid Session! Please generate a new string."

            # 🛠️ 6. SELECTIVE PLUGIN REGISTRATION (With Name Fixing)
            if "empire" in current_plan or user_id == ADMIN_ID:
                load_target = "all modules" if is_all_request else INTERNAL_MAP.get(trigger_raw, trigger_raw)
            else:
                # Standard user ke liye name fix karke bhejo
                load_target = INTERNAL_MAP.get(trigger_raw, trigger_raw)

            # Ab loader ko hamesha sahi naam milega (jaise 'info_tools')
            await load_all_modules(client, target_module=load_target)

            # Store the state
            display_name = "ALL_MODULES" if is_all_request else load_target.upper()
            ACTIVE_CLIENTS[user_id] = {
                "client": client,
                "module": display_name
            }
            
            # 🔥 DATABASE SYNC
            await set_bot_status(user_id, True, display_name)
            
            client.loop.create_task(client.run_until_disconnected())
            
            log.info(f"🚀 Userbot started for {user_id} | Plan: {plan} | Module: {display_name}")
            
            return (
                f"🚀 **Userbot Activated!**\n\n"
                f"**Loaded Module:** `{display_name}`\n"
                f"**Plan Status:** `{plan}`\n"
                f"**Status:** `Online`"
            )

        except Exception as e:
            log.error(f"Startup Error for {user_id}: {e}")
            return f"❌ **Startup Error:** `{str(e)}`"

    @staticmethod
    async def stop_userbot(user_id):
        """Cleanly disconnects the session."""
        if user_id in ACTIVE_CLIENTS:
            try:
                await set_bot_status(user_id, False)
                await ACTIVE_CLIENTS[user_id]["client"].disconnect()
                del ACTIVE_CLIENTS[user_id]
                return "🛑 **Userbot Stopped Successfully.**"
            except Exception as e:
                return f"❌ **Error:** `{e}`"
        return "⚠️ Not running."
