from bot_instance import bot 
from telethon import events, Button
from core.session_manager import SessionManager
from database import is_subscribed

# --- 1. HANDLE MODULE ACTIVATION ---
@bot.on(events.CallbackQuery(pattern=r"activate_"))
async def activate_module(event):
    user_id = event.sender_id
    # Extract module name (e.g., activate_wordseek -> wordseek)
    module_name = event.data.decode("utf-8").replace("activate_", "")
    
    # Final Security Check: Subscription status
    if not await is_subscribed(user_id):
        await event.edit(
            "⚠️ **Subscription Required!**\n\n"
            "Your account is not active. Please pay ₹10 to use this module.",
            buttons=[[Button.inline("💳 Pay ₹10 Now", data="pay_now")]]
        )
        return

    # Give immediate feedback to user
    await event.edit(f"⏳ **Starting `{module_name.capitalize()}`...**\nPlease wait a moment.")

    # Call the SessionManager to start the userbot
    result_message = await SessionManager.start_userbot(user_id, module_name)

    # If successfully started, show the "Stop" button
    if "Successfully Started" in result_message:
        buttons = [[Button.inline("🛑 Stop Userbot", data=f"stop_{module_name}")]]
    else:
        buttons = [[Button.inline("🔙 Back to Menu", data="modules_main")]]

    await event.edit(result_message, buttons=buttons)

# --- 2. HANDLE STOPPING THE USERBOT ---
@bot.on(events.CallbackQuery(pattern=r"stop_"))
async def stop_module(event):
    user_id = event.sender_id
    module_name = event.data.decode("utf-8").replace("stop_", "")

    # Stop the client via Engine
    result = await SessionManager.stop_userbot(user_id)
    
    await event.edit(
        f"{result}\n\nModule `{module_name.capitalize()}` has been disconnected.",
        buttons=[[Button.inline("🚀 Restart", data=f"activate_{module_name}"), Button.inline("🔙 Menu", data="modules_main")]]
    )

# --- 3. RE-STARTING ALREADY LOGGED IN USERS ---
# This handles the case where user session is found in plugins/login.py
@bot.on(events.CallbackQuery(pattern=r"start_ub_"))
async def restart_existing(event):
    # Just a wrapper to keep the flow clean
    module_name = event.data.decode("utf-8").replace("start_ub_", "")
    await activate_module(event)
