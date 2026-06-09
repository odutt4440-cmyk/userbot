import logging
import os
import glob
import importlib
import asyncio
import shutil # File copy karne ke liye
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

# --- 2. SEPARATE AUTO-BACKUP TASK ---
async def auto_backup_task():
    """Har 6 ghante me database file ko safe jagah bhejega"""
    while True:
        # Wait for 6 hours
        await asyncio.sleep(21600) 
        
        if os.path.exists("community.db"):
            try:
                # 1. Temporary copy banao
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_name = f"backup_{timestamp}.db"
                shutil.copy("community.db", backup_name)
                
                caption = (
                    "📂 **Empire SaaS: Security Backup**\n"
                    f"📅 **Date:** `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}`\n\n"
                    "Ye file aapka pura data hold karti hai. VPS change karte waqt ise use karein."
                )
                
                # --- SEND TO ADMIN DM (Safety Layer 1) ---
                await bot.send_file(ADMIN_ID, backup_name, caption=caption + "\n🔰 Mode: `Private Admin Backup`")
                
                # --- SEND TO BACKUP CHAT (Safety Layer 2) ---
                if BACKUP_CHAT != 0:
                    await bot.send_file(BACKUP_CHAT, backup_name, caption=caption + "\n📢 Mode: `Dedicated Storage Backup`")
                
                # Cleanup temporary file
                os.remove(backup_name)
                log.info(f"✅ Auto-Backup successful for {timestamp}")
                
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
                types.BotCommand(command='start', description='Start the bot and see menu'),
                types.BotCommand(command='help', description='Rules and Help info'),
                types.BotCommand(command='modules', description='Explore userbot modules')
            ]
        ))
    except: pass

    # --- MAIN LOG GC (Only Status/Activity) ---
    if LOG_GROUP:
        try:
            await bot.send_message(LOG_GROUP, "🚀 **Userbot Community Bot Started Successfully!**\n\nDatabase: `SQLite (Local)`\nStatus: `Running`\nBackup: `Enabled (Every 6h)`")
        except Exception as e:
            log.error(f"Failed to send startup log: {e}")
    
    # STEP 3: LOAD PLUGINS
    load_plugins()

    # 🔥 STEP 4: TRIGGER BACKUP IN BACKGROUND
    # Isse bot freeze nahi hoga, backup piche chalta rahega
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
