import datetime
import asyncio
import aiosqlite
from bot_instance import bot 
from telethon import events, Button, errors
from config import ADMIN_ID, SUDO_USERS
from core.session_manager import ACTIVE_CLIENTS, SessionManager # ACTIVE_CLIENTS import kiya
from database import (
    add_subscription, 
    users_db, 
    subs_db, 
    ban_user, 
    unban_user, 
    transfer_subscription, 
    cancel_subscription,
    get_sub_info,
    remove_user_session, # Naya function
    DB_FILE
)

# --- HELPER: CHECK IF SUDO ---
def is_sudo(user_id):
    return user_id in SUDO_USERS

# --- 1. LIST ACTIVE SESSIONS: /active ---
@bot.on(events.NewMessage(pattern='/active'))
async def active_sessions(event):
    if not is_sudo(event.sender_id): return
    
    if not ACTIVE_CLIENTS:
        await event.reply("info: No userbot sessions are currently running on the server.")
        return

    msg = "🚀 **Active Userbot Sessions:**\n\n"
    async with aiosqlite.connect(DB_FILE) as db:
        for user_id in ACTIVE_CLIENTS.keys():
            async with db.execute('SELECT phone FROM users WHERE user_id = ?', (user_id,)) as c:
                row = await cursor.fetchone()
                phone = row[0] if row else "Unknown"
                msg += f"👤 **ID:** `{user_id}` | 📱 **Phone:** `{phone}`\n"
    
    await event.reply(msg)

# --- 2. LOGOUT & TERMINATE: /logout <id> ---
@bot.on(events.NewMessage(pattern=r'/logout (\d+)'))
async def logout_handler(event):
    if not is_sudo(event.sender_id): return
    
    user_id = int(event.pattern_match.group(1))
    
    # Check if session exists in memory
    if user_id in ACTIVE_CLIENTS:
        try:
            client = ACTIVE_CLIENTS[user_id]
            # Telegram servers se session permanently delete karega (Account Safe)
            await client.log_out() 
            await client.disconnect()
            del ACTIVE_CLIENTS[user_id]
        except Exception as e:
            print(f"Logout Error: {e}")

    # Database se entry uda do
    await remove_user_session(user_id)
    
    await event.reply(f"✅ **Logout Successful!**\n\nUser `{user_id}` has been logged out from the server and the session has been terminated from their devices.")
    
    try:
        await bot.send_message(user_id, "⚠️ **Security Notice:** Your userbot session has been terminated and logged out by the Admin.")
    except: pass

# --- 3. GRANULAR APPROVE: /approve <id> <days> <hours> <mins> ---
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
        await event.reply(f"✅ **Subscription Added!**\nUser: `{user_id}`\nDuration: `{time_str}`")
        await bot.send_message(user_id, f"🎉 Premium access granted for {time_str}!", buttons=[[Button.inline("⚙️ Modules", data="modules_main")]])
    except Exception as e:
        await event.reply(f"❌ Error: {e}")

# --- 4. USER INFO: /info <id> (Updated with Phone) ---
@bot.on(events.NewMessage(pattern=r'/info (\d+)'))
async def user_info(event):
    if not is_sudo(event.sender_id): return
    user_id = int(event.pattern_match.group(1))
    
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT phone, last_login FROM users WHERE user_id = ?', (user_id,)) as c:
            row = await c.fetchone()
            phone = row[0] if row else "N/A"
            last_login = row[1] if row else "Never"

    status, time_left = await get_sub_info(user_id)
    rem = str(time_left).split('.')[0] if time_left else "N/A"
    is_active = "Online 🟢" if user_id in ACTIVE_CLIENTS else "Offline 🔴"
    
    info_text = (
        "👤 **User Management Profile**\n\n"
        f"🆔 **User ID:** `{user_id}`\n"
        f"📱 **Phone:** `{phone}`\n"
        f"📡 **Bot Status:** `{is_active}`\n"
        f"💳 **Subscription:** `{status}`\n"
        f"⏳ **Remaining Time:** `{rem}`\n"
        f"📅 **Last Login:** `{last_login}`"
    )
    await event.reply(info_text)

# --- 5. BROADCAST, BAN, UNBAN, TRANSFER (Same as before) ---
@bot.on(events.NewMessage(pattern=r'/broadcast (.*)'))
async def broadcast_handler(event):
    if event.sender_id != ADMIN_ID: return
    msg = event.pattern_match.group(1)
    status_msg = await event.reply("📣 Broadcasting...")
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT user_id FROM users') as cursor:
            rows = await cursor.fetchall()
    done, failed = 0, 0
    for row in rows:
        try:
            await bot.send_message(row[0], msg)
            done += 1
            await asyncio.sleep(0.3)
        except errors.FloodWaitError as e: await asyncio.sleep(e.seconds)
        except: failed += 1
    await status_msg.edit(f"📣 Broadcast Done!\n✅ Sent: {done} | ❌ Failed: {failed}")

@bot.on(events.NewMessage(pattern=r'/ban (\d+)'))
async def ban_handler(event):
    if not is_sudo(event.sender_id): return
    user_id = int(event.pattern_match.group(1))
    await ban_user(user_id)
    await event.reply(f"🚫 User `{user_id}` Banned.")

@bot.on(events.NewMessage(pattern=r'/unban (\d+)'))
async def unban_handler(event):
    if not is_sudo(event.sender_id): return
    user_id = int(event.pattern_match.group(1))
    await unban_user(user_id)
    await event.reply(f"✅ User `{user_id}` Unbanned.")

@bot.on(events.NewMessage(pattern=r'/transfer (\d+) (\d+)'))
async def transfer_handler(event):
    if not is_sudo(event.sender_id): return
    f, t = int(event.pattern_match.group(1)), int(event.pattern_match.group(2))
    s, m = await transfer_subscription(f, t)
    await event.reply(f"♻️ {m}" if s else f"❌ {m}")

@bot.on(events.NewMessage(pattern=r'/reset_trial (\d+)'))
async def reset_trial_handler(event):
    if not is_sudo(event.sender_id): return
    u = int(event.pattern_match.group(1))
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('DELETE FROM trials WHERE user_id = ?', (u,))
        await db.commit()
    await event.reply(f"🎁 Trial reset for `{u}`.")
