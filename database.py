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
        # Users Table
        await db.execute('''CREATE TABLE IF NOT EXISTS users 
            (user_id INTEGER PRIMARY KEY, session TEXT, last_login TEXT)''')
        
        # Subscriptions Table
        await db.execute('''CREATE TABLE IF NOT EXISTS subscriptions 
            (user_id INTEGER PRIMARY KEY, status TEXT, expiry_date TEXT)''')
        
        # Game State Table
        await db.execute('''CREATE TABLE IF NOT EXISTS game_state 
            (user_id INTEGER, game_name TEXT, data TEXT, PRIMARY KEY (user_id, game_name))''')
        
        # Ban Table
        await db.execute('''CREATE TABLE IF NOT EXISTS banned 
            (user_id INTEGER PRIMARY KEY, banned_at TEXT)''')

        # Trial Tracker Table (Nayi table taaki ek banda ek hi baar trial le)
        await db.execute('''CREATE TABLE IF NOT EXISTS trials 
            (user_id INTEGER PRIMARY KEY, claimed_at TEXT)''')
        
        await db.commit()
    log.info("✅ SQLite Database & Trial System Initialized.")

# --- TRIAL LOGIC ---

async def has_claimed_trial(user_id):
    """Check karega ki user ne pehle trial liya hai ya nahi"""
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT user_id FROM trials WHERE user_id = ?', (user_id,)) as cursor:
            return True if await cursor.fetchone() else False

async def claim_trial(user_id):
    """User ko 24 ghante ka free access dene ke liye"""
    if await has_claimed_trial(user_id):
        return False, "You have already used your free trial."
    
    # Add 1 Day (24 hours)
    expiry = await add_subscription(user_id, days=1)
    
    # Record trial claim
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('INSERT INTO trials (user_id, claimed_at) VALUES (?, ?)', 
            (user_id, datetime.datetime.now().isoformat()))
        await db.commit()
    
    return True, expiry

# --- USER SESSION FUNCTIONS ---

async def save_user_session(user_id, string_session):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''INSERT OR REPLACE INTO users (user_id, session, last_login) 
            VALUES (?, ?, ?)''', (user_id, string_session, datetime.datetime.now().isoformat()))
        await db.commit()

async def get_user_session(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT session FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

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
                if expiry > datetime.datetime.now():
                    return True
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

async def cancel_subscription(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('UPDATE subscriptions SET status = "expired" WHERE user_id = ?', (user_id,))
        await db.commit()

async def transfer_subscription(from_id, to_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT expiry_date FROM subscriptions WHERE user_id = ? AND status = "active"', (from_id,)) as cursor:
            row = await cursor.fetchone()
            if not row: return False, "Source user has no active subscription."
            expiry = row[0]
            
        await db.execute('UPDATE subscriptions SET status = "expired" WHERE user_id = ?', (from_id,))
        await db.execute('''INSERT OR REPLACE INTO subscriptions (user_id, status, expiry_date) 
            VALUES (?, ?, ?)''', (to_id, "active", expiry))
        await db.commit()
        return True, "Transferred."

async def get_sub_info(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT expiry_date FROM subscriptions WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row: return "No Plan", None
            expiry = datetime.datetime.fromisoformat(row[0])
            now = datetime.datetime.now()
            return ("Active", expiry - now) if expiry > now else ("Expired", None)

# --- GAME STATE FUNCTIONS ---

async def set_game_state(user_id, game_name, data):
    async with aiosqlite.connect(DB_FILE) as db:
        data_str = json.dumps(data)
        await db.execute('''INSERT OR REPLACE INTO game_state (user_id, game_name, data) 
            VALUES (?, ?, ?)''', (user_id, game_name, data_str))
        await db.commit()

async def get_game_state(user_id, game_name):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT data FROM game_state WHERE user_id = ? AND game_name = ?', (user_id, game_name)) as cursor:
            row = await cursor.fetchone()
            return json.loads(row[0]) if row else {}

# --- PROXY OBJECTS (For Admin.py Compatibility) ---
class CollectionProxy:
    def __init__(self, table): self.table = table
    async def count_documents(self, query):
        async with aiosqlite.connect(DB_FILE) as db:
            if self.table == "subs":
                sql = 'SELECT COUNT(*) FROM subscriptions WHERE status = "active"'
            else:
                sql = 'SELECT COUNT(*) FROM users'
            async with db.execute(sql) as c:
                r = await c.fetchone()
                return r[0]

users_db = CollectionProxy("users")
subs_db = CollectionProxy("subs")
