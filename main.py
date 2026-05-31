import logging
import os
import glob
import importlib.util
import asyncio
from telethon import TelegramClient, functions, types # added functions/types for commands
from config import API_ID, API_HASH, BOT_TOKEN, LOG_GROUP

# 1. Logging Setup
logging.basicConfig(
    format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
    level=logging.INFO
)
log = logging.getLogger(__name__)

# 2. Bot Client Initialize
bot = TelegramClient('bot_session', API_ID, API_HASH)

# 3. Plugin Loader Function
def load_plugins():
    path = "plugins/*.py"
    files = glob.glob(path)
    for name in files:
        if name.endswith("__init__.py"):
            continue
            
        plugin_name = os.path.basename(name).replace(".py", "")
        spec = importlib.util.spec_from_file_location(f"plugins.{plugin_name}", name)
        module = importlib.util.module_from_spec(spec)
        # Is tarah load karne se @bot.on sahi se register hote hain
        spec.loader.exec_module(module)
        log.info(f"Successfully loaded plugin: {plugin_name}")

async def start_bot():
    print("---------------------------------------")
    print("   Userbot Community Bot Starting...   ")
    print("---------------------------------------")
    
    # Bot Start
    await bot.start(bot_token=BOT_TOKEN)

    # --- SET BOT COMMANDS VIA CODE ---
    try:
        await bot(functions.bots.SetBotCommandsRequest(
            scope=types.BotCommandScopeDefault(),
            lang_code='en',
            commands=[
                types.BotCommand(command='start', description='Start the bot and see menu'),
                types.BotCommand(command='help', description='Rules and Help info'),
                types.BotCommand(command='modules', description='Explore userbot modules')
            ]
        ))
        log.info("Successfully synced bot commands to Telegram.")
    except Exception as e:
        log.error(f"Failed to sync commands: {e}")

    # --- LOGGER PART START ---
    if LOG_GROUP:
        try:
            await bot.send_message(LOG_GROUP, "🚀 **Userbot Community Bot Started Successfully!**\n\nAll plugins are loaded and the engine is ready.")
        except Exception as e:
            log.error(f"Failed to send startup log: {e}")
    # --- LOGGER PART END ---
    
    # Load plugins after bot is fully started
    load_plugins()
    
    print("---------------------------------------")
    print("   Bot is now Online and Ready!        ")
    print("---------------------------------------")
    
    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_bot())
    except KeyboardInterrupt:
        pass
