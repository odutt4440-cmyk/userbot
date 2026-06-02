import aiosqlite
import datetime
import logging
import json
import os
from config import ADMIN_ID

log = logging.getLogger(__name__)
DB_FILE = "community.db"

# --- DB INITIALIZATION ---
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        # Users Table - Added 'phone' column
        await db.execute('''CREATE TABLE IF NOT EXISTS users 
            (user_id INTEGER PRIMARY KEY, session TEXT, phone TEXT, last_login TEXT)''')
        
        await db.execute('''CREATE TABLE IF NOT EXISTS subscriptions 
            (user_id INTEGER PRIMARY KEY, status TEXT, expiry_date TEXT)''')
        
        await db.execute('''CREATE TABLE IF NOT EXISTS game_state 
            (user_id INTEGER, game_name TEXT, data TEXT, PRIMARY KEY (user_id, game_name))''')
        
        await db.execute('''CREATE TABLE IF NOT EXISTS banned 
            (user_id INTEGER PRIMARY KEY, banned_at TEXT)''')

        await db.execute('''CREATE TABLE IF NOT EXISTS trials 
            (user_id INTEGER PRIMARY KEY, claimed_at TEXT)''')
            
        await db.execute('''CREATE TABLE IF NOT EXISTS settings 
            (key TEXT PRIMARY KEY, value TEXT)''')

        await db.execute('''CREATE TABLE IF NOT EXISTS warnings 
            (user_id INTEGER, chat_id INTEGER, count INTEGER, PRIMARY KEY (user_id, chat_id))''')
        await db.execute('''CREATE TABLE IF NOT EXISTS sudo_users 
            (user_id INTEGER PRIMARY KEY, can_ban INTEGER, can_pay INTEGER)''')
        
        await db.commit()
    log.info("✅ SQLite Engine: Database ready with Phone support.")

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

# --- TRIAL LOGIC ---
async def has_claimed_trial(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT user_id FROM trials WHERE user_id = ?', (user_id,)) as cursor:
            return True if await cursor.fetchone() else False

async def claim_trial(user_id):
    if await has_claimed_trial(user_id):
        return False, "You have already used your free trial."
    expiry = await add_subscription(user_id, days=1)
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('INSERT INTO trials (user_id, claimed_at) VALUES (?, ?)', 
            (user_id, datetime.datetime.now().isoformat()))
        await db.commit()
    return True, expiry

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
async def ban_user(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('INSERT OR REPLACE INTO banned (user_id, banned_at) VALUES (?, ?)', 
            (user_id, datetime.datetime.now().isoformat()))
        await db.commit()

async def unban_user(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('DELETE FROM banned WHERE user_id = ?', (user_id,))
        await db.commit()

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

async def add_subscription(user_id, days=0, hours=0, minutes=0):
    now = datetime.datetime.now()
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT expiry_date FROM subscriptions WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                old_expiry = datetime.datetime.fromisoformat(row[0])
                base_date = old_expiry if old_expiry > now else now
            else:
                base_date = now
        new_expiry = base_date + datetime.timedelta(days=days, hours=hours, minutes=minutes)
        await db.execute('''INSERT OR REPLACE INTO subscriptions (user_id, status, expiry_date) 
            VALUES (?, ?, ?)''', (user_id, "active", new_expiry.isoformat()))
        await db.commit()
        return new_expiry

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
