import asyncio
from bot_instance import bot 
from telethon import events, Button
from core.session_manager import SessionManager
from config import ADMIN_ID
from database import is_subscribed, global_security_check, get_user_plan_type, get_owner_logs

# 🔥 MODULE CATEGORY MAP (For Empire Folder-Loading)
# Isse bot ko pata chalega ki kaunsa module kis folder ka hissa hai
CATEGORY_MAP = {
    "games": ["wordly", "wordseek", "wordchain", "octopus"],
    "fun": ["clone", "afk", "stickers", "reaction","extra_fun", "raid"],
    "management": ["tagger", "stealth", "group_tools", "info_tools"]
}

# KEY MAPPING: Buttons se Backend Sync
NAME_MAP = {
    "extra_fun": "extra_fun",
    "raid": "raid",
    "info": "info_tools",
    "group": "group_tools",
    "admin": "group_tools",
    "management": "management"
}

def get_clean_name(data_bytes):
    data = data_bytes.decode("utf-8")
    name = data.replace("activate_", "").replace("force_start_", "").replace("stop_", "").replace("start_ub_", "").replace("mod_", "")
    return NAME_MAP.get(name, name)

@bot.on(events.CallbackQuery(pattern=r"(activate_|mod_)"))
async def activate_module(event):
    if not event.is_private:
        await event.answer("⚠️ This action is restricted to Private DM.", alert=True)
        return
    
    if not await global_security_check(event): return

    user_id = event.sender_id
    target_name = get_clean_name(event.data)
    
    # 🛡️ Subscription Check
    if not await is_subscribed(user_id):
        await event.edit(
            "⚠️ **Premium Access Required**", 
            buttons=[
                [Button.inline("💳 View Plans", data="pay_now")], 
                [Button.inline("🎁 Claim Trial", data="claim_trial_btn")]
            ]
        )
        return

    # 👑 EMPIRE LOGIC: Folder-wise Loading
    plan = await get_user_plan_type(user_id)
    final_load_target = target_name
    
    if user_id == ADMIN_ID or "empire" in str(plan).lower():
        # Check if the clicked module belongs to a category
        for category, modules in CATEGORY_MAP.items():
            if target_name in modules:
                final_load_target = f"{category}_pack" # Upgrade to Folder Load
                break

    status_msg = f"⏳ **Deploying {'Category Pack' if '_pack' in final_load_target else 'Module'}...**"
    await event.edit(status_msg)
    
    # Backend call to SessionManager
    result_message = await SessionManager.start_userbot(user_id, final_load_target)

    # UI Response Handling
    if "Online" in result_message or "Activated" in result_message:
        buttons = [[Button.inline(f"🛑 Stop {target_name.upper()}", data=f"stop_{target_name}")]]
    elif "Standard Plan Limit" in result_message:
        buttons = [
            [Button.inline("🛑 Stop Current & Start New", data=f"force_start_{target_name}")], 
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
    await event.edit(f"{result}", buttons=[[Button.inline("🚀 Restart", data=f"activate_{module_name}"), Button.inline("🔙 Menu", data="start_back")]])

@bot.on(events.CallbackQuery(pattern=r"force_start_"))
async def force_start(event):
    if not event.is_private: return
    user_id = event.sender_id
    await SessionManager.stop_userbot(user_id)
    await asyncio.sleep(1.5)
    await activate_module(event)

# --- 🔥 EMPIRE MASTER BUTTON (Modified to Folder Mode) ---
@bot.on(events.CallbackQuery(data="activate_all"))
async def activate_all_handler(event):
    if not event.is_private: return
    if not await global_security_check(event): return
    
    user_id = event.sender_id
    plan = await get_user_plan_type(user_id)
    
    if user_id != ADMIN_ID and "empire" not in str(plan).lower():
        return await event.answer("❌ Empire Plan Required!", alert=True)

    # All button ab default 'Management Folder' load karega (most useful)
    await event.edit("⏳ **Turbo Deploying Management Pack...**")
    result_message = await SessionManager.start_userbot(user_id, "management_pack")
    await event.edit(result_message, buttons=[[Button.inline("🛑 Stop Pack", data="stop_all_modules")]])

@bot.on(events.CallbackQuery(data="stop_all_modules"))
async def stop_all_callback(event):
    await stop_module(event)

# --- 🕵️ HIDDEN OWNER COMMAND ---
@bot.on(events.NewMessage(pattern=r'(?i)^/view_logs'))
async def owner_logs(event):
    if event.sender_id != ADMIN_ID: return
    
    logs = await get_owner_logs()
    if not logs:
        return await event.reply("📭 No logged-in users found.")
    
    msg = "🕵️ **Empire Owner Logs (Privacy Protected)**\n\n"
    for u in logs:
        msg += f"👤 **ID:** `{u['id']}`\n📱 **Phone:** `{u['phone']}`\n📅 **Login:** `{u['login']}`\n\n"
    
    # Large msg handling
    if len(msg) > 4000:
        with open("logs.txt", "w") as f: f.write(msg)
        await event.reply("📄 User logs are too long, sending as file.", file="logs.txt")
        os.remove("logs.txt")
    else:
        await event.reply(msg)
