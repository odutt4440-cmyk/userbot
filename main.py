import logging
import os
import glob
import importlib
from telethon import TelegramClient
from config import API_ID, API_HASH, BOT_TOKEN

# 1. Logging Setup (Taaki errors console mein dikhen)
logging.basicConfig(
    format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
    level=logging.INFO
)
log = logging.getLogger(__name__)

# 2. Bot Client Initialize
# BotFather wala bot session 'bot_session' naam se save hoga
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# 3. Plugin Loader Function
# Ye function 'plugins' folder ke andar ki saari .py files ko automatic load karega
def load_plugins():
    path = "plugins/*.py"
    files = glob.glob(path)
    for name in files:
        # File ka path nikal kar use import karna
        module_spec = importlib.util.spec_from_file_location(
            name.replace("/", ".").replace("\\", ".").replace(".py", ""), 
            name
        )
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        log.info(f"Successfully loaded plugin: {os.path.basename(name)}")

async def start_bot():
    print("---------------------------------------")
    print("   Userbot Community Bot Started!     ")
    print("---------------------------------------")
    
    # Plugins load karna shuru
    load_plugins()
    
    # Bot ko tab tak chalne dena jab tak koi band na kare
    await bot.run_until_disconnected()

if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_bot())
