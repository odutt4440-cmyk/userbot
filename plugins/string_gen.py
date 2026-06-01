import asyncio
from bot_instance import bot
from telethon import events, Button, TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    ApiIdInvalidError, 
    PhoneNumberInvalidError, 
    PhoneCodeInvalidError, 
    SessionPasswordNeededError
)
from config import API_ID, API_HASH
from database import save_user_session # <--- Session save karne ke liye

# User state tracker
GEN_DATA = {}

# --- 1. START GENERATION ---
@bot.on(events.CallbackQuery(data="gen_string_internal"))
async def start_string_gen(event):
    user_id = event.sender_id
    GEN_DATA[user_id] = {"step": "phone"}
    
    await event.edit(
        "🔑 **String Session Generator**\n\n"
        "I will help you generate a Telethon String Session securely.\n\n"
        "**Step 1:** Please send your **Phone Number** with country code.\n"
        "Example: `+919876543210`",
        buttons=[Button.inline("❌ Cancel", data="start_back")]
    )

# --- 2. INPUT HANDLER ---
@bot.on(events.NewMessage)
async def handle_gen_input(event):
    user_id = event.sender_id
    if user_id not in GEN_DATA or event.text.startswith('/'):
        return

    state = GEN_DATA[user_id]
    step = state["step"]
    text = event.raw_text.strip()

    # --- STEP 1: RECEIVE PHONE ---
    if step == "phone":
        state["phone"] = text
        msg = await event.reply("⏳ Connecting to Telegram servers...")
        
        tmp_client = TelegramClient(StringSession(), API_ID, API_HASH)
        await tmp_client.connect()
        
        try:
            hash_obj = await tmp_client.send_code_request(text)
            state["client"] = tmp_client
            state["hash"] = hash_obj.phone_code_hash
            state["step"] = "otp"
            
            await msg.edit(
                "✅ **OTP Sent Successfully!**\n\n"
                "Please send the code here in this format:\n"
                "👉 `1 2 3 4 5` (spaces between digits)."
            )
        except Exception as e:
            await msg.edit(f"❌ **Error:** `{str(e)}` \nTry again with /start.")
            await tmp_client.disconnect()
            del GEN_DATA[user_id]

    # --- STEP 2: RECEIVE OTP ---
    elif step == "otp":
        otp = text.replace(" ", "")
        tmp_client = state["client"]
        phone = state["phone"]
        code_hash = state["hash"]
        
        msg = await event.reply("⏳ Verifying OTP...")
        
        try:
            await tmp_client.sign_in(phone, otp, phone_code_hash=code_hash)
            string = tmp_client.session.save()
            
            # --- AUTO SAVE TO DATABASE ---
            await save_user_session(user_id, string, phone)
            
            success_text = (
                "🎯 **Session Generated & Linked!**\n\n"
                f"🏷️ **Phone:** `{phone}`\n"
                f"🔑 **String:** `{string}`\n\n"
                "✅ This session has been automatically linked to your account. "
                "You can now go to Modules and fire up your bot!"
            )
            await msg.edit(success_text, buttons=[[Button.inline("⚙️ Go to Modules", data="modules_main")]])
            await tmp_client.disconnect()
            del GEN_DATA[user_id]
            
        except SessionPasswordNeededError:
            state["step"] = "password"
            await msg.edit("🔐 **Two-Step Verification detected.**\nPlease send your account password below.")
        except Exception as e:
            await msg.edit(f"❌ **OTP Error:** `{str(e)}`")

    # --- STEP 3: RECEIVE 2FA PASSWORD ---
    elif step == "password":
        tmp_client = state["client"]
        phone = state["phone"]
        msg = await event.reply("⏳ Verifying Password...")
        
        try:
            await tmp_client.sign_in(password=text)
            string = tmp_client.session.save()
            
            # --- AUTO SAVE TO DATABASE ---
            await save_user_session(user_id, string, phone)
            
            await msg.edit(
                "🎯 **Session Generated & Linked (2FA Auth)!**\n\n"
                f"🏷️ **Phone:** `{phone}`\n"
                f"🔑 **String:** `{string}`\n\n"
                "Your account is now linked successfully.",
                buttons=[[Button.inline("⚙️ Go to Modules", data="modules_main")]]
            )
            await tmp_client.disconnect()
            del GEN_DATA[user_id]
        except Exception as e:
            await msg.edit(f"❌ **Password Error:** `{str(e)}`")
