from bot_instance import bot 
from telethon import events, Button
from database import save_user_session, get_user_session, is_subscribed

# Tracking users providing session strings
WAITING_FOR_STR = {}

# --- 1. MODULE CLICK HANDLER ---
@bot.on(events.CallbackQuery(pattern=r"mod_"))
async def login_step_1(event):
    # 🛡️ Private Only Check
    if not event.is_private:
        await event.answer("⚠️ Please use this bot in Private Chat (DM) for security.", alert=True)
        return

    user_id = event.sender_id
    module_name = event.data.decode("utf-8").replace("mod_", "")
    
    # Check session and subscription status
    existing_session = await get_user_session(user_id)
    subscribed = await is_subscribed(user_id)
    
    if existing_session:
        status_text = "✅ **Account Linked!**"
        if not subscribed:
            # Session exists but no active plan/trial
            await event.edit(
                f"{status_text}\nModule: `{module_name.upper()}`\n\n"
                "Your account is connected, but you need an active subscription or trial to start this module.",
                buttons=[
                    [Button.inline("💳 Pay ₹10 & Activate", data="pay_now")],
                    [Button.inline("🎁 Claim 1-Day Trial", data="claim_trial_btn")],
                    [Button.inline("🔄 Change Session String", data=f"relog_{module_name}")]
                ]
            )
        else:
            # Everything is ready
            await event.edit(
                f"{status_text}\nModule: `{module_name.upper()}`\n\n"
                "Your account is ready for deployment. Click the button below to fire up the userbot engine!",
                buttons=[
                    [Button.inline("🚀 Activate Now", data=f"activate_{module_name}")],
                    [Button.inline("🔄 Change Session String", data=f"relog_{module_name}")]
                ]
            )
    else:
        # No session found, request string in private
        WAITING_FOR_STR[user_id] = module_name
        await event.edit(
            f"🔑 **Login Required: {module_name.upper()}**\n\n"
            "To run this module, please provide your **Telethon String Session**.\n\n"
            "**Steps:**\n"
            "1. Use the 'Generate String' tool in the main menu.\n"
            "2. Copy the resulting string code.\n"
            "3. Paste and send the string here in this chat.\n\n"
            "⚠️ **Security:** Your session is stored locally on our fast SQLite engine and used only for your bot.",
            buttons=[Button.inline("❌ Cancel", data="start_back")]
        )

# --- 2. RECEIVE STRING HANDLER ---
@bot.on(events.NewMessage)
async def receive_string(event):
    # 🛡️ Gatekeeper: Ignore messages in groups for security
    if not event.is_private:
        return

    user_id = event.sender_id
    
    if user_id in WAITING_FOR_STR:
        # Ignore if user sends a command instead of string
        if event.text.startswith('/'): 
            return

        string_session = event.text.strip()
        module = WAITING_FOR_STR[user_id]
        
        # Validation
        if len(string_session) < 50:
            await event.reply("❌ **Invalid Session!**\nThe string you provided is too short. Please make sure you copied the entire code.")
            return
        
        # Save to SQLite Database
        await save_user_session(user_id, string_session)
        
        # Final Status Check
        subscribed = await is_subscribed(user_id)
        
        if subscribed:
            await event.reply(
                f"✅ **Session Saved!**\n\n"
                f"Active subscription detected. You can now deploy `{module.upper()}` immediately!",
                buttons=[[Button.inline("🚀 Deploy Bot", data=f"activate_{module}")]]
            )
        else:
            await event.reply(
                f"✅ **Session Saved!**\n\n"
                f"Your account is linked. Now just activate your access to start using `{module.upper()}`.",
                buttons=[
                    [Button.inline("💳 Pay ₹10 & Activate", data="pay_now")],
                    [Button.inline("🎁 Claim 1-Day Trial", data="claim_trial_btn")]
                ]
            )
        
        # Remove from waiting list
        del WAITING_FOR_STR[user_id]

# --- 3. RELOG LOGIC ---
@bot.on(events.CallbackQuery(pattern=r"relog_"))
async def relog(event):
    if not event.is_private: return
    
    user_id = event.sender_id
    module = event.data.decode("utf-8").replace("relog_", "")
    WAITING_FOR_STR[user_id] = module
    await event.edit(
        "🔄 **Update Session String**\n\n"
        "Please send your new **Telethon String Session** below.\n"
        "The previous string will be replaced.",
        buttons=[Button.inline("🔙 Back", data=f"mod_{module}")]
    )
