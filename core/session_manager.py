import logging
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH
from database import get_user_session, is_subscribed
from core.plugin_loader import load_all_modules

log = logging.getLogger(__name__)

# Dictionary to track active sessions
ACTIVE_CLIENTS = {}

class SessionManager:
    @staticmethod
    async def start_userbot(user_id, module_name):
        """Starts a userbot session with fresh registration."""
        
        # 1. Security Check
        if not await is_subscribed(user_id):
            return "❌ Your subscription has expired. Please pay ₹10 to reactivate."

        # 2. String Retrieval
        string_session = await get_user_session(user_id)
        if not string_session:
            return "❌ No session found. Please generate one first."

        # 3. AUTO-CLEANUP (Fix for Switching/Lag)
        # Agar user pehle se koi bot chala raha hai, toh use pehle disconnect karo
        if user_id in ACTIVE_CLIENTS:
            log.info(f"🔄 Restarting session for {user_id}...")
            try:
                old_client = ACTIVE_CLIENTS[user_id]
                await old_client.disconnect()
                del ACTIVE_CLIENTS[user_id]
            except: pass

        # 4. Initialize New Client
        client = TelegramClient(
            StringSession(string_session), 
            API_ID, 
            API_HASH,
            sequential_updates=True
        )

        try:
            await client.connect()
            if not await client.is_user_authorized():
                return "❌ Invalid Session! Please generate a new string."

            # 5. FRESH HANDLER REGISTRATION
            # Ab saare game modules (Wordly, WordChain etc.) fresh load honge
            await load_all_modules(client)

            ACTIVE_CLIENTS[user_id] = client
            
            # Start background execution
            client.loop.create_task(client.run_until_disconnected())
            
            log.info(f"🚀 Userbot started for {user_id} with module {module_name}")
            return (
                f"🚀 **Userbot Activated Successfully!**\n\n"
                f"**Active Module:** `{module_name.upper()}`\n"
                f"**Status:** `Online`\n\n"
                "Check your 'Saved Messages' if needed (for WordChain) or use commands in groups."
            )

        except Exception as e:
            log.error(f"Startup Error for {user_id}: {e}")
            return f"❌ **Error:** `{str(e)}`"

    @staticmethod
    async def stop_userbot(user_id):
        """Cleanly disconnects the session."""
        if user_id in ACTIVE_CLIENTS:
            client = ACTIVE_CLIENTS[user_id]
            try:
                await client.disconnect()
            except: pass
            del ACTIVE_CLIENTS[user_id]
            return "🛑 **Userbot Stopped Successfully.**"
        return "⚠️ Your userbot is not running."
