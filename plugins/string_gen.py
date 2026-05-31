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

# Step-by-step state tracker
GEN_DATA = {}

@bot.on(events.CallbackQuery(data="gen_string_start"))
async def start_string_gen(event):
    await event.edit(
        "🔑 **String Session Generator**\n\n"
        "I will help you generate a Telethon String Session.\n\n"
        "Please send your **Phone Number** with country code.\n"
        "Example: `+919876543210`",
        buttons=[Button.inline("❌ Cancel", data="start_back")]
    )
    GEN_DATA[event.sender_id] = {"step": "phone"}

@bot.on(events.NewMessage)
async def handle_gen_input(event):
    user_id = event.sender_id
    if user_id not in GEN_DATA:
        return

    step = GEN_DATA[user_id]["step"]
    text = event.raw_text.strip()

    # STEP 1: RECEIVE PHONE
    if step == "phone":
        GEN_DATA[user_id]["phone"] = text
        await event.reply("⏳ Sending OTP... Please wait.")
        
        # Temporary client to get OTP
        tmp_client = TelegramClient(StringSession(), API_ID, API_HASH)
        await tmp_client.connect()
        
        try:
            hash_obj = await tmp_client.send_code_request(text)
            GEN_DATA[user_id]["client"] = tmp_client
            GEN_DATA[user_id]["hash"] = hash_obj.phone_code_hash
            GEN_DATA[user_id]["step"] = "otp"
            await event.reply("✅ **OTP Sent!**\n\nPlease send the OTP in this format: `1 2 3 4 5` (with spaces).")
        except Exception as e:
            await event.reply(f"❌ **Error:** `{e}`\nTry again with /start.")
            del GEN_DATA[user_id]

    # STEP 2: RECEIVE OTP
    elif step == "otp":
        otp = text.replace(" ", "")
        tmp_client = GEN_DATA[user_id]["client"]
        phone = GEN_DATA[user_id]["phone"]
        code_hash = GEN_DATA[user_id]["hash"]
        
        try:
            await tmp_client.sign_in(phone, otp, phone_code_hash=code_hash)
            string = tmp_client.session.save()
            await event.reply(f"🎯 **Your String Session:**\n\n`{string}`\n\n⚠️ **Note:** Keep this safe! Now you can paste this in the login section.")
            await tmp_client.disconnect()
            del GEN_DATA[user_id]
        except SessionPasswordNeededError:
            GEN_DATA[user_id]["step"] = "password"
            await event.reply("🔐 **Two-Step Verification detected.**\nPlease send your account password.")
        except Exception as e:
            await event.reply(f"❌ **OTP Error:** `{e}`")

    # STEP 3: RECEIVE PASSWORD (If 2FA is on)
    elif step == "password":
        tmp_client = GEN_DATA[user_id]["client"]
        try:
            await tmp_client.sign_in(password=text)
            string = tmp_client.session.save()
            await event.reply(f"🎯 **Your String Session:**\n\n`{string}`")
            await tmp_client.disconnect()
            del GEN_DATA[user_id]
        except Exception as e:
            await event.reply(f"❌ **Password Error:** `{e}`")
