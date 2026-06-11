import logging
import os
import glob
import importlib
import asyncio
import shutil 
import datetime
from telethon import functions, types
from config import API_ID, API_HASH, BOT_TOKEN, LOG_GROUP, ADMIN_ID, BACKUP_CHAT
from bot_instance import bot 
from database import init_db 

# 1. Logging Setup
logging.basicConfig(
    format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
    level=logging.INFO
)
log = logging.getLogger(__name__)

# --- 2. AUTO-BACKUP TASK (Modified for Cloud) ---
async def auto_backup_task():
    """Cloud storage me file backup ki zarurat nahi hoti, ye sirf placeholder hai crash rokne ke liye"""
    while True:
        await asyncio.sleep(21600) 
        # Agar tu koi aur file backup karna chahe toh yahan logic daal sakta hai
        log.info("☁️ Cloud Database is automatically backed up by MongoDB Atlas.")

# 3. Plugin Loader Function
def load_plugins():
    path = "plugins/*.py"
    files = glob.glob(path)
    for name in files:
        if name.endswith("__init__.py"):
            continue
        plugin_name = os.path.basename(name).replace(".py", "")
        try:
            importlib.import_module(f"plugins.{plugin_name}")
            log.info(f"Successfully loaded plugin: {plugin_name}")
        except Exception as e:
            log.error(f"Failed to load plugin {plugin_name}: {e}")

async def start_bot():
    print("---------------------------------------")
    print("   Userbot Community Bot Starting...   ")
    print("---------------------------------------")
    
    # STEP 1: INITIALIZE DATABASE (Now connects to MongoDB Cloud)
    await init_db()
    log.info("MongoDB Cloud Database connected.")

    # STEP 2: START BOT
    await bot.start(bot_token=BOT_TOKEN)

    # --- SET BOT COMMANDS VIA CODE ---
    try:
        await bot(functions.bots.SetBotCommandsRequest(
            scope=types.BotCommandScopeDefault(),
            lang_code='en',
            commands=[
                types.BotCommand(command='start', description='Open main menu'),
                types.BotCommand(command='modules', description='Explore all userbot tools'),
                types.BotCommand(command='plan', description='View premium pricing plans'),
                types.BotCommand(command='me', description='Check your profile and expiry'),
                types.BotCommand(command='help', description='Empire community guide')
            ]
        ))
        log.info("Successfully synced bot commands to Telegram.")
    except Exception as e:
        log.error(f"Failed to sync commands: {e}")

    # --- 📢 LOG LAYER 1: MAIN ACTIVITY GROUP ---
    if LOG_GROUP:
        try:
            await bot.send_message(
                LOG_GROUP, 
                "🚀 **Userbot Community Bot is Online!**\n\n"
                "• Database: `MongoDB (Cloud)`\n"
                "• Status: `Active & Secure`"
            )
        except Exception as e:
            log.error(f"Activity Log failed: {e}")

    # --- 📂 LOG LAYER 2: DEDICATED BACKUP GROUP ---
    if BACKUP_CHAT:
        try:
            await bot.send_message(
                BACKUP_CHAT, 
                "☁️ **Cloud Storage System Connected!**\n\n"
                "• Status: `Online`\n"
                "• Protection: `MongoDB Atlas Sync`"
            )
        except Exception as e:
            log.error(f"Backup Log failed: {e}")
    
    # STEP 3: LOAD PLUGINS
    load_plugins()

    # STEP 4: TRIGGER BACKUP TASK
    asyncio.create_task(auto_backup_task())
    
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
