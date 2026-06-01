from bot_instance import bot 
from telethon import events, Button
from database import save_user_session, get_user_session, is_subscribed

# Tracking users providing session strings
WAITING_FOR_STR = {}

# --- 1. MODULE CLICK HANDLER ---
@bot.on(events.CallbackQuery(pattern=r"mod_"))
async def login_step_1(event):
    user_id = event.sender_id
    module_name = event.data.decode("utf-8").replace("mod_", "")
    
    # Check session and subscription status
    existing_session = await get_user_session(user_id)
    subscribed = await is_subscribed(user_id)
    
    if existing_session:
        status_text = "✅ **Account Connected!**"
        if not subscribed:
            # Session hai par paise/trial nahi hai
            await event.edit(
                f"{status_text}\nModule: `{module_name.upper()}`\n\n"
                "You need an active subscription or trial to start this module.",
                buttons=[
                    [Button.inline("💳 Pay ₹10 & Activate", data="pay_now")],
                    [Button.inline("🎁 Claim Trial", data="claim_trial_btn")],
                    [Button.inline("🔄 Change String", data=f"relog_{module_name}")]
                ]
            )
        else:
            # Sab kuch hai, seedha activate
            await event.edit(
                f"{status_text}\nModule: `{module_name.upper()}`\n\n"
                "Your account is ready. Click below to fire up the userbot!",
                buttons=[
                    [Button.inline("🚀 Activate Now", data=f"activate_{module_name}")],
                    [Button.inline("🔄 Change String", data=f"relog_{module_name}")]
                ]
            )
    else:
        # No session, ask for string
        WAITING_FOR_STR[user_id] = module_name
        await event.edit(
            f"🔑 **Login Required: {module_name.upper()}**\n\n"
            "To run this module, please provide your **Telethon String Session**.\n\n"
            "**How to get it?**\n"
            "1. Use the 'Generate String' tool in the main menu.\n"
            "2. Paste the long code here in the chat.\n\n"
            "⚠️ Your session is safe and encrypted.",
            buttons=[Button.inline("❌ Cancel", data="start_back")]
        )

# --- 2. RECEIVE STRING HANDLER ---
@bot.on(events.NewMessage)
async def receive_string(event):
    user_id = event.sender_id
    
    if user_id in WAITING_FOR_STR:
        if event.text.startswith('/'): return

        string_session = event.text.strip()
        module = WAITING_FOR_STR[user_id]
        
        if len(string_session) < 50:
            await event.reply("❌ **Invalid String!** Please send a valid Telethon session.")
            return
        
        # Save to SQLite
        await save_user_session(user_id, string_session)
        
        # Check if they already have trial/sub before showing payment button
        subscribed = await is_subscribed(user_id)
        
        if subscribed:
            await event.reply(
                f"✅ **Session Saved!**\n\n"
                f"You have an active subscription/trial. You can now activate `{module.upper()}` immediately!",
                buttons=[[Button.inline("🚀 Activate Now", data=f"activate_{module}")]]
            )
        else:
            await event.reply(
                f"✅ **Session Saved!**\n\n"
                f"Now you just need to activate your access to start using `{module.upper()}`.",
                buttons=[
                    [Button.inline("💳 Pay ₹10 & Activate", data="pay_now")],
                    [Button.inline("🎁 Claim 1-Day Trial", data="claim_trial_btn")]
                ]
            )
        
        del WAITING_FOR_STR[user_id]

# --- 3. RELOG LOGIC ---
@bot.on(events.CallbackQuery(pattern=r"relog_"))
async def relog(event):
    user_id = event.sender_id
    module = event.data.decode("utf-8").replace("relog_", "")
    WAITING_FOR_STR[user_id] = module
    await event.edit("🔄 **Update String:**\nPlease send your new Telethon session string below:")
