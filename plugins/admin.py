import datetime
import asyncio
from bot_instance import bot 
from telethon import events, Button, errors
from config import ADMIN_ID, SUDO_USERS
from database import (
    add_subscription, 
    users_db, 
    subs_db, 
    ban_user, 
    unban_user, 
    transfer_subscription, 
    cancel_subscription,
    get_sub_info,
    DB_FILE
)
import aiosqlite

# --- HELPER: CHECK IF SUDO ---
def is_sudo(user_id):
    return user_id in SUDO_USERS

# --- 1. GRANULAR APPROVE: /approve <id> <days> <hours> <mins> ---
@bot.on(events.NewMessage(pattern=r'/approve (\d+) (\d+)(?: (\d+))?(?: (\d+))?'))
async def manual_approve(event):
    if not is_sudo(event.sender_id): return
    
    try:
        user_id = int(event.pattern_match.group(1))
        days = int(event.pattern_match.group(2))
        hours = int(event.pattern_match.group(3) or 0)
        minutes = int(event.pattern_match.group(4) or 0)
        
        expiry = await add_subscription(user_id, days, hours, minutes)
        
        time_str = f"{days}d {hours}h {minutes}m"
        await event.reply(
            f"✅ **Subscription Added Manually!**\n\n"
            f"👤 **User:** `{user_id}`\n"
            f"⏳ **Duration:** `{time_str}`\n"
            f"📅 **New Expiry:** `{expiry.strftime('%Y-%m-%d %H:%M:%S')}`"
        )
        
        try:
            await bot.send_message(
                user_id, 
                f"🎉 **Premium Access Granted!**\n\nAdmin has manually activated your subscription for **{time_str}**.\nYou can now use all premium modules.",
                buttons=[[Button.inline("⚙️ Open Modules", data="modules_main")]]
            )
        except: pass
    except Exception as e:
        await event.reply(f"❌ **Error:** `{e}`")

# --- 2. BAN USER: /ban <id> ---
@bot.on(events.NewMessage(pattern=r'/ban (\d+)'))
async def ban_handler(event):
    if not is_sudo(event.sender_id): return
    user_id = int(event.pattern_match.group(1))
    
    await ban_user(user_id)
    await event.reply(f"🚫 **User Banned:** `{user_id}` has been restricted from using the bot.")
    try:
        await bot.send_message(user_id, "⚠️ **Notice:** Your access to Userbot Community has been revoked by an Admin.")
    except: pass

# --- 3. UNBAN USER: /unban <id> ---
@bot.on(events.NewMessage(pattern=r'/unban (\d+)'))
async def unban_handler(event):
    if not is_sudo(event.sender_id): return
    user_id = int(event.pattern_match.group(1))
    
    await unban_user(user_id)
    await event.reply(f"✅ **User Unbanned:** `{user_id}` can now use the bot services again.")

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
            await bot.send_message(to_id, "🎁 **Subscription Transferred!**\nYour premium plan has been moved to this account.")
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
    
    # Using the proxy functions for SQLite
    total_users = await users_db.count_documents({})
    active_subs = await subs_db.count_documents({})
    
    text = (
        "📊 **Global Empire Statistics**\n\n"
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
    
    # Fetch from SQLite
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT session FROM users WHERE user_id = ?', (user_id,)) as c:
            row = await c.fetchone()
            has_session = "Linked ✅" if row else "Missing ❌"

    status, time_left = await get_sub_info(user_id)
    readable_time = str(time_left).split('.')[0] if time_left else "N/A"
    
    info_text = (
        "👤 **User Information**\n\n"
        f"🆔 **User ID:** `{user_id}`\n"
        f"🔑 **Session:** `{has_session}`\n"
        f"💳 **Plan Status:** `{status}`\n"
        f"⏳ **Remaining:** `{readable_time}`"
    )
    await event.reply(info_text)

# --- 8. BROADCAST: /broadcast <message> ---
@bot.on(events.NewMessage(pattern=r'/broadcast (.*)'))
async def broadcast_handler(event):
    if event.sender_id != ADMIN_ID: return # Only Owner can broadcast
    
    msg = event.pattern_match.group(1)
    status_msg = await event.reply("📣 **Broadcasting message to all users...**")
    
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT user_id FROM users') as cursor:
            rows = await cursor.fetchall()

    done = 0
    failed = 0
    for row in rows:
        try:
            await bot.send_message(row[0], msg)
            done += 1
            await asyncio.sleep(0.3) # Prevent flood limit
        except errors.FloodWaitError as e:
            await asyncio.sleep(e.seconds)
        except:
            failed += 1
            
    await status_msg.edit(f"📣 **Broadcast Completed!**\n\n✅ **Sent:** {done}\n❌ **Failed:** {failed}")

# --- 9. RESET TRIAL: /reset_trial <id> ---
@bot.on(events.NewMessage(pattern=r'/reset_trial (\d+)'))
async def reset_trial_handler(event):
    if not is_sudo(event.sender_id): return
    user_id = int(event.pattern_match.group(1))
    
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('DELETE FROM trials WHERE user_id = ?', (user_id,))
        await db.commit()
        
    await event.reply(f"🎁 **Trial Reset:** User `{user_id}` can now claim the free trial again.")
