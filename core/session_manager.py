import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH
from database import get_user_session, is_subscribed

# Logger setup for the engine
log = logging.getLogger(__name__)

# Dictionary to keep track of running userbots: {user_id: client_instance}
ACTIVE_CLIENTS = {}

class SessionManager:
    @staticmethod
    async def start_userbot(user_id, module_name):
        """Starts a userbot for a specific user and loads a specific module."""
        
        # 1. Security Check: Is the user subscribed?
        if not await is_subscribed(user_id):
            return "❌ Your subscription has expired. Please pay ₹10 to reactivate."

        # 2. Get the string session from Database
        string_session = await get_user_session(user_id)
        if not string_session:
            return "❌ No session found. Please login first."

        # 3. Check if already running
        if user_id in ACTIVE_CLIENTS:
            return "⚠️ Your userbot is already running!"

        # 4. Initialize Userbot Client
        client = TelegramClient(
            StringSession(string_session), 
            API_ID, 
            API_HASH,
            sequential_updates=True
        )

        try:
            await client.connect()
            if not await client.is_user_authorized():
                return "❌ Invalid Session! Please generate a new string and relog."

            # 5. Module Injection Logic
            # This part will dynamically load the game logic into the client
            await SessionManager.load_module(client, module_name)

            # Store the active client
            ACTIVE_CLIENTS[user_id] = client
            
            # Start the client in the background
            client.loop.create_task(client.run_until_disconnected())
            
            log.info(f"Userbot started for ID: {user_id} with Module: {module_name}")
            return f"🚀 **Successfully Started!**\nModule `{module_name.capitalize()}` is now active on your account."

        except Exception as e:
            log.error(f"Error starting userbot for {user_id}: {e}")
            return f"❌ **Error:** {str(e)}"

    @staticmethod
    async def stop_userbot(user_id):
        """Stops the running userbot for a user."""
        if user_id in ACTIVE_CLIENTS:
            client = ACTIVE_CLIENTS[user_id]
            await client.disconnect()
            del ACTIVE_CLIENTS[user_id]
            return "🛑 **Userbot Stopped Successfully.**"
        return "⚠️ Your userbot is not running."

    @staticmethod
    async def load_module(client, module_name):
        """
        This is where the magic happens. 
        It will import the game logic and register it to the user's client.
        """
        try:
            # Example: if module_name is 'wordseek', it imports from modules.games.wordseek.wordseek
            module_path = f"modules.games.{module_name}.{module_name}"
            import importlib
            game_module = importlib.import_module(module_path)
            
            # Every game file must have a 'register' function
            game_module.register(client)
            
        except Exception as e:
            log.error(f"Failed to load module {module_name}: {e}")
