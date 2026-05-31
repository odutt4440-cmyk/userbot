from bot_instance import bot 
from telethon import events, Button
from core.session_manager import SessionManager
from database import is_subscribed

# --- 1. HANDLE MODULE ACTIVATION ---
@bot.on(events.CallbackQuery(pattern=r"activate_"))
async def activate_module(event):
    user_id = event.sender_id
    # Extract module name (e.g., activate_wordly -> wordly)
    module_name = event.data.decode("utf-8").replace("activate_", "")
    
    # 🛡️ Security Check: Is the subscription still active?
    if not await is_subscribed(user_id):
        await event.edit(
            "⚠️ **Subscription Required!**\n\n"
            "Your premium access has expired or is not active. "
            "Please pay ₹10 to activate this module and enjoy 24/7 service.",
            buttons=[[Button.inline("💳 Pay ₹10 & Activate", data="pay_now")]]
        )
        return

    # UI Feedback: Let the user know the engine is firing up
    await event.edit(
        f"⏳ **Initializing `{module_name.upper()}`...**\n"
        "Connecting to Telegram servers. Please wait a moment."
    )

    # 🚀 Trigger the Core Engine (Session Manager)
    # This will load all modules (Wordly, Octopus, etc.) into the user's account
    result_message = await SessionManager.start_userbot(user_id, module_name)

    # UI Update: Based on success or failure
    # We check if the result contains "Successfully" to show the Stop button
    if "Successfully" in result_message:
        buttons = [[Button.inline("🛑 Stop Userbot", data=f"stop_{module_name}")]]
    else:
        # If there's an error (Invalid string, etc.), show back button
        buttons = [[Button.inline("🔙 Back to Modules", data="modules_main")]]

    await event.edit(result_message, buttons=buttons)

# --- 2. HANDLE STOPPING THE USERBOT ---
@bot.on(events.CallbackQuery(pattern=r"stop_"))
async def stop_module(event):
    user_id = event.sender_id
    module_name = event.data.decode("utf-8").replace("stop_", "")

    # 🛑 Call the Engine to disconnect the client
    result = await SessionManager.stop_userbot(user_id)
    
    await event.edit(
        f"{result}\n\nModule `{module_name.upper()}` is no longer running on our servers.",
        buttons=[
            [Button.inline("🚀 Restart Module", data=f"activate_{module_name}")],
            [Button.inline("🔙 Back to Menu", data="modules_main")]
        ]
    )

# --- 3. RE-STARTING ALREADY LOGGED IN USERS ---
# This handles the 'Activate' button from login.py when a session is already found
@bot.on(events.CallbackQuery(pattern=r"start_ub_"))
async def restart_existing(event):
    module_name = event.data.decode("utf-8").replace("start_ub_", "")
    await activate_module(event)
