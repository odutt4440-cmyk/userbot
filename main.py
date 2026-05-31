import logging
import os
import glob
import importlib.util
from telethon import TelegramClient
from config import API_ID, API_HASH, BOT_TOKEN

# 1. Logging Setup
logging.basicConfig(
    format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
    level=logging.INFO
)
log = logging.getLogger(__name__)

# 2. Bot Client Initialize (Sirf object create kiya hai, start nahi)
bot = TelegramClient('bot_session', API_ID, API_HASH)

# 3. Plugin Loader Function
def load_plugins():
    path = "plugins/*.py"
    files = glob.glob(path)
    for name in files:
        # __init__.py ko skip karne ke liye
        if name.endswith("__init__.py"):
            continue
            
        plugin_name = os.path.basename(name).replace(".py", "")
        # Plugin ko properly import karne ka naya tareeka
        spec = importlib.util.spec_from_file_location(f"plugins.{plugin_name}", name)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        log.info(f"Successfully loaded plugin: {plugin_name}")

async def start_bot():
    print("---------------------------------------")
    print("   Userbot Community Bot Starting...   ")
    print("---------------------------------------")
    
    # Bot ko yahan properly start karenge
    await bot.start(bot_token=BOT_TOKEN)
    
    # Plugins ko start hone ke BAAD load karenge
    load_plugins()
    
    print("---------------------------------------")
    print("   Bot is now Online and Ready!        ")
    print("---------------------------------------")
    
    await bot.run_until_disconnected()

if __name__ == "__main__":
    import asyncio
    # Naye python versions ke liye loop handle karne ka tareeka
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_bot())
    except KeyboardInterrupt:
        pass
