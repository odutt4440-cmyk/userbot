import asyncio
from bot_instance import bot 
from telethon import events, Button
from core.session_manager import SessionManager
from config import ADMIN_ID
from database import is_subscribed, global_security_check, get_user_plan_type

# 🔥 KEY MAPPING: Buttons aur Backend ke names ko sync karne ke liye
NAME_MAP = {
    "info": "info_tools",
    "group": "group_tools",
    "admin": "group_tools",
    "management": "group_tools"
}

def get_clean_name(data_bytes):
    data = data_bytes.decode("utf-8")
    name = data.replace("activate_", "").replace("force_start_", "").replace("stop_", "").replace("start_ub_", "")
    # Agar mapping me hai toh badlo, warna wahi rehne do
    return NAME_MAP.get(name, name)

@bot.on(events.CallbackQuery(pattern=r"activate_"))
async def activate_module(event):
    if not event.is_private:
        await event.answer("⚠️ Action allowed in Private DM only.", alert=True)
        return
    if not await global_security_check(event): return

    user_id = event.sender_id
    module_name = get_clean_name(event.data)
    
    if not await is_subscribed(user_id):
        await event.edit("⚠️ **Premium Access Required**", buttons=[[Button.inline("💳 View Plans", data="pay_now")], [Button.inline("🎁 Claim Trial", data="claim_trial_btn")]])
        return

    await event.edit(f"⏳ **Deploying `{module_name.upper()}`...**")
    result_message = await SessionManager.start_userbot(user_id, module_name)

    if "Activated" in result_message:
        buttons = [[Button.inline(f"🛑 Stop {module_name.upper()}", data=f"stop_{module_name}")]]
    elif "Access Denied" in result_message:
        buttons = [[Button.inline("🛑 Stop Current & Start This", data=f"force_start_{module_name}")], [Button.inline("💎 Upgrade", data="pay_now")]]
    else:
        buttons = [[Button.inline("🔙 Back", data="modules_main")]]
    await event.edit(result_message, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=r"stop_"))
async def stop_module(event):
    if not event.is_private: return
    user_id = event.sender_id
    module_name = get_clean_name(event.data)
    result = await SessionManager.stop_userbot(user_id)
    await event.edit(f"{result}", buttons=[[Button.inline("🚀 Restart", data=f"activate_{module_name}"), Button.inline("🔙 Menu", data="start_back")]])

@bot.on(events.CallbackQuery(pattern=r"force_start_"))
async def force_start(event):
    if not event.is_private: return
    user_id = event.sender_id
    await SessionManager.stop_userbot(user_id)
    await asyncio.sleep(1.5)
    await activate_module(event)

@bot.on(events.CallbackQuery(pattern=r"start_ub_"))
async def restart_existing(event):
    await activate_module(event)

@bot.on(events.CallbackQuery(data="activate_all"))
async def activate_all_handler(event):
    if not event.is_private: return
    if not await global_security_check(event): return
    user_id = event.sender_id
    plan = await get_user_plan_type(user_id)
    if user_id != ADMIN_ID and "empire" not in str(plan).lower():
        return await event.answer("❌ Empire Plan Required!", alert=True)

    await event.edit("⏳ **Turbo Deploying Empire Mode...**")
    result_message = await SessionManager.start_userbot(user_id, "All Modules")
    await event.edit(result_message, buttons=[[Button.inline("🛑 Stop All", data="stop_all_modules")]])

@bot.on(events.CallbackQuery(data="stop_all_modules"))
async def stop_all_callback(event):
    await stop_module(event)
