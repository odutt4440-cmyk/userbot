import datetime
import os
import shutil 
import asyncio
import aiosqlite
from bot_instance import bot 
from telethon import events, Button, errors
from config import ADMIN_ID
from core.session_manager import ACTIVE_CLIENTS, SessionManager
from database import (
    add_subscription, 
    ban_user, 
    unban_user, 
    is_banned,
    transfer_subscription, 
    cancel_subscription,
    get_sub_info,
    remove_user_session,
    has_claimed_trial,
    is_staff,
    get_sudo_info, 
    DB_FILE,
    set_plan_status,
    is_plan_available,
    set_maintenance
)

# --- NEW SUDO POWER HELPERS ---

async def get_sudo_powers(user_id):
    """DB se sudo ki powers check karne ke liye"""
    if user_id == ADMIN_ID:
        return {"can_ban": 1, "can_pay": 1} # Owner has all powers
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT can_ban, can_pay FROM sudo_users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"can_ban": row[0], "can_pay": row[1]}
    return None

async def is_staff(user_id):
    """Check if user is either Admin or any Sudo"""
    if user_id == ADMIN_ID: return True
    powers = await get_sudo_powers(user_id)
    return powers is not None

# --- 1. SUDO MANAGEMENT (OWNER ONLY) ---

@bot.on(events.NewMessage(pattern=r'/addsudo (\d+) (\d) (\d)'))
async def add_sudo_handler(event):
    if event.sender_id != ADMIN_ID: return
    try:
        uid = int(event.pattern_match.group(1))
        can_ban = int(event.pattern_match.group(2)) # 1 for Yes, 0 for No
        can_pay = int(event.pattern_match.group(3)) # 1 for Yes, 0 for No
        
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute('INSERT OR REPLACE INTO sudo_users VALUES (?, ?, ?)', (uid, can_ban, can_pay))
            await db.commit()
        
        powers_msg = f"🚫 Ban: {'✅' if can_ban else '❌'} | 💳 Pay: {'✅' if can_pay else '❌'}"
        await event.reply(f"👤 **Sudo Added Successfully!**\n**ID:** `{uid}`\n**Powers:** {powers_msg}")
    except Exception as e:
        await event.reply(f"❌ **Error:** {e}")

@bot.on(events.NewMessage(pattern=r'/rmsudo (\d+)'))
async def rm_sudo_handler(event):
    if event.sender_id != ADMIN_ID: return
    uid = int(event.pattern_match.group(1))
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('DELETE FROM sudo_users WHERE user_id = ?', (uid,))
        await db.commit()
    await event.reply(f"❌ **Sudo Removed:** `{uid}` is no longer staff.")

@bot.on(events.NewMessage(pattern='/sudolist'))
async def sudo_list(event):
    if event.sender_id != ADMIN_ID: return
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT * FROM sudo_users') as cursor:
            rows = await cursor.fetchall()
            if not rows: return await event.reply("No sudo users found.")
            msg = "🛡️ **Empire Staff List:**\n\n"
            for r in rows:
                msg += f"👤 `{r[0]}` | Ban: {r[1]} | Pay: {r[2]}\n"
            await event.reply(msg)

# --- 2. ACTIVE SESSIONS & LOGOUT ---

@bot.on(events.NewMessage(pattern='/active'))
async def active_sessions(event):
    if not await is_staff(event.sender_id): return
    if not ACTIVE_CLIENTS:
        return await event.reply("info: No userbot sessions are currently running.")
    
    msg = "🚀 **Active Sessions:**\n\n"
    async with aiosqlite.connect(DB_FILE) as db:
        for uid in list(ACTIVE_CLIENTS.keys()):
            async with db.execute('SELECT phone FROM users WHERE user_id = ?', (uid,)) as c:
                row = await c.fetchone()
                msg += f"👤 `{uid}` | 📱 `{row[0] if row else 'N/A'}`\n"
    await event.reply(msg)

@bot.on(events.NewMessage(pattern=r'/logout (\d+)'))
async def logout_handler(event):
    if not await is_staff(event.sender_id): return
    user_id = int(event.pattern_match.group(1))
    if user_id in ACTIVE_CLIENTS:
        try:
            client = ACTIVE_CLIENTS[user_id]
            await client.log_out() 
            await client.disconnect()
            del ACTIVE_CLIENTS[user_id]
        except: pass
    await remove_user_session(user_id)
    await event.reply(f"✅ **Logout Successful:** `{user_id}` terminated.")



# --- 2. BAN USER (With Reason Support) ---
@bot.on(events.NewMessage(pattern=r'/ban (\d+)(?:\s+(.*))?'))
async def ban_handler(event):
    # Power check: Ban power needed
    p = await get_sudo_powers(event.sender_id)
    if not p or not p['can_ban']: 
        return await event.reply("❌ You don't have 'Ban' permission.")
    
    user_id = int(event.pattern_match.group(1))
    reason = event.pattern_match.group(2) or "No reason provided by Admin."
    
    await ban_user(user_id, reason)
    
    # Session stop logic
    if user_id in ACTIVE_CLIENTS:
        await SessionManager.stop_userbot(user_id)
        
    await event.reply(f"🚫 **User Banned:** `{user_id}`\n📝 **Reason:** {reason}")
    
    try:
        await bot.send_message(user_id, f"❌ **You have been banned!**\n\n**Reason:** {reason}\n\nContact support if this is a mistake.")
    except: pass
        
@bot.on(events.NewMessage(pattern=r'/unban (\d+)'))
async def unban_handler(event):
    p = await get_sudo_powers(event.sender_id)
    if not p or not p['can_ban']: return
    user_id = int(event.pattern_match.group(1))
    await unban_user(user_id)
    await event.reply(f"✅ **User Unbanned:** `{user_id}`.")

# --- 3. MANUAL APPROVE: /approve <id> <plan> <d> <h> <m> ---
@bot.on(events.NewMessage(pattern=r'/approve (\d+) (\w+) (\d+)(?: (\d+))?(?: (\d+))?'))
async def manual_approve(event):
    # Power check: Pay power needed
    p = await get_sudo_powers(event.sender_id)
    if not p or not p['can_pay']: return
    
    try:
        user_id = int(event.pattern_match.group(1))
        
        # 🔥 1. THE DOUBLE-PLAN PROTECTION
        status, _ = await get_sub_info(user_id)
        if status == "Active":
            return await event.reply(
                "❌ **Error:** This user already has an active premium plan.\n\n"
                "Kindly use `/cancel` first to remove the current plan before re-approving."
            )

        # 2. Parsing logic
        plan_raw = event.pattern_match.group(2).replace("_", " ") # Ultra_Standard -> Ultra Standard
        days = int(event.pattern_match.group(3))
        hours = int(event.pattern_match.group(4) or 0)
        minutes = int(event.pattern_match.group(5) or 0)
        
        # 3. Call DB (Fixed arguments)
        from database import add_subscription
        expiry = await add_subscription(
            user_id, 
            plan_type=plan_raw, 
            days=days, 
            hours=hours, 
            minutes=minutes
        )
        
        time_str = f"{days}d {hours}h {minutes}m"
        await event.reply(
            f"✅ **Manual Approval Done!**\n\n"
            f"👤 **User:** `{user_id}`\n"
            f"💎 **Plan:** {plan_raw}\n"
            f"⏳ **Duration:** {time_str}"
        )
        
        # Notify User
        try:
            await bot.send_message(
                user_id, 
                f"🎉 **Premium Activated!**\n\nAdmin has activated your **{plan_raw}** plan for **{time_str}**.",
                buttons=[[Button.inline("⚙️ Open Modules", data="modules_main")]]
            )
        except: pass

    except Exception as e:
        await event.reply(f"❌ **Error:** `{e}`")

# --- 4. CANCEL PLAN: /cancel <id> ---
@bot.on(events.NewMessage(pattern=r'/cancel (\d+)'))
async def cancel_handler(event):
    p = await get_sudo_powers(event.sender_id)
    if not p or not p['can_pay']: return
    
    user_id = int(event.pattern_match.group(1))
    
    # 1. Reset in Database (Expired status + Reset expiry_date)
    await cancel_subscription(user_id)
    
    # 2. Kill Active Bot Session
    if user_id in ACTIVE_CLIENTS:
        await SessionManager.stop_userbot(user_id)
        
    await event.reply(f"📉 **Plan Terminated:** User `{user_id}` premium access removed.")
    try:
        await bot.send_message(user_id, "⚠️ **Notice:** Your premium subscription has been cancelled by an Admin.")
    except: pass

# --- 5. INFO & STATS ---

@bot.on(events.NewMessage(pattern=r'/info (\d+)'))
async def user_info(event):
    if not await is_staff(event.sender_id): return
    user_id = int(event.pattern_match.group(1))
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT phone, last_login FROM users WHERE user_id = ?', (user_id,)) as c:
            row = await c.fetchone()
            phone = row[0] if row else "N/A"
    status, time_left = await get_sub_info(user_id)
    claimed = await has_claimed_trial(user_id)
    trial_status = "Claimed (0) ❌" if claimed else "Available (1) ✅"
    is_live = "Online 🟢" if user_id in ACTIVE_CLIENTS else "Offline 🔴"
    await event.reply(f"👤 **Info:** `{user_id}`\n📱 **Phone:** `{phone}`\n🎁 **Trial:** {trial_status}\n📡 **Status:** {is_live}\n💳 **Plan:** {status}\n⏳ **Left:** {str(time_left).split('.')[0] if time_left else '0'}")

@bot.on(events.NewMessage(pattern='/stats'))
async def bot_stats(event):
    if not await is_staff(event.sender_id): return
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT COUNT(*) FROM users') as c1: u_count = (await c1.fetchone())[0]
        async with db.execute('SELECT COUNT(*) FROM subscriptions WHERE status="active"') as c2: s_count = (await c2.fetchone())[0]
    await event.reply(f"📊 **Stats:** Users: {u_count} | Active: {s_count} | Live: {len(ACTIVE_CLIENTS)}")

# --- 9. GET DATABASE: /getdb ---
@bot.on(events.NewMessage(pattern='/getdb'))
async def get_db_file(event):
    # Sirf staff hi DB mangwa sakte hain
    if not await is_staff(event.sender_id): return
    
    status_msg = await event.reply("⏳ **Preparing database file...**")
    try:
        if os.path.exists(DB_FILE):
            # Live DB ko copy karke bhejenge taaki 'Locked' error na aaye
            import shutil
            temp_db = "temp_backup.db"
            shutil.copy(DB_FILE, temp_db)
            
            await bot.send_file(
                event.chat_id, 
                temp_db, 
                caption=f"📁 **Empire Community Database**\n📅 **Exported on:** `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
            )
            os.remove(temp_db)
            await status_msg.delete()
        else:
            await status_msg.edit("❌ **Error:** Database file not found.")
    except Exception as e:
        await status_msg.edit(f"❌ **Failed to export DB:** `{e}`")
# --- 6. OWNER ONLY ---

@bot.on(events.NewMessage(pattern=r'/broadcast (.*)'))
async def broadcast_handler(event):
    if not await is_staff(event.sender_id): return # Fixed: Staff can broadcast now
    msg = event.pattern_match.group(1)
    status_msg = await event.reply("📣 Broadcasting...")
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT user_id FROM users') as cursor: rows = await cursor.fetchall()
    done, failed = 0, 0
    for row in rows:
        try: await bot.send_message(row[0], msg); done += 1; await asyncio.sleep(0.3)
        except: failed += 1
    await status_msg.edit(f"📣 Broadcast Finished!\n✅ Sent: {done} | ❌ Failed: {failed}")

@bot.on(events.NewMessage(pattern=r'/toggleplan (\w+) (on|off)'))
async def toggle_plan_handler(event):
    p = await get_sudo_powers(event.sender_id)
    if not p or not p['can_pay']: return

    plan_key = event.pattern_match.group(1).lower()
    status = event.pattern_match.group(2).lower()
    
    await set_plan_status(plan_key, status)
    
    emoji = "✅ ENABLED" if status == "on" else "🚫 DISABLED"
    await event.reply(f"⚙️ **Plan Manager:**\nPlan `{plan_key.upper()}` is now {emoji}.")
    
    if LOG_GROUP:
        await bot.send_message(LOG_GROUP, f"🛠️ **Admin Action:** Plan `{plan_key}` was toggled `{status}` by `{event.sender_id}`")

@bot.on(events.NewMessage(pattern=r'/reset_trial (\d+)'))
async def reset_trial_handler(event):
    if event.sender_id != ADMIN_ID: return
    u = int(event.pattern_match.group(1))
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('DELETE FROM trials WHERE user_id = ?', (u,))
        await db.commit()
    await event.reply(f"🎁 Trial reset for `{u}`.")

@bot.on(events.NewMessage(pattern=r'/transfer (\d+) (\d+)'))
async def transfer_handler(event):
    if event.sender_id != ADMIN_ID: return
    f, t = int(event.pattern_match.group(1)), int(event.pattern_match.group(2))
    s, m = await transfer_subscription(f, t)
    await event.reply(f"♻️ {m}")

# --- 8. MAINTENANCE MODE (Owner Only) ---
# Usage: /maintenance on <message> OR /maintenance off
@bot.on(events.NewMessage(pattern=r'/maintenance (on|off)(?:\s+(.*))?'))
async def maintenance_handler(event):
    if event.sender_id != ADMIN_ID: 
        return # Sudo users maintenance control nahi kar sakte

    status = event.pattern_match.group(1).lower()
    maint_text = event.pattern_match.group(2) or "Bot is under maintenance for updates. Please try again later."
    
    await set_maintenance(status, maint_text)
    
    status_emoji = "🛠️ ON" if status == "on" else "✅ OFF"
    await event.reply(f"⚙️ **Maintenance Mode:** {status_emoji}\n\n**Display Text:** {maint_text}")


# --- STAFF HELP CENTER (Owner & Sudo Only) ---
@bot.on(events.NewMessage(pattern=r'(?i)^/sudohelp'))
async def sudo_help(event):
    # 🛡️ Staff Check: Sirf Owner aur Sudo hi dekh sakte hain
    from database import is_staff, get_sudo_info
    
    if not await is_staff(event.sender_id):
        return # Normal users ke liye bot reply hi nahi karega

    # Powers fetch karo commands dikhane ke liye
    powers = await get_sudo_info(event.sender_id)
    is_owner = (event.sender_id == ADMIN_ID)

    help_msg = "🛡️ **Empire Admin Control Center**\n\n"
    help_msg += "Welcome to the professional management suite. Below are the commands you can use based on your power level.\n\n"

    # --- OWNER SECTION ---
    if is_owner:
        help_msg += "👑 **Owner Privileges (Exclusive):**\n"
        help_msg += "• `/addsudo <ID> <Ban> <Pay>` - Add new staff\n"
        help_msg += "  👉 _Ex: /addsudo 1234567 1 1_ (Full Power)\n"
        help_msg += "• `/rmsudo <ID>` - Remove a staff member\n"
        help_msg += "  👉 _Ex: /rmsudo 1234567_\n"
        help_msg += "• `/sudolist` - View current staff members\n"
        help_msg += "• `/broadcast <Msg>` - Message all bot users\n"
        help_msg += "  👉 _Ex: /broadcast Bot updated!_\n"
        help_msg += "• `/transfer <FromID> <ToID>` - Move subscription\n"
        help_msg += "  👉 _Ex: /transfer 111 222_\n"
        help_msg += "• `/reset_trial <ID>` - Allow trial again\n\n"
        help_msg += "• `/maintenance <on/off> <msg>` - Master Switch\n"

    # --- BAN MANAGEMENT ---
    if is_owner or (powers and powers[0] == 1): # can_ban power
        help_msg += "🚫 **Security & Bans:**\n"
        help_msg += "• `/ban <ID> <Reason>` - Block with reason\n"
        help_msg += "  👉 _Ex: /ban 1234567_reason\n"
        help_msg += "• `/unban <ID>` - Restore user access\n\n"

    # --- FINANCIAL & SYSTEM TOOLS ---
    if is_owner or (powers and powers[1] == 1): # can_pay power
        help_msg += "💳 **Management & Billing:**\n"
        help_msg += "• `/approve <ID> <Plan> <Days>` - Approve any plan\n"
        help_msg += "  👉 _Ex: /approve 123 Ultra_Empire 30_\n"
        help_msg += "  👉 _Ex: /approve 123 30 0 0_ (Add 30 days)\n"
        help_msg += "  👉 _Ex: /approve 123 0 2 30_ (Add 2hr 30m)\n"
        help_msg += "• `/cancel <ID>` - Terminate premium plan\n"
        help_msg += "• `/logout <ID>` - Permanent session termination\n"
        help_msg += "• `/active` - List currently running userbots\n"
        help_msg += "• `/info <ID>` - Check phone, trial & expiry info\n"
        help_msg += "• `/stats` - View global bot statistics\n"
        help_msg += "• `/getdb` - Download the SQLite database file\n"
        help_msg += "• `/toggleplan <key> <on/off>` - Enable/Disable a plan\n"
        help_msg += "  👉 _Ex: /toggleplan u_std_15 off_\n"

    await event.reply(help_msg)
