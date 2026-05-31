import logging
import os
import glob
import importlib
import asyncio
from telethon import functions, types
from config import API_ID, API_HASH, BOT_TOKEN, LOG_GROUP
from bot_instance import bot # <--- Bot ab yahan se aayega

# 1. Logging Setup
logging.basicConfig(
    format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
    level=logging.INFO
)
log = logging.getLogger(__name__)

# 2. Plugin Loader Function
def load_plugins():
    path = "plugins/*.py"
    files = glob.glob(path)
    for name in files:
        if name.endswith("__init__.py"):
            continue
            
        # Proper way to import modules so that decorators (@bot.on) work
        plugin_name = os.path.basename(name).replace(".py", "")
        importlib.import_module(f"plugins.{plugin_name}")
        log.info(f"Successfully loaded plugin: {plugin_name}")

async def start_bot():
    print("---------------------------------------")
    print("   Userbot Community Bot Starting...   ")
    print("---------------------------------------")
    
    # Bot Start using the instance from bot_instance.py
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
