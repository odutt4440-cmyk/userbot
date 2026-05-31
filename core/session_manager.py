import logging
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH
from database import get_user_session, is_subscribed
from core.plugin_loader import load_all_modules  # <--- New Import

# Logger setup
log = logging.getLogger(__name__)

# Dictionary to keep track of running userbots: {user_id: client_instance}
ACTIVE_CLIENTS = {}

class SessionManager:
    @staticmethod
    async def start_userbot(user_id, module_name):
        """Starts a userbot session and injects all available modules."""
        
        # 1. Security Check: Subscription status
        if not await is_subscribed(user_id):
            return "❌ Your subscription has expired. Please pay ₹10 to reactivate."

        # 2. Get string session from MongoDB
        string_session = await get_user_session(user_id)
        if not string_session:
            return "❌ No session found. Please login using the 'String Gen' button first."

        # 3. Prevent duplicate sessions
        if user_id in ACTIVE_CLIENTS:
            return "⚠️ Your userbot is already running! Stop it first if you want to restart."

        # 4. Initialize Telegram Client
        client = TelegramClient(
            StringSession(string_session), 
            API_ID, 
            API_HASH,
            sequential_updates=True
        )

        try:
            await client.connect()
            if not await client.is_user_authorized():
                return "❌ Invalid Session! Your string has expired or was revoked. Please relog."

            # 5. PLUGIN INJECTION
            # This will load Wordly, WordSeek, WordChain, and Octopus all at once
            await load_all_modules(client)

            # Store the client instance to manage it later
            ACTIVE_CLIENTS[user_id] = client
            
            # Run the client in a background task
            # Using create_task ensures the main bot doesn't freeze
            client.loop.create_task(client.run_until_disconnected())
            
            log.info(f"🚀 Userbot started for ID: {user_id} (Requested: {module_name})")
            
            return (
                f"🚀 **Userbot Activated Successfully!**\n\n"
                f"Active Module: `{module_name.upper()}`\n"
                f"Status: `Running`\n\n"
                f"You can now use your userbot commands in any chat."
            )

        except Exception as e:
            log.error(f"Error starting userbot for {user_id}: {e}")
            return f"❌ **Startup Error:** `{str(e)}`"

    @staticmethod
    async def stop_userbot(user_id):
        """Disconnects and removes a userbot session."""
        if user_id in ACTIVE_CLIENTS:
            client = ACTIVE_CLIENTS[user_id]
            try:
                await client.disconnect()
            except:
                pass
            del ACTIVE_CLIENTS[user_id]
            log.info(f"🛑 Userbot stopped for ID: {user_id}")
            return "🛑 **Userbot Stopped.** All modules have been disconnected."
        
        return "⚠️ Your userbot is not currently running."

# Note: The 'load_module' function was removed because 'load_all_modules' 
# from plugin_loader now handles everything more efficiently.
