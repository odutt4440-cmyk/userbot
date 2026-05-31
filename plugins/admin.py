from bot_instance import bot 
from telethon import events
from config import ADMIN_ID, SUDO_USERS
from database import (
    add_subscription, 
    users_db, 
    subs_db, 
    ban_user, 
    unban_user, 
    transfer_subscription, 
    cancel_subscription,
    get_sub_info
)
import datetime

# --- HELPER: CHECK IF SUDO ---
def is_sudo(user_id):
    return user_id in SUDO_USERS

# --- 1. GRANULAR APPROVE: /approve <id> <days> <hours> <mins> ---
# Example: /approve 12345 1 0 0 (For 1 day) or /approve 12345 0 2 30 (For 2hr 30min)
@bot.on(events.NewMessage(pattern=r'/approve (\d+) (\d+)(?: (\d+))?(?: (\d+))?'))
async def manual_approve(event):
    if not is_sudo(event.sender_id): return
    
    user_id = int(event.pattern_match.group(1))
    days = int(event.pattern_match.group(2))
    hours = int(event.pattern_match.group(3) or 0)
    minutes = int(event.pattern_match.group(4) or 0)
    
    expiry = await add_subscription(user_id, days, hours, minutes)
    
    if expiry:
        time_str = f"{days}d {hours}h {minutes}m"
        await event.reply(f"✅ **Subscription Added!**\n**User:** `{user_id}`\n**Added:** `{time_str}`\n**New Expiry:** `{expiry.strftime('%Y-%m-%d %H:%M:%S')}`")
        
        try:
            await bot.send_message(user_id, f"🎉 **Premium Access Granted!**\nAdmin has activated your subscription for **{time_str}**.\nEnjoy our 24/7 Userbot Community services!")
        except: pass
    else:
        await event.reply("❌ Error updating database.")

# --- 2. BAN USER: /ban <id> ---
@bot.on(events.NewMessage(pattern=r'/ban (\d+)'))
async def ban_handler(event):
    if not is_sudo(event.sender_id): return
    user_id = int(event.pattern_match.group(1))
    
    await ban_user(user_id)
    await event.reply(f"🚫 **User Banned:** `{user_id}` has been blocked from using the bot.")
    try:
        await bot.send_message(user_id, "⚠️ **Notice:** You have been banned from Userbot Community by an Admin.")
    except: pass

# --- 3. UNBAN USER: /unban <id> ---
@bot.on(events.NewMessage(pattern=r'/unban (\d+)'))
async def unban_handler(event):
    if not is_sudo(event.sender_id): return
    user_id = int(event.pattern_match.group(1))
    
    await unban_user(user_id)
    await event.reply(f"✅ **User Unbanned:** `{user_id}` is now allowed to use the bot again.")

# --- 4. TRANSFER SUB: /transfer <from_id> <to_id> ---
@bot.on(events.NewMessage(pattern=r'/transfer (\d+) (\d+)'))
async def transfer_handler(event):
    if not is_sudo(event.sender_id): return
    from_id = int(event.pattern_match.group(1))
    to_id = int(event.pattern_match.group(2))
    
    success, msg = await transfer_subscription(from_id, to_id)
    if success:
        await event.reply(f"♻️ **Transfer Successful!**\nFrom `{from_id}` to `{to_id}`.")
        try:
            await bot.send_message(to_id, "🎁 **Subscription Transferred!**\nYour premium access has been moved to this account.")
        except: pass
    else:
        await event.reply(f"❌ **Transfer Failed:** {msg}")

# --- 5. CANCEL SUB: /cancel <id> ---
@bot.on(events.NewMessage(pattern=r'/cancel (\d+)'))
async def cancel_handler(event):
    if not is_sudo(event.sender_id): return
    user_id = int(event.pattern_match.group(1))
    
    await cancel_subscription(user_id)
    await event.reply(f"📉 **Subscription Cancelled:** User `{user_id}` plan is now expired.")

# --- 6. STATS: /stats ---
@bot.on(events.NewMessage(pattern='/stats'))
async def bot_stats(event):
    if not is_sudo(event.sender_id): return
    
    total_users = await users_db.count_documents({})
    active_subs = await subs_db.count_documents({"status": "active", "expiry_date": {"$gt": datetime.datetime.now()}})
    
    text = (
        "📊 **System Wide Statistics**\n\n"
        f"👤 **Total Users:** `{total_users}`\n"
        f"💎 **Active Premium:** `{active_subs}`\n"
        f"🛡️ **Sudo Users:** `{len(SUDO_USERS)}`"
    )
    await event.reply(text)

# --- 7. USER INFO: /info <id> ---
@bot.on(events.NewMessage(pattern=r'/info (\d+)'))
async def user_info(event):
    if not is_sudo(event.sender_id): return
    
    user_id = int(event.pattern_match.group(1))
    user_data = await users_db.find_one({"user_id": user_id})
    status, time_left = await get_sub_info(user_id)
    
    if not user_data:
        await event.reply("❌ User not found in database.")
        return
    
    readable_time = str(time_left).split('.')[0] if time_left else "N/A"
    
    info_text = (
        "👤 **Detailed User Profile**\n\n"
        f"🆔 **User ID:** `{user_id}`\n"
        f"🔑 **Session:** `{'Linked ✅' if user_data.get('session') else 'Missing ❌'}`\n"
        f"💳 **Plan Status:** `{status}`\n"
        f"⏳ **Remaining:** `{readable_time}`"
    )
    await event.reply(info_text)
