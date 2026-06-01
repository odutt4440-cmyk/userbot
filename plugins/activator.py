from bot_instance import bot 
from telethon import events, Button
from core.session_manager import SessionManager
from database import is_subscribed

# --- 1. HANDLE MODULE ACTIVATION ---
@bot.on(events.CallbackQuery(pattern=r"activate_"))
async def activate_module(event):
    # 🛡️ Gatekeeper: Check if interaction is in Private DM
    if not event.is_private:
        await event.answer("⚠️ This action is only allowed in Private DM for security reasons.", alert=True)
        return

    user_id = event.sender_id
    # Extract module name (e.g., activate_wordly -> wordly)
    module_name = event.data.decode("utf-8").replace("activate_", "")
    
    # 🛡️ Final Security Check: Subscription/Trial status
    if not await is_subscribed(user_id):
        await event.edit(
            "⚠️ **Premium Access Required**\n\n"
            "Your subscription has expired or is not yet active. "
            "Please claim your 1-Day trial or pay ₹10 to continue.",
            buttons=[
                [Button.inline("💳 Pay ₹10 & Activate", data="pay_now")],
                [Button.inline("🎁 Claim Free Trial", data="claim_trial_btn")]
            ]
        )
        return

    # UI Feedback: Show that the engine is starting
    await event.edit(
        f"⏳ **Deploying `{module_name.upper()}`...**\n"
        "Connecting to our high-speed servers. Please wait."
    )

    # 🚀 Call the Engine (Session Manager)
    # This automatically refreshes/stops any old session first (Logic in File 8)
    result_message = await SessionManager.start_userbot(user_id, module_name)

    # UI Update: Success or Error
    if "Activated" in result_message:
        # Userbot is now running in background
        buttons = [[Button.inline("🛑 Stop Userbot", data=f"stop_{module_name}")]]
    else:
        # Something went wrong (Revoked session, connection error etc.)
        buttons = [[Button.inline("🔙 Back to Modules", data="modules_main")]]

    await event.edit(result_message, buttons=buttons)

# --- 2. HANDLE STOPPING THE USERBOT ---
@bot.on(events.CallbackQuery(pattern=r"stop_"))
async def stop_module(event):
    # 🛡️ Private Only Check
    if not event.is_private: return

    user_id = event.sender_id
    module_name = event.data.decode("utf-8").replace("stop_", "")

    # 🛑 Disconnect the client via Engine
    result = await SessionManager.stop_userbot(user_id)
    
    await event.edit(
        f"{result}\n\nYour session has been terminated safely.",
        buttons=[
            [Button.inline("🚀 Restart Engine", data=f"activate_{module_name}")],
            [Button.inline("🔙 Main Menu", data="start_back")]
        ]
    )

# --- 3. RE-STARTING ALREADY LOGGED IN USERS ---
@bot.on(events.CallbackQuery(pattern=r"start_ub_"))
async def restart_existing(event):
    if not event.is_private: return
    module_name = event.data.decode("utf-8").replace("start_ub_", "")
    await activate_module(event)
