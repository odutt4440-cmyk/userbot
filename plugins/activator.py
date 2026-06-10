from bot_instance import bot 
from telethon import events, Button
from core.session_manager import SessionManager
from database import is_subscribed, global_security_check # Added security check

# --- 1. HANDLE MODULE ACTIVATION ---
@bot.on(events.CallbackQuery(pattern=r"activate_"))
async def activate_module(event):
    # 🛡️ Gatekeeper: Check if Private DM & Not Banned/Maintenance
    if not event.is_private:
        await event.answer("⚠️ This action is only allowed in Private DM.", alert=True)
        return
    
    if not await global_security_check(event):
        return

    user_id = event.sender_id
    # Extract module name
    module_name = event.data.decode("utf-8").replace("activate_", "")
    
    # 🛡️ Final Security Check: Subscription/Trial status
    if not await is_subscribed(user_id):
        await event.edit(
            "⚠️ **Premium Access Required**\n\n"
            "Your subscription has expired or is not yet active. "
            "Please select a plan to continue enjoying our high-speed userbot services.",
            buttons=[
                [Button.inline("💳 View Premium Plans", data="pay_now")],
                [Button.inline("🎁 Claim Free Trial", data="claim_trial_btn")],
                [Button.inline("🔙 Back", data="modules_main")]
            ]
        )
        return

    # UI Feedback
    await event.edit(
        f"⏳ **Deploying `{module_name.upper()}`...**\n"
        "Connecting to Telegram servers and injecting handlers."
    )

    # 🚀 Call the Engine (Session Manager)
    # Ye function 'Standard' vs 'Empire' plan khud check karega
    result_message = await SessionManager.start_userbot(user_id, module_name)

    # UI Update: Success, Access Denied (Standard Plan), or Error
    if "Activated" in result_message:
        # Userbot successfully fired up
        buttons = [[Button.inline("🛑 Stop Userbot", data=f"stop_{module_name}")]]
        
    elif "Access Denied" in result_message:
        # Standard user trying to run 2 modules (Logic from File 8)
        buttons = [
            [Button.inline("🛑 Stop Current & Start This", data=f"force_start_{module_name}")],
            [Button.inline("💎 Upgrade to Empire", data="pay_now")],
            [Button.inline("🔙 Back", data="modules_main")]
        ]
    else:
        # Other errors (Invalid string, etc.)
        buttons = [[Button.inline("🔙 Back to Modules", data="modules_main")]]

    await event.edit(result_message, buttons=buttons)

# --- 2. HANDLE STOPPING THE USERBOT ---
@bot.on(events.CallbackQuery(pattern=r"stop_"))
async def stop_module(event):
    if not event.is_private: return
    if not await global_security_check(event): return

    user_id = event.sender_id
    module_name = event.data.decode("utf-8").replace("stop_", "")

    # 🛑 Disconnect the client via Engine
    result = await SessionManager.stop_userbot(user_id)
    
    await event.edit(
        f"{result}\n\nYour userbot session for **{module_name.upper()}** has been terminated.",
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
    
    # Pehle purana bot band karo, fir naya chalu karo
    await SessionManager.stop_userbot(user_id)
    await activate_module(event)

# --- 4. RE-STARTING ALREADY LOGGED IN USERS ---
@bot.on(events.CallbackQuery(pattern=r"start_ub_"))
async def restart_existing(event):
    if not event.is_private: return
    module_name = event.data.decode("utf-8").replace("start_ub_", "")
    await activate_module(event)
    

# --- 5. ACTIVATE ALL MODULES (Empire Exclusive) ---
@bot.on(events.CallbackQuery(data="activate_all"))
async def activate_all_handler(event):
    if not event.is_private: return
    if not await global_security_check(event): return

    from database import get_user_plan_type
    user_id = event.sender_id
    plan = await get_user_plan_type(user_id)

    # 🛡️ Step 1: Check if User is Empire or Admin
    if plan != "Empire" and user_id != ADMIN_ID:
        return await event.answer(
            "❌ Access Denied: This button is only for Empire Plan users.\n\n"
            "Kindly upgrade your plan to 'Empire' to run all modules at once!", 
            alert=True
        )

    # 🚀 Step 2: Activate everything if plan is correct
    await event.edit("⏳ **Initializing Empire Mode...**\nStarting all solvers and tools on your account.")

    # Hum 'Empire' trigger bhejenge jo engine ko bolega ki saare handlers load kar do
    result_message = await SessionManager.start_userbot(user_id, "All Modules")

    if "Activated" in result_message:
        buttons = [[Button.inline("🛑 Stop All Sessions", data="stop_all_modules")]]
    else:
        buttons = [[Button.inline("🔙 Back", data="games_ub")]]

    await event.edit(result_message, buttons=buttons)

# Callback to stop all
@bot.on(events.CallbackQuery(data="stop_all_modules"))
async def stop_all_callback(event):
    await stop_module(event) 
