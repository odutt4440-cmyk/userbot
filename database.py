import aiosqlite
import datetime
import logging
import json
import os
from config import ADMIN_ID

log = logging.getLogger(__name__)
DB_FILE = "community.db"

# --- DB INITIALIZATION (Replace this function) ---
# --- DB INITIALIZATION (Updated with Plan Tier Logic) ---
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        # Core Tables
        await db.execute('''CREATE TABLE IF NOT EXISTS users 
            (user_id INTEGER PRIMARY KEY, session TEXT, phone TEXT, last_login TEXT)''')
        
        # FIX: Ensure plan column is part of the table structure
        await db.execute('''CREATE TABLE IF NOT EXISTS subscriptions 
            (user_id INTEGER PRIMARY KEY, status TEXT, expiry_date TEXT, plan TEXT)''')
            
        await db.execute('''CREATE TABLE IF NOT EXISTS game_state 
            (user_id INTEGER, game_name TEXT, data TEXT, PRIMARY KEY (user_id, game_name))''')
        
        # Banned table with reason support
        await db.execute('''CREATE TABLE IF NOT EXISTS banned 
            (user_id INTEGER PRIMARY KEY, banned_at TEXT, reason TEXT)''')

        await db.execute('''CREATE TABLE IF NOT EXISTS trials 
            (user_id INTEGER PRIMARY KEY, claimed_at TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS settings 
            (key TEXT PRIMARY KEY, value TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS warnings 
            (user_id INTEGER, chat_id INTEGER, count INTEGER, PRIMARY KEY (user_id, chat_id))''')
        await db.execute('''CREATE TABLE IF NOT EXISTS sudo_users 
            (user_id INTEGER PRIMARY KEY, can_ban INTEGER, can_pay INTEGER)''')

        # --- CAMPAIGN TABLES (Keeping as requested) ---
        await db.execute('''CREATE TABLE IF NOT EXISTS campaign_accounts 
            (user_id INTEGER, phone TEXT, session TEXT, PRIMARY KEY (user_id, phone))''')
        await db.execute('''CREATE TABLE IF NOT EXISTS campaign_config 
            (user_id INTEGER PRIMARY KEY, target TEXT, messages TEXT, 
             delay_min INTEGER, delay_max INTEGER, delete_after INTEGER, is_running INTEGER)''')

        # 🔥 AUTO-MIGRATION FIX 1: Missing column fix for 'reason'
        try:
            await db.execute('SELECT reason FROM banned LIMIT 1')
        except aiosqlite.OperationalError:
            await db.execute('ALTER TABLE banned ADD COLUMN reason TEXT DEFAULT "No reason provided"')
            log.info("Migration: Added missing 'reason' column to banned table.")

        # 🔥 AUTO-MIGRATION FIX 2: Missing column fix for 'plan' tier
        try:
            await db.execute('SELECT plan FROM subscriptions LIMIT 1')
        except aiosqlite.OperationalError:
            await db.execute('ALTER TABLE subscriptions ADD COLUMN plan TEXT DEFAULT "Standard"')
            log.info("Migration: Added missing 'plan' column to subscriptions table.")

        await db.commit()
    log.info("✅ SQLite Engine: All tables and columns (Plan Tier Ready) verified.")
    
# --- SETTINGS FUNCTIONS ---
async def get_setting(key):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT value FROM settings WHERE key = ?', (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def set_setting(key, value):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        await db.commit()

# --- PLAN MANAGEMENT LOGIC ---

async def set_plan_status(plan_key, status):
    """Plan ko enable/disable karne ke liye. status: 'on'/'off'"""
    # plan_key examples: standard_15, ultra_emp_30, etc.
    await set_setting(f"STATUS_{plan_key.upper()}", status)

async def is_plan_available(plan_key):
    """Check karega ki plan chalu hai ya band"""
    # Default 'on' rahega agar setting nahi mili
    res = await get_setting(f"STATUS_{plan_key.upper()}")
    return res != "off"

# --- TRIAL LOGIC ---
async def has_claimed_trial(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT user_id FROM trials WHERE user_id = ?', (user_id,)) as cursor:
            return True if await cursor.fetchone() else False

# --- SUBSCRIPTION & TRIAL LOGIC (Plan Aware) ---

async def claim_trial(user_id):
    """Trial always grants 'Standard' plan for 24 hours"""
    if await has_claimed_trial(user_id):
        return False, "You have already used your free trial."
    
    # 1 Day Standard Plan
    expiry = await add_subscription(user_id, plan_type="Standard", days=1)
    
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('INSERT INTO trials VALUES (?, ?)', (user_id, datetime.datetime.now().isoformat()))
        await db.commit()
    return True, expiry

# --- SUBSCRIPTION LOGIC (Updated to accept Plan Type) ---

async def add_subscription(user_id, plan_type="Standard", days=0, hours=0, minutes=0):
    """
    Admin ab plan_type pass karega: 
    'Standard', 'Empire', 'Ultra Standard', ya 'Ultra Empire'
    """
    now = datetime.datetime.now()
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT expiry_date FROM subscriptions WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                try:
                    # Purani expiry date uthao
                    old_expiry = datetime.datetime.fromisoformat(row[0])
                    # Agar abhi bhi valid hai toh uske aage time add karo, warna aaj se
                    base_date = old_expiry if old_expiry > now else now
                except:
                    base_date = now
            else:
                base_date = now
        
        # Naya expiry time calculate karo
        new_expiry = base_date + datetime.timedelta(days=days, hours=hours, minutes=minutes)
        
        # 🔥 FIX: SQL query me 'plan' column include kiya hai
        await db.execute('''INSERT OR REPLACE INTO subscriptions (user_id, status, expiry_date, plan) 
            VALUES (?, ?, ?, ?)''', (user_id, "active", new_expiry.isoformat(), plan_type))
        await db.commit()
        return new_expiry
        
# --- USER SESSION FUNCTIONS (Updated to save Phone) ---

async def save_user_session(user_id, string_session, phone="N/A"):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''INSERT OR REPLACE INTO users (user_id, session, phone, last_login) 
            VALUES (?, ?, ?, ?)''', (user_id, string_session, phone, datetime.datetime.now().isoformat()))
        await db.commit()

async def get_user_session(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT session FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def remove_user_session(user_id):
    """Admin ke liye: Database se user ka session saaf karna"""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        await db.commit()

# --- ADMIN TOOLS (Get All Users) ---
async def get_all_users():
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT user_id, phone, last_login FROM users') as cursor:
            return await cursor.fetchall()

# --- BAN SYSTEM ---
async def ban_user(user_id, reason="No reason provided"):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('INSERT OR REPLACE INTO banned (user_id, banned_at, reason) VALUES (?, ?, ?)', 
            (user_id, datetime.datetime.now().isoformat(), reason))
        await db.commit()

async def unban_user(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('DELETE FROM banned WHERE user_id = ?', (user_id,))
        await db.commit()

async def get_ban_info(user_id):
    """Banned hone ka time aur wajah nikalne ke liye"""
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT banned_at, reason FROM banned WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone() # returns (time, reason) or None

async def is_banned(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT user_id FROM banned WHERE user_id = ?', (user_id,)) as cursor:
            return True if await cursor.fetchone() else False

# --- SUBSCRIPTION FUNCTIONS ---
async def is_subscribed(user_id):
    if user_id == ADMIN_ID: return True
    if await is_banned(user_id): return False
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT status, expiry_date FROM subscriptions WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] == "active":
                expiry = datetime.datetime.fromisoformat(row[1])
                return expiry > datetime.datetime.now()
    return False

async def get_sub_info(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT expiry_date FROM subscriptions WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row: return "No Plan", None
            expiry = datetime.datetime.fromisoformat(row[0])
            now = datetime.datetime.now()
            return ("Active", expiry - now) if expiry > now else ("Expired", None)

async def cancel_subscription(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        now = datetime.datetime.now().isoformat()
        await db.execute('UPDATE subscriptions SET status = "expired", expiry_date = ? WHERE user_id = ?', (now, user_id))
        await db.commit()

async def transfer_subscription(from_id, to_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT expiry_date FROM subscriptions WHERE user_id = ? AND status = "active"', (from_id,)) as cursor:
            row = await cursor.fetchone()
            if not row: return False, "Source has no sub."
            expiry = row[0]
        await db.execute('UPDATE subscriptions SET status = "expired" WHERE user_id = ?', (from_id,))
        await db.execute('INSERT OR REPLACE INTO subscriptions (user_id, status, expiry_date) VALUES (?, ?, ?)', (to_id, "active", expiry))
        await db.commit()
        return True, "Transferred."

# --- GAME STATE FUNCTIONS ---
async def set_game_state(user_id, game_name, data):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('INSERT OR REPLACE INTO game_state (user_id, game_name, data) VALUES (?, ?, ?)', 
            (user_id, game_name, json.dumps(data)))
        await db.commit()

async def get_game_state(user_id, game_name):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT data FROM game_state WHERE user_id = ? AND game_name = ?', (user_id, game_name)) as cursor:
            row = await cursor.fetchone()
            return json.loads(row[0]) if row else {}

async def handle_warn(user_id, chat_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT count FROM warnings WHERE user_id = ? AND chat_id = ?', (user_id, chat_id)) as cursor:
            row = await cursor.fetchone()
            new_count = (row[0] + 1) if row else 1
            await db.execute('INSERT OR REPLACE INTO warnings VALUES (?, ?, ?)', (user_id, chat_id, new_count))
            await db.commit()
            return new_count

async def add_sudo(user_id, can_ban=0, can_pay=0):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('INSERT OR REPLACE INTO sudo_users VALUES (?, ?, ?)', (user_id, can_ban, can_pay))
        await db.commit()

async def remove_sudo(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('DELETE FROM sudo_users WHERE user_id = ?', (user_id,))
        await db.commit()

async def get_sudo_info(user_id):
    """User ki powers check karne ke liye"""
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT can_ban, can_pay FROM sudo_users WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone()

async def list_all_sudos():
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT * FROM sudo_users') as cursor:
            return await cursor.fetchall()

# --- database.py me ye function add karo ---

async def is_staff(user_id):
    """Check if user is either Admin or any Sudo"""
    # config se ADMIN_ID check karo
    if user_id == ADMIN_ID: 
        return True
    
    # Check in sudo_users table
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT user_id FROM sudo_users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return True if row else False

# --- MAINTENANCE LOGIC ---
async def set_maintenance(status, message="Bot is under maintenance."):
    """Maintenance ON/OFF karne ke liye. status: 'on'/'off'"""
    await set_setting("MAINTENANCE_MODE", status)
    await set_setting("MAINTENANCE_TEXT", message)

async def get_maintenance():
    """Check maintenance status and message"""
    mode = await get_setting("MAINTENANCE_MODE")
    text = await get_setting("MAINTENANCE_TEXT")
    return (mode == "on", text or "Bot is under maintenance.")

# --- USER PROFILE DATA (For /me Command) ---

# --- USER PROFILE DATA (Updated: No Phone) ---
# --- USER PROFILE DATA (Updated: No Phone) ---

async def get_user_profile(user_id):
    """Returns Plan and Time details for /me command"""
    async with aiosqlite.connect(DB_FILE) as db:
        # Fetch subscription info
        async with db.execute('SELECT plan, expiry_date, status FROM subscriptions WHERE user_id = ?', (user_id,)) as c:
            s_row = await c.fetchone()
            
            if s_row and s_row[2] == "active":
                plan = s_row[0]
                expiry = datetime.datetime.fromisoformat(s_row[1])
                time_left = expiry - datetime.datetime.now()
                
                # Format time left readable string
                if time_left.total_seconds() > 0:
                    days = time_left.days
                    hours, remainder = divmod(time_left.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    rem_str = f"{days}d {hours}h {minutes}m"
                else:
                    rem_str = "Expired"
            else:
                plan = "Free / No Plan"
                rem_str = "N/A"
        
        return {"plan": plan, "time_left": rem_str}


async def get_user_plan_type(user_id):
    """Returns 'Empire' or 'Standard' for internal engine check"""
    if user_id == ADMIN_ID: return "Empire"
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT plan FROM subscriptions WHERE user_id = ? AND status = "active"', (user_id,)) as c:
            row = await c.fetchone()
            return row[0] if row else "None"
        
# --- database.py ke aakhir mein ye function add karo ---

async def global_security_check(event):
    """Universal security check for all plugins (DM Only + Ban + Maintenance)"""
    user_id = event.sender_id
    
    # 1. Maintenance Check (Admin is exempt)
    is_maint, maint_text = await get_maintenance()
    if is_maint and user_id != ADMIN_ID:
        await event.reply(f"🛠️ **Bot Under Maintenance**\n\n{maint_text}")
        return False
        
    # 2. Ban Check
    if await is_banned(user_id):
        ban_info = await get_ban_info(user_id) # Returns (time, reason)
        reason = ban_info[1] if ban_info else "No reason provided."
        await event.reply(f"🚫 **Access Denied!**\n\nYou have been banned from using this bot.\n\n**Reason:** `{reason}`")
        return False
        
    return True


# --- PROXY OBJECTS FOR ADMIN ---
class CollectionProxy:
    def __init__(self, table): self.table = table
    async def count_documents(self, query):
        async with aiosqlite.connect(DB_FILE) as db:
            sql = 'SELECT COUNT(*) FROM subscriptions WHERE status = "active"' if self.table == "subs" else 'SELECT COUNT(*) FROM users'
            async with db.execute(sql) as c:
                r = await c.fetchone()
                return r[0]

users_db = CollectionProxy("users")
subs_db = CollectionProxy("subs")
