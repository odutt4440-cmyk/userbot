import asyncio
from bot_instance import bot 
from telethon import events, Button
from core.session_manager import SessionManager
from config import ADMIN_ID
from database import is_subscribed, global_security_check, get_user_plan_type

# 🔥 KEY MAPPING: Buttons (mod_...) aur Backend names ko sync karne ke liye
NAME_MAP = {
    "info": "info_tools",
    "info_tools": "info_tools",
    "group": "group_tools",
    "admin": "group_tools",
    "management": "group_tools",
    "group_tools": "group_tools",
    "stickers": "stickers",      # Naya
    "reaction": "reaction",      # Naya
    "stealth": "stealth",        # Naya
    "clone": "clone",
    "afk": "afk",
    "tagger": "tagger"
}

def get_clean_name(data_bytes):
    """Callback data se saare prefixes saaf karne ke liye"""
    data = data_bytes.decode("utf-8")
    
    # Saare possible prefixes ko remove karo
    name = data.replace("activate_", "").replace("force_start_", "").replace("stop_", "").replace("start_ub_", "").replace("mod_", "")
    
    # Mapping se final backend name uthao, agar mapping me nahi hai toh wahi return karo
    return NAME_MAP.get(name, name)

# 🔥 UPDATE: Pattern me (activate_|mod_) dono rakha hai taaki start.py ke buttons kaam karein
@bot.on(events.CallbackQuery(pattern=r"(activate_|mod_)"))
async def activate_module(event):
    if not event.is_private:
        await event.answer("⚠️ Action allowed in Private DM only.", alert=True)
        return
    
    if not await global_security_check(event): return

    user_id = event.sender_id
    module_name = get_clean_name(event.data)
    
    # Subscription Check
    if not await is_subscribed(user_id):
        await event.edit(
            "⚠️ **Premium Access Required**", 
            buttons=[
                [Button.inline("💳 View Plans", data="pay_now")], 
                [Button.inline("🎁 Claim Trial", data="claim_trial_btn")]
            ]
        )
        return

    await event.edit(f"⏳ **Deploying `{module_name.upper()}`...**")
    
    # Backend Session Manager call
    result_message = await SessionManager.start_userbot(user_id, module_name)

    if "Activated" in result_message:
        buttons = [[Button.inline(f"🛑 Stop {module_name.upper()}", data=f"stop_{module_name}")]]
    elif "Access Denied" in result_message:
        # Standard users ke liye: Stop current and start this
        buttons = [
            [Button.inline("🛑 Stop Current & Start This", data=f"force_start_{module_name}")], 
            [Button.inline("💎 Upgrade to Empire", data="pay_now")]
        ]
    else:
        buttons = [[Button.inline("🔙 Back", data="modules_main")]]
        
    await event.edit(result_message, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=r"stop_"))
async def stop_module(event):
    if not event.is_private: return
    user_id = event.sender_id
    module_name = get_clean_name(event.data)
    
    result = await SessionManager.stop_userbot(user_id)
    
    await event.edit(
        f"{result}", 
        buttons=[
            [Button.inline("🚀 Restart", data=f"activate_{module_name}"), 
             Button.inline("🔙 Menu", data="start_back")]
        ]
    )

@bot.on(events.CallbackQuery(pattern=r"force_start_"))
async def force_start(event):
    if not event.is_private: return
    user_id = event.sender_id
    # Pehle purana bot stop karo
    await SessionManager.stop_userbot(user_id)
    await asyncio.sleep(1.5)
    # Phir naya start karo
    await activate_module(event)

@bot.on(events.CallbackQuery(pattern=r"start_ub_"))
async def restart_existing(event):
    await activate_module(event)

# --- EMPIRE DEPLOY LOGIC ---
@bot.on(events.CallbackQuery(data="activate_all"))
async def activate_all_handler(event):
    if not event.is_private: return
    if not await global_security_check(event): return
    
    user_id = event.sender_id
    plan = await get_user_plan_type(user_id)
    
    # Empire Plan Check
    if user_id != ADMIN_ID and "empire" not in str(plan).lower():
        return await event.answer("❌ Empire Plan Required for Turbo Deploy!", alert=True)

    await event.edit("⏳ **Turbo Deploying Empire Mode (All Modules)...**")
    
    # Backend call with "All Modules" flag
    result_message = await SessionManager.start_userbot(user_id, "All Modules")
    
    await event.edit(result_message, buttons=[[Button.inline("🛑 Stop All", data="stop_all_modules")]])

@bot.on(events.CallbackQuery(data="stop_all_modules"))
async def stop_all_callback(event):
    await stop_module(event)
