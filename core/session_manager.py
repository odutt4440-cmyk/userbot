import logging
import asyncio
import gc
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from config import API_ID, API_HASH, ADMIN_ID
from database import get_user_session, is_subscribed, get_user_plan_type, set_bot_status
from core.plugin_loader import load_all_modules
from bot_instance import bot # Manager Bot instance for DMs

log = logging.getLogger(__name__)

ACTIVE_CLIENTS = {}
USER_LOCKS = {}

# 🔥 Persistent Modules: Inhe kabhi hibernate mat karna (24/7 required)
PERSISTENT_MODULES = ["afk", "stealth", "reaction", "fun_pack", "management_pack"]
IDLE_TIMEOUT = 7200 # 2 Hours of total silence

class SessionManager:
    @staticmethod
    async def start_userbot(user_id, module_name):
        """Starts userbot with Instance Locking & Smart Hibernation."""
        if user_id not in USER_LOCKS:
            USER_LOCKS[user_id] = asyncio.Lock()
        
        async with USER_LOCKS[user_id]:
            # 🛡️ Security Check
            if not await is_subscribed(user_id):
                return "❌ Your subscription has expired."

            plan = await get_user_plan_type(user_id)
            trigger = str(module_name).strip().lower()

            # 🛠️ HARD CLEANUP: Stop existing ghost sessions
            if user_id in ACTIVE_CLIENTS:
                try:
                    old = ACTIVE_CLIENTS[user_id]
                    await old["client"].disconnect()
                    if old["task"]: old["task"].cancel()
                    if old["monitor"]: old["monitor"].cancel()
                except: pass
                del ACTIVE_CLIENTS[user_id]
                gc.collect()

            # 🚀 Session Fetch
            string_session = await get_user_session(user_id)
            if not string_session: return "❌ No session string found."

            client = TelegramClient(
                StringSession(string_session), API_ID, API_HASH,
                sequential_updates=True,
                flood_sleep_threshold=60,
                device_model="Empire-SaaS v3"
            )

            try:
                await asyncio.wait_for(client.connect(), timeout=30)
                if not await client.is_user_authorized():
                    return "❌ Session invalid. Please relogin."

                client._event_builders.clear()
                
                # Load Plugins
                await load_all_modules(client, target_module=trigger)
                
                # Background Task
                task = client.loop.create_task(client.run_until_disconnected())
                
                # Register in Memory
                ACTIVE_CLIENTS[user_id] = {
                    "client": client,
                    "module": trigger,
                    "task": task,
                    "last_activity": datetime.now(),
                    "monitor": None
                }

                # 🔥 Start Hibernate Monitor only for Non-Persistent modules
                if not any(m in trigger for m in PERSISTENT_MODULES):
                    ACTIVE_CLIENTS[user_id]["monitor"] = client.loop.create_task(
                        SessionManager.hibernate_monitor(user_id)
                    )

                # Activity Tracker: Reset timer on every command
                @client.on(events.NewMessage(outgoing=True))
                async def update_activity(event):
                    if user_id in ACTIVE_CLIENTS:
                        ACTIVE_CLIENTS[user_id]["last_activity"] = datetime.now()

                await set_bot_status(user_id, True, trigger.upper())
                log.info(f"🚀 Bot Deployed: {user_id} | Module: {trigger}")
                
                return f"🚀 **Userbot Online!**\n📦 **Module:** `{trigger.upper()}`"

            except Exception as e:
                log.error(f"Startup Error: {e}")
                return f"❌ **Error:** {str(e)}"

    @staticmethod
    async def hibernate_monitor(user_id):
        """Monitors inactivity and sends a DM from Official Bot before stopping."""
        while user_id in ACTIVE_CLIENTS:
            await asyncio.sleep(600) # Check every 10 mins
            data = ACTIVE_CLIENTS.get(user_id)
            if not data: break
            
            idle_duration = (datetime.now() - data["last_activity"]).total_seconds()
            
            if idle_duration > IDLE_TIMEOUT:
                log.info(f"😴 Hibernating idle bot: {user_id}")
                
                # 🛑 Stop the bot
                await SessionManager.stop_userbot(user_id)
                
                # 📩 Send Professional Notification from Official Bot
                try:
                    notification = (
                        "😴 **Hibernation Mode Activated**\n\n"
                        "Hello! Your userbot session has been **paused** due to 2 hours of inactivity. "
                        "This automated process keeps our servers fast and optimized for everyone.\n\n"
                        "⚡ **Ready to wake up?**\n"
                        "Simply go to the /modules menu and redeploy your session."
                    )
                    await bot.send_message(user_id, notification)
                except Exception as e:
                    log.error(f"Could not send Hibernate DM: {e}")
                break

    @staticmethod
    async def stop_userbot(user_id):
        """Kills session and purges RAM."""
        if user_id in ACTIVE_CLIENTS:
            try:
                data = ACTIVE_CLIENTS[user_id]
                await data["client"].disconnect()
                if data["task"]: data["task"].cancel()
                if data["monitor"]: data["monitor"].cancel()
                
                await set_bot_status(user_id, False, None)
                del ACTIVE_CLIENTS[user_id]
                gc.collect()
                return "🛑 **Stopped & Memory Purged.**"
            except: pass
        return "⚠️ Not running."
