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

# User state tracker to handle multiple users generating strings at once
GEN_DATA = {}

# --- 1. START GENERATION ---
@bot.on(events.CallbackQuery(data="gen_string_internal"))
async def start_string_gen(event):
    user_id = event.sender_id
    GEN_DATA[user_id] = {"step": "phone"}
    
    await event.edit(
        "🔑 **String Session Generator**\n\n"
        "I will help you generate a Telethon String Session securely. "
        "Your session string is required to run the userbot modules.\n\n"
        "**Step 1:** Please send your **Phone Number** with country code.\n"
        "Example: `+919876543210` or `+1234567890`",
        buttons=[Button.inline("❌ Cancel", data="start_back")]
    )

# --- 2. INPUT HANDLER (Steps) ---
@bot.on(events.NewMessage)
async def handle_gen_input(event):
    user_id = event.sender_id
    if user_id not in GEN_DATA or event.text.startswith('/'):
        return

    step = GEN_DATA[user_id]["step"]
    text = event.raw_text.strip()

    # --- STEP 1: RECEIVE PHONE & SEND OTP ---
    if step == "phone":
        GEN_DATA[user_id]["phone"] = text
        msg = await event.reply("⏳ Connecting to Telegram servers... please wait.")
        
        # Creating a temporary client for this user
        tmp_client = TelegramClient(StringSession(), API_ID, API_HASH)
        await tmp_client.connect()
        
        try:
            # Requesting OTP from Telegram
            hash_obj = await tmp_client.send_code_request(text)
            GEN_DATA[user_id]["client"] = tmp_client
            GEN_DATA[user_id]["hash"] = hash_obj.phone_code_hash
            GEN_DATA[user_id]["step"] = "otp"
            
            await msg.edit(
                "✅ **OTP Sent Successfully!**\n\n"
                "Check your Telegram app for the login code. Send the code here in this format:\n"
                "👉 `1 2 3 4 5` (Put spaces between each digit)."
            )
        except Exception as e:
            await msg.edit(f"❌ **Error:** `{str(e)}` \n\nPlease try again with /start.")
            await tmp_client.disconnect()
            if user_id in GEN_DATA: del GEN_DATA[user_id]

    # --- STEP 2: RECEIVE OTP & SIGN IN ---
    elif step == "otp":
        otp = text.replace(" ", "")
        tmp_client = GEN_DATA[user_id]["client"]
        phone = GEN_DATA[user_id]["phone"]
        code_hash = GEN_DATA[user_id]["hash"]
        
        msg = await event.reply("⏳ Verifying OTP...")
        
        try:
            await tmp_client.sign_in(phone, otp, phone_code_hash=code_hash)
            # Success! Generate the string
            string = tmp_client.session.save()
            
            success_text = (
                "🎯 **String Session Generated!**\n\n"
                f"🏷️ **Your String:**\n`{string}`\n\n"
                "⚠️ **Safety Warning:** Never share this string with anyone. "
                "Anyone with this string can access your account.\n\n"
                "Copy this string and paste it when activating a module."
            )
            await msg.edit(success_text)
            await tmp_client.disconnect()
            del GEN_DATA[user_id]
            
        except SessionPasswordNeededError:
            # User has 2FA (Two-Step Verification) enabled
            GEN_DATA[user_id]["step"] = "password"
            await msg.edit(
                "🔐 **Two-Step Verification Detected**\n\n"
                "Your account has a cloud password. Please send your password below."
            )
        except Exception as e:
            await msg.edit(f"❌ **OTP Error:** `{str(e)}` \nPlease try again.")

    # --- STEP 3: RECEIVE 2FA PASSWORD ---
    elif step == "password":
        tmp_client = GEN_DATA[user_id]["client"]
        msg = await event.reply("⏳ Verifying Password...")
        
        try:
            await tmp_client.sign_in(password=text)
            string = tmp_client.session.save()
            
            await msg.edit(
                "🎯 **String Session Generated (2FA Auth)!**\n\n"
                f"🏷️ **Your String:**\n`{string}`\n\n"
                "Now you can use this string to log into the modules."
            )
            await tmp_client.disconnect()
            del GEN_DATA[user_id]
        except Exception as e:
            await msg.edit(f"❌ **Password Error:** `{str(e)}` \nPlease try again.")
