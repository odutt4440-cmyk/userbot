import asyncio
from bot_instance import bot 
from telethon import events, Button
from core.session_manager import SessionManager
from config import ADMIN_ID
from database import is_subscribed, global_security_check, get_user_plan_type

# --- HELPER: GET CLEAN MODULE NAME ---
def get_clean_name(data_bytes):
    """Callback data se prefixes saaf karke asli module name nikalne ke liye"""
    data = data_bytes.decode("utf-8")
    return data.replace("activate_", "").replace("force_start_", "").replace("stop_", "").replace("start_ub_", "")

# --- 1. MAIN ACTIVATION HANDLER ---
@bot.on(events.CallbackQuery(pattern=r"activate_"))
async def activate_module(event):
    if not event.is_private:
        await event.answer("⚠️ Action allowed in Private DM only.", alert=True)
        return
    
    if not await global_security_check(event):
        return

    user_id = event.sender_id
    # 🔥 FIX: Clean name extraction
    module_name = get_clean_name(event.data)
    
    if not await is_subscribed(user_id):
        await event.edit(
            "⚠️ **Premium Access Required**\n\nYour subscription has expired. Please select a plan to continue.",
            buttons=[
                [Button.inline("💳 View Plans", data="pay_now")],
                [Button.inline("🎁 Claim Trial", data="claim_trial_btn")],
                [Button.inline("🔙 Back", data="modules_main")]
            ]
        )
        return

    await event.edit(f"⏳ **Deploying `{module_name.upper()}`...**\nInitializing handlers on your account.")

    # Core Engine call (Selective Loading handles the rest)
    result_message = await SessionManager.start_userbot(user_id, module_name)

    if "Activated" in result_message:
        buttons = [[Button.inline(f"🛑 Stop {module_name.upper()}", data=f"stop_{module_name}")]]
    elif "Access Denied" in result_message:
        # Standard user switching logic
        buttons = [
            [Button.inline("🛑 Stop Current & Start This", data=f"force_start_{module_name}")],
            [Button.inline("💎 Upgrade to Empire", data="pay_now")],
            [Button.inline("🔙 Back", data="modules_main")]
        ]
    else:
        buttons = [[Button.inline("🔙 Back to Modules", data="modules_main")]]

    await event.edit(result_message, buttons=buttons)

# --- 2. STOP HANDLER ---
@bot.on(events.CallbackQuery(pattern=r"stop_"))
async def stop_module(event):
    if not event.is_private: return
    user_id = event.sender_id
    module_name = get_clean_name(event.data)

    result = await SessionManager.stop_userbot(user_id)
    await event.edit(
        f"{result}\n\nModule `{module_name.upper()}` is now offline.",
        buttons=[[Button.inline("🚀 Restart", data=f"activate_{module_name}"), Button.inline("🔙 Menu", data="start_back")]]
    )

# --- 3. FORCE START (Standard Users Switching) ---
@bot.on(events.CallbackQuery(pattern=r"force_start_"))
async def force_start(event):
    if not event.is_private: return
    user_id = event.sender_id
    
    # 1. Stop the current active bot
    await SessionManager.stop_userbot(user_id)
    # 2. Wait 1 second for cleanup
    await asyncio.sleep(1)
    # 3. Trigger fresh activation for the new module
    await activate_module(event)

# --- 4. RE-STARTING EXISTING SESSIONS ---
@bot.on(events.CallbackQuery(pattern=r"start_ub_"))
async def restart_existing(event):
    if not event.is_private: return
    await activate_module(event)

# --- 5. EMPIRE ALL MODULES HANDLER ---
@bot.on(events.CallbackQuery(data="activate_all"))
async def activate_all_handler(event):
    if not event.is_private: return
    if not await global_security_check(event): return

    user_id = event.sender_id
    plan = await get_user_plan_type(user_id)
    current_plan = str(plan).strip().lower()

    if user_id != ADMIN_ID and "empire" not in current_plan:
        return await event.answer("❌ Access Denied! Upgrade to Empire Plan to run all bots together.", alert=True)

    await event.edit("⏳ **Turbo Deploying Empire Mode...**\nInjecting all solvers to your account.")

    # Send 'All Modules' trigger to engine
    result_message = await SessionManager.start_userbot(user_id, "All Modules")

    if "Activated" in result_message or "Active" in result_message:
        buttons = [[Button.inline("🛑 Stop All Sessions", data="stop_all_modules")]]
    else:
        buttons = [[Button.inline("🔙 Back", data="modules_main")]]

    await event.edit(result_message, buttons=buttons)

@bot.on(events.CallbackQuery(data="stop_all_modules"))
async def stop_all_callback(event):
    await stop_module(event)
