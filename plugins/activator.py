from bot_instance import bot 
from telethon import events, Button
from core.session_manager import SessionManager
from config import ADMIN_ID # <--- Ye missing tha
from database import is_subscribed, global_security_check, get_user_plan_type # <--- Ye bhi add kiya

# --- 1. HANDLE MODULE ACTIVATION ---
@bot.on(events.CallbackQuery(pattern=r"activate_"))
async def activate_module(event):
    if not event.is_private:
        await event.answer("⚠️ This action is only allowed in Private DM.", alert=True)
        return
    
    if not await global_security_check(event):
        return

    user_id = event.sender_id
    module_name = event.data.decode("utf-8").replace("activate_", "")
    
    if not await is_subscribed(user_id):
        await event.edit(
            "⚠️ **Premium Access Required**\n\n"
            "Your subscription has expired or is not yet active. "
            "Please select a plan to continue.",
            buttons=[
                [Button.inline("💳 View Premium Plans", data="pay_now")],
                [Button.inline("🎁 Claim Free Trial", data="claim_trial_btn")],
                [Button.inline("🔙 Back", data="modules_main")]
            ]
        )
        return

    await event.edit(
        f"⏳ **Deploying `{module_name.upper()}`...**\n"
        "Connecting to Telegram servers and injecting handlers."
    )

    result_message = await SessionManager.start_userbot(user_id, module_name)

    if "Activated" in result_message:
        buttons = [[Button.inline("🛑 Stop Userbot", data=f"stop_{module_name}")]]
        
    elif "Access Denied" in result_message:
        buttons = [
            [Button.inline("🛑 Stop Current & Start This", data=f"force_start_{module_name}")],
            [Button.inline("💎 Upgrade to Empire", data="pay_now")],
            [Button.inline("🔙 Back", data="modules_main")]
        ]
    else:
        buttons = [[Button.inline("🔙 Back to Modules", data="modules_main")]]

    await event.edit(result_message, buttons=buttons)

# --- 2. HANDLE STOPPING THE USERBOT ---
@bot.on(events.CallbackQuery(pattern=r"stop_"))
async def stop_module(event):
    if not event.is_private: return
    if not await global_security_check(event): return

    user_id = event.sender_id
    module_name = event.data.decode("utf-8").replace("stop_", "")

    result = await SessionManager.stop_userbot(user_id)
    
    await event.edit(
        f"{result}\n\nYour userbot session has been terminated.",
        buttons=[
            [Button.inline("🚀 Restart Engine", data=f"activate_{module_name}")],
            [Button.inline("🔙 Main Menu", data="start_back")]
        ]
    )

# --- 3. FORCE START FOR STANDARD USERS ---
@bot.on(events.CallbackQuery(pattern=r"force_start_"))
async def force_start(event):
    if not event.is_private: return
    user_id = event.sender_id
    module_name = event.data.decode("utf-8").replace("force_start_", "")
    
    await SessionManager.stop_userbot(user_id)
    await activate_module(event)

# --- 4. RE-STARTING ALREADY LOGGED IN USERS ---
@bot.on(events.CallbackQuery(pattern=r"start_ub_"))
async def restart_existing(event):
    if not event.is_private: return
    module_name = event.data.decode("utf-8").replace("start_ub_", "")
    await activate_module(event)

# --- 5. ACTIVATE ALL MODULES (Strict Empire Check) ---
@bot.on(events.CallbackQuery(data="activate_all"))
async def activate_all_handler(event):
    if not event.is_private: return
    if not await global_security_check(event): return

    user_id = event.sender_id
    plan = await get_user_plan_type(user_id)
    
    # Plan name ko saaf karke check karenge (No spaces, No case issues)
    current_plan = str(plan).strip().lower()

    # 🛡️ THE WALL: Agar owner nahi hai AUR plan "empire" nahi hai...
    if user_id != ADMIN_ID and "empire" not in current_plan:
        return await event.answer(
            "⚠️ Access Denied: Empire Plan Required\n\n"
            "Standard users can only deploy one module at a time. "
            "Please use individual buttons to start a bot.", 
            alert=True
        )

    # ✅ Permission Granted (Empire or Admin)
    await event.edit("⏳ **Turbo Deploying Empire Mode...**")
    result_message = await SessionManager.start_userbot(user_id, "All Modules")
    
    buttons = [[Button.inline("🛑 Stop All Sessions", data="stop_all_modules")]]
    await event.edit(result_message, buttons=buttons)

# Callback to stop all
@bot.on(events.CallbackQuery(data="stop_all_modules"))
async def stop_all_callback(event):
    await stop_module(event)
