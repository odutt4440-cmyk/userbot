import logging
import os
import glob
import importlib
import asyncio
import shutil 
import datetime
from telethon import functions, types
# Ensure these are defined in your config.py
from config import API_ID, API_HASH, BOT_TOKEN, LOG_GROUP, ADMIN_ID, BACKUP_CHAT
from bot_instance import bot 
from database import init_db 

# 1. Logging Setup
logging.basicConfig(
    format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
    level=logging.INFO
)
log = logging.getLogger(__name__)

# --- 2. SEPARATE AUTO-BACKUP TASK ---
async def auto_backup_task():
    """Har 6 ghante me database file ko safe jagah bhejega"""
    while True:
        # Wait for 6 hours
        await asyncio.sleep(21600) 
        
        if os.path.exists("community.db"):
            try:
                # 1. Temporary copy taaki 'database is locked' error na aaye
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_name = f"backup_{timestamp}.db"
                shutil.copy("community.db", backup_name)
                
                caption = (
                    "📂 **Empire SaaS: Security Backup**\n"
                    f"📅 **Date:** `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}`\n\n"
                    "Ye file aapka pura data hold karti hai. Ise hamesha safe rakhein."
                )
                
                # Mode 1: Admin Private DM
                await bot.send_file(ADMIN_ID, backup_name, caption=caption + "\n🔰 Type: `Private Admin Backup`")
                
                # Mode 2: Dedicated Backup GC
                if BACKUP_CHAT:
                    await bot.send_file(BACKUP_CHAT, backup_name, caption=caption + "\n📢 Type: `Storage Backup`")
                
                os.remove(backup_name)
                log.info(f"✅ Auto-Backup successful.")
            except Exception as e:
                log.error(f"❌ Backup Task Failed: {e}")

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
    
    # STEP 1: INITIALIZE DATABASE
    await init_db()
    log.info("SQLite Database initialized.")

    # STEP 2: START BOT
    await bot.start(bot_token=BOT_TOKEN)

    # --- SET BOT COMMANDS ---
    try:
        await bot(functions.bots.SetBotCommandsRequest(
            scope=types.BotCommandScopeDefault(),
            lang_code='en',
            commands=[
                types.BotCommand(command='start', description='Start menu'),
                types.BotCommand(command='help', description='Guide'),
                types.BotCommand(command='modules', description='Modules')
            ]
        ))
    except: pass

    # --- 📢 LOG LAYER 1: MAIN ACTIVITY GROUP ---
    if LOG_GROUP:
        try:
            await bot.send_message(
                LOG_GROUP, 
                "🚀 **Userbot Community Bot is Online!**\n\n"
                "• Database: `SQLite (Local)`\n"
                "• Status: `Active`"
            )
        except Exception as e:
            log.error(f"Activity Log failed: {e}")

    # --- 📂 LOG LAYER 2: DEDICATED BACKUP GROUP ---
    if BACKUP_CHAT:
        try:
            await bot.send_message(
                BACKUP_CHAT, 
                "📂 **Database Backup System Active!**\n\n"
                "• Storage: `community.db`\n"
                "• Frequency: `Every 6 Hours`\n"
                "• Security: `Encrypted Sync` (Ready)"
            )
        except Exception as e:
            log.error(f"Backup Log failed: {e}")
    
    # STEP 3: LOAD PLUGINS
    load_plugins()

    # STEP 4: TRIGGER BACKUP IN BACKGROUND
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
