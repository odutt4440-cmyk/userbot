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
        """Starts a userbot session based on user plan (Standard/Empire)."""
        
        # 🛡️ 1. Security & Subscription Check
        if not await is_subscribed(user_id):
            return "❌ Your subscription has expired. Please buy a plan to reactivate."

        # 🛡️ 2. Plan Logic: Standard vs Empire
        plan = await get_user_plan_type(user_id)
        
        if user_id in ACTIVE_CLIENTS:
            # Agar banda Standard plan par hai aur doosra module chalu kar raha hai
            if plan == "Standard" and user_id != ADMIN_ID:
                running_module = ACTIVE_CLIENTS[user_id]["module"]
                # Agar wahi same module dobara chalu kar raha hai
                if running_module == module_name.upper():
                    return f"⚠️ Your userbot is already running the **{module_name.upper()}** module."
                
                # Agar doosra module chalu kar raha hai bina purana stop kiye
                return (
                    f"⚠️ **Access Denied:** You are on the **Standard Plan**.\n\n"
                    f"Please stop your running module **[{running_module}]** first "
                    f"before starting **{module_name.upper()}**.\n\n"
                    f"💡 *Upgrade to Empire Plan (₹35) to run all modules together!*"
                )
            
            # Agar Empire user hai aur bot pehle se active hai
            if plan == "Empire" or user_id == ADMIN_ID:
                # Empire users ke liye hamara engine saare modules ek sath load kar deta hai
                return f"✅ **Empire Mode Active:** Your userbot is already running with all modules enabled!"

        # 🛡️ 3. Session Retrieval
        string_session = await get_user_session(user_id)
        if not string_session:
            return "❌ No session found. Please generate a string using 'Generate String' first."

        # 🚀 4. Initialize Fresh Telegram Client
        client = TelegramClient(
            StringSession(string_session), 
            API_ID, 
            API_HASH,
            sequential_updates=True,
            flood_sleep_threshold=240 
        )

        try:
            await client.connect()
            if not await client.is_user_authorized():
                return "❌ Invalid Session! Your string was revoked. Please generate a new one."

            # 🛠️ 5. Plugin Registration
            # Empire users ke liye saare load honge, Standard ke liye bhi logic same hai 
            # par usey commands sirf ek ke hi pata honge
            await load_all_modules(client)

            # Store the active client and the name of the module that triggered it
            ACTIVE_CLIENTS[user_id] = {
                "client": client,
                "module": module_name.upper()
            }
            
            # Start background execution
            client.loop.create_task(client.run_until_disconnected())
            
            log.info(f"🚀 Userbot started for {user_id} [{plan}] with trigger: {module_name}")
            
            return (
                f"🚀 **Userbot Activated!**\n\n"
                f"**Trigger Module:** `{module_name.upper()}`\n"
                f"**Your Plan:** `{plan}`\n"
                f"**Status:** `Online`\n\n"
                f"Commands are now active. {'You can now start other modules too!' if plan == 'Empire' else ''}"
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
                module = data["module"]
                
                await client.disconnect()
                del ACTIVE_CLIENTS[user_id]
                
                log.info(f"🛑 Userbot stopped for ID: {user_id}")
                return f"🛑 **Userbot Stopped:** Module **{module}** has been terminated safely."
            except Exception as e:
                log.error(f"Stop Error for {user_id}: {e}")
                return f"❌ **Error while stopping:** `{e}`"
        
        return "⚠️ Your userbot is not currently running."
