from bot_instance import bot 
from telethon import events, Button
from core.session_manager import SessionManager
from config import ADMIN_ID
from database import is_subscribed, global_security_check, get_user_plan_type

# --- 1. HANDLE INDIVIDUAL MODULE ACTIVATION ---
# Logic: mod_wordly -> activator triggers 'wordly'
@bot.on(events.CallbackQuery(pattern=r"activate_"))
async def activate_module(event):
    if not event.is_private:
        await event.answer("⚠️ Action allowed in Private DM only.", alert=True)
        return
    
    if not await global_security_check(event):
        return

    user_id = event.sender_id
    # module_name will be: 'wordly', 'afk', 'tagger', etc.
    module_name = event.data.decode("utf-8").replace("activate_", "")
    
    if not await is_subscribed(user_id):
        await event.edit(
            "⚠️ **Premium Access Required**\n\n"
            "Your subscription has expired or is not yet active. "
            "Select a plan or claim your trial to continue.",
            buttons=[
                [Button.inline("💳 View Premium Plans", data="pay_now")],
                [Button.inline("🎁 Claim Free Trial", data="claim_trial_btn")],
                [Button.inline("🔙 Back", data="modules_main")]
            ]
        )
        return

    await event.edit(
        f"⏳ **Deploying `{module_name.upper()}`...**\n"
        "Initializing engine and injecting selective handlers."
    )

    # Trigger Session Manager (Selective Loading)
    result_message = await SessionManager.start_userbot(user_id, module_name)

    # UI Feedback based on Plan Lock
    if "Activated" in result_message:
        # Success: Show Stop Button
        buttons = [[Button.inline(f"🛑 Stop {module_name.upper()}", data=f"stop_{module_name}")]]
        
    elif "Access Denied" in result_message:
        # Standard User Conflict (Running module name is shown in result_message)
        buttons = [
            [Button.inline("🛑 Stop Running & Start This", data=f"force_start_{module_name}")],
            [Button.inline("💎 Upgrade to Empire", data="pay_now")],
            [Button.inline("🔙 Back to Modules", data="modules_main")]
        ]
    else:
        # Other Errors (Invalid string, etc.)
        buttons = [[Button.inline("🔙 Back", data="modules_main")]]

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
        f"{result}\n\nYour session has been terminated safely.",
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
    
    # Engine logic handles cleanup and fresh selective start
    await SessionManager.stop_userbot(user_id)
    await activate_module(event)

# --- 4. RE-STARTING FOR EXISTING SESSIONS ---
@bot.on(events.CallbackQuery(pattern=r"start_ub_"))
async def restart_existing(event):
    if not event.is_private: return
    # This comes from login.py when string is already in DB
    module_name = event.data.decode("utf-8").replace("start_ub_", "")
    await activate_module(event)

# --- 5. ACTIVATE ALL MODULES (Empire Exclusive) ---
@bot.on(events.CallbackQuery(data="activate_all"))
async def activate_all_handler(event):
    if not event.is_private: return
    if not await global_security_check(event): return

    user_id = event.sender_id
    plan = await get_user_plan_type(user_id)
    current_plan = str(plan).strip().lower()

    # 🛡️ THE WALL: OWNER & EMPIRE ONLY
    if user_id != ADMIN_ID and "empire" not in current_plan:
        return await event.answer(
            "❌ Access Denied!\n\nStandard users can only deploy one module at a time. "
            "Please upgrade to Empire Plan to run all bots simultaneously.", 
            alert=True
        )

    await event.edit("⏳ **Initializing Empire Mode...**\nDeploying the entire module suite to your account.")

    # Trigger ALL
    result_message = await SessionManager.start_userbot(user_id, "All Modules")

    if "Activated" in result_message or "Active" in result_message:
        buttons = [[Button.inline("🛑 Stop All Sessions", data="stop_all_modules")]]
    else:
        buttons = [[Button.inline("🔙 Back", data="modules_main")]]

    await event.edit(result_message, buttons=buttons)

@bot.on(events.CallbackQuery(data="stop_all_modules"))
async def stop_all_callback(event):
    await stop_module(event)
