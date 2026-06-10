import logging
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH, ADMIN_ID
from database import get_user_session, is_subscribed, get_user_plan_type
from core.plugin_loader import load_all_modules

log = logging.getLogger(__name__)

# Dictionary format: {user_id: {"client": client_instance, "module": "module_name"}}
ACTIVE_CLIENTS = {}

class SessionManager:
    @staticmethod
    async def start_userbot(user_id, module_name):
        """Starts a userbot session with strict plan enforcement."""
        
        # 🛡️ 1. Security & Subscription Check
        if not await is_subscribed(user_id):
            return "❌ Your subscription has expired. Please buy a plan to reactivate."

        # 🛡️ 2. Plan Retrieval & Normalization
        plan = await get_user_plan_type(user_id)
        current_plan = str(plan).strip().lower()
        
        # Normalize trigger for strict checking
        trigger_clean = str(module_name).strip().lower()
        # 🔥 Check if this is any kind of 'ALL' request
        is_all_request = "all" in trigger_clean

        # 🔥 THE ULTIMATE GUARD: Stop Standard users from ANY 'ALL' trigger
        # Agar request me 'all' hai aur plan 'empire' nahi hai, toh seedha block.
        if is_all_request and "empire" not in current_plan and user_id != ADMIN_ID:
            return (
                "❌ **Access Denied!**\n\n"
                "Your plan (**Standard**) only allows **one module at a time**.\n"
                "You are not allowed to use the 'Activate All' feature.\n\n"
                "👉 Please upgrade to **Empire Plan** (₹35) to unlock this."
            )
        
        # 🛡️ 3. Existing Session Handling
        if user_id in ACTIVE_CLIENTS:
            # For Standard users trying to switch or restart individual modules
            if "empire" not in current_plan and user_id != ADMIN_ID:
                running_module = ACTIVE_CLIENTS[user_id]["module"]
                
                # If trying to start the same one
                if running_module == module_name.upper():
                    return f"⚠️ Your userbot is already running the **{module_name.upper()}** module."
                
                # If they try to trigger any other module (Standard users must stop first)
                return (
                    f"⚠️ **Access Denied:** You are on the **Standard Plan**.\n\n"
                    f"Please stop your running module **[{running_module}]** first "
                    f"before starting **{module_name.upper()}**."
                )
            
            # For Empire/Admin users: If already running, return status
            if "empire" in current_plan or user_id == ADMIN_ID:
                if is_all_request:
                    return f"✅ **Empire Mode Active:** Your userbot is already running with all modules enabled!"

        # 🛡️ 4. Session Retrieval
        string_session = await get_user_session(user_id)
        if not string_session:
            return "❌ No session found. Please generate a string using 'Generate String' first."

        # 🚀 5. Initialize Fresh Telegram Client with Parallel Processing
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
                return "❌ Invalid Session! Your string was revoked. Please generate a new one."

            # 🛠️ 6. Plugin Registration
            await load_all_modules(client)

            # Store the active client
            # Standard users store module name, Empire users store "ALL_MODULES"
            display_name = "ALL_MODULES" if is_all_request else module_name.upper()
            ACTIVE_CLIENTS[user_id] = {
                "client": client,
                "module": display_name
            }
            
            # Start background execution
            client.loop.create_task(client.run_until_disconnected())
            
            log.info(f"🚀 Userbot started for {user_id} [{plan}] | Trigger: {module_name}")
            
            return (
                f"🚀 **Userbot Activated!**\n\n"
                f"**Trigger Mode:** `{display_name}`\n"
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
                data = ACTIVE_CLIENTS[user_id]
                client = data["client"]
                await client.disconnect()
                del ACTIVE_CLIENTS[user_id]
                return "🛑 **Userbot Stopped Successfully.**"
            except Exception as e:
                log.error(f"Stop Error for {user_id}: {e}")
                return f"❌ **Error while stopping:** `{e}`"
        
        return "⚠️ Your userbot is not currently running."
