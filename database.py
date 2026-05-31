import aiosqlite
import datetime
import logging
import json
import os
from config import ADMIN_ID

log = logging.getLogger(__name__)
DB_FILE = "community.db"

# --- DB INITIALIZATION ---
# Is function ko hum main.py me call karenge start hote hi
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
        
        await db.commit()
    log.info("✅ SQLite Database Initialized (Local Fast Mode)")

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
            row = await cursor.fetchone()
            return True if row else False

# --- SUBSCRIPTION FUNCTIONS ---

async def is_subscribed(user_id):
    # ADMIN/OWNER hamesha bypass
    if user_id == ADMIN_ID:
        return True
    
    # Check if banned first
    if await is_banned(user_id):
        return False
    
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
        # Puraani expiry check karo
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
            if not row:
                return False, "Source user has no active subscription."
            expiry = row[0]
            
        # Swap logic
        await db.execute('UPDATE subscriptions SET status = "expired" WHERE user_id = ?', (from_id,))
        await db.execute('''INSERT OR REPLACE INTO subscriptions (user_id, status, expiry_date) 
            VALUES (?, ?, ?)''', (to_id, "active", expiry))
        await db.commit()
        return True, "Subscription successfully transferred."

async def get_sub_info(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT expiry_date FROM subscriptions WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return "No Plan", None
            
            expiry = datetime.datetime.fromisoformat(row[0])
            now = datetime.datetime.now()
            
            if expiry > now:
                return "Active", expiry - now
            return "Expired", None

# --- GAME STATE FUNCTIONS ---

async def set_game_state(user_id, game_name, data):
    async with aiosqlite.connect(DB_FILE) as db:
        # SQLite me JSON direct nahi jata, stringify karna padta hai
        data_str = json.dumps(data)
        await db.execute('''INSERT OR REPLACE INTO game_state (user_id, game_name, data) 
            VALUES (?, ?, ?)''', (user_id, game_name, data_str))
        await db.commit()

async def get_game_state(user_id, game_name):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT data FROM game_state WHERE user_id = ? AND game_name = ?', (user_id, game_name)) as cursor:
            row = await cursor.fetchone()
            return json.loads(row[0]) if row else {}

# Dummy objects for compatibility (since admin.py used users_db.count_documents)
# Inhe hum admin.py update karke theek karenge
class CollectionProxy:
    async def count_documents(self, query):
        async with aiosqlite.connect(DB_FILE) as db:
            if "status" in str(query):
                async with db.execute('SELECT COUNT(*) FROM subscriptions WHERE status = "active"') as c:
                    r = await c.fetchone()
                    return r[0]
            async with db.execute('SELECT COUNT(*) FROM users') as c:
                r = await c.fetchone()
                return r[0]

users_db = CollectionProxy()
subs_db = CollectionProxy()
