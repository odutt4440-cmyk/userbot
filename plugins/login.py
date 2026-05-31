from bot_instance import bot 
from telethon import events, Button
from database import save_user_session, get_user_session

# Temporary dictionary to track users who need to provide a string
# Key: user_id, Value: module_name
WAITING_FOR_STR = {}

# --- 1. WHEN USER CLICKS A MODULE (e.g., Wordly, WordSeek) ---
@bot.on(events.CallbackQuery(pattern=r"mod_"))
async def login_step_1(event):
    user_id = event.sender_id
    # Extracting module name from callback data
    module_name = event.data.decode("utf-8").replace("mod_", "")
    
    # Check if this user already has a session in our Database
    existing_session = await get_user_session(user_id)
    
    if existing_session:
        # Session exists, ask to activate or change
        await event.edit(
            f"✅ **Account Connected!**\n"
            f"Module Selected: `{module_name.upper()}`\n\n"
            "We found an existing session for your account. "
            "Would you like to activate this module now?",
            buttons=[
                [Button.inline("🚀 Activate Now", data=f"activate_{module_name}")],
                [Button.inline("🔄 Change Session String", data=f"relog_{module_name}")]
            ]
        )
    else:
        # No session found, request string
        WAITING_FOR_STR[user_id] = module_name
        await event.edit(
            f"🔑 **Login Required: {module_name.upper()}**\n\n"
            "To run this module, I need your **Telethon String Session**.\n\n"
            "**Instructions:**\n"
            "1. Generate a string using the 'String Gen' tool.\n"
            "2. Paste the session string here in the chat.\n\n"
            "⚠️ **Privacy Note:** Your session is stored securely and only used to run your modules.",
            buttons=[Button.inline("❌ Cancel", data="start_back")]
        )

# --- 2. RECEIVE AND SAVE THE STRING SESSION ---
@bot.on(events.NewMessage)
async def receive_string(event):
    user_id = event.sender_id
    
    # Check if we are actually waiting for a string from this user
    if user_id in WAITING_FOR_STR:
        # If user sends a command instead of a string, ignore it
        if event.text.startswith('/'):
            return

        string_session = event.text.strip()
        module = WAITING_FOR_STR[user_id]
        
        # Basic Validation: Telethon strings are usually very long
        if len(string_session) < 50:
            await event.reply(
                "❌ **Invalid String Detected!**\n\n"
                "The string you sent is too short to be a valid Telethon session. "
                "Please make sure you copied the full string and try again."
            )
            return
        
        # Save to MongoDB via database.py
        await save_user_session(user_id, string_session)
        
        # Success response with Payment trigger
        await event.reply(
            f"✅ **Session Saved Successfully!**\n\n"
            f"Your account is now linked. You are one step away from activating `{module.upper()}`.\n\n"
            "💰 **Subscription:** A small fee of **₹10/Month** is required to keep the bot running 24/7 on our servers.",
            buttons=[[Button.inline("💳 Pay ₹10 & Activate", data="pay_now")]]
        )
        
        # Remove from waiting list
        del WAITING_FOR_STR[user_id]

# --- 3. RELOG LOGIC (To update/change string) ---
@bot.on(events.CallbackQuery(pattern=r"relog_"))
async def relog(event):
    user_id = event.sender_id
    module = event.data.decode("utf-8").replace("relog_", "")
    
    WAITING_FOR_STR[user_id] = module
    await event.edit(
        "🔄 **Update Session String**\n\n"
        "Please send your new **Telethon String Session** below.\n"
        "The old session will be replaced.",
        buttons=[Button.inline("🔙 Back", data=f"mod_{module}")]
    )
