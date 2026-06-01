import logging
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH
from database import get_user_session, is_subscribed
from core.plugin_loader import load_all_modules

log = logging.getLogger(__name__)

# Dictionary to keep track of running userbots: {user_id: client_instance}
ACTIVE_CLIENTS = {}

class SessionManager:
    @staticmethod
    async def start_userbot(user_id, module_name):
        """Starts a userbot session with fresh registration and cleanup."""
        
        # 1. Security Check: Subscription status
        if not await is_subscribed(user_id):
            return "❌ Your subscription has expired. Please pay ₹10 to reactivate."

        # 2. Get string session from SQLite
        string_session = await get_user_session(user_id)
        if not string_session:
            return "❌ No session found. Please generate one first."

        # 3. SMOOTH SWITCHING / AUTO-CLEANUP
        # Agar user pehle se koi bot chala raha hai, toh use refresh karna zaroori hai
        if user_id in ACTIVE_CLIENTS:
            log.info(f"🔄 Refreshing session for user {user_id}...")
            try:
                old_client = ACTIVE_CLIENTS[user_id]
                await old_client.disconnect()
                # 1 second ka gap taaki system handlers ko clean kar sake
                await asyncio.sleep(1)
                del ACTIVE_CLIENTS[user_id]
            except Exception as e:
                log.error(f"Error during cleanup: {e}")

        # 4. Initialize Fresh Telegram Client
        client = TelegramClient(
            StringSession(string_session), 
            API_ID, 
            API_HASH,
            sequential_updates=True
        )

        try:
            await client.connect()
            if not await client.is_user_authorized():
                return "❌ Invalid Session! Your string has been revoked. Please generate a new one."

            # 5. FRESH PLUGIN REGISTRATION
            # Isse WordChain ke 'Saved Messages' wale handlers properly register honge
            await load_all_modules(client)

            # Store the active client
            ACTIVE_CLIENTS[user_id] = client
            
            # Start background execution
            client.loop.create_task(client.run_until_disconnected())
            
            log.info(f"🚀 Userbot started for {user_id} with module: {module_name}")
            
            return (
                f"🚀 **Userbot Activated!**\n\n"
                f"**Active Module:** `{module_name.upper()}`\n"
                f"**Status:** `Online`\n\n"
                "You can now use your userbot commands in any chat. "
                "For WordChain, check your 'Saved Messages' for the setup button."
            )

        except Exception as e:
            log.error(f"Startup Error for {user_id}: {e}")
            return f"❌ **Startup Error:** `{str(e)}`"

    @staticmethod
    async def stop_userbot(user_id):
        """Cleanly disconnects the session."""
        if user_id in ACTIVE_CLIENTS:
            try:
                client = ACTIVE_CLIENTS[user_id]
                await client.disconnect()
                del ACTIVE_CLIENTS[user_id]
                log.info(f"🛑 Userbot stopped for ID: {user_id}")
                return "🛑 **Userbot Stopped Successfully.**"
            except Exception as e:
                log.error(f"Stop Error for {user_id}: {e}")
                return f"❌ **Error while stopping:** `{e}`"
        
        return "⚠️ Your userbot is not currently running."
