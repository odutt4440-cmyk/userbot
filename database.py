import datetime
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL, ADMIN_ID

log = logging.getLogger(__name__)

# --- ULTRA FAST MONGODB CONNECTION ---
try:
    # Fix: Removed tlsAllowInvalidCertificates because tlsInsecure covers it
    client = AsyncIOMotorClient(
        MONGO_URL,
        tlsInsecure=True, 
        serverSelectionTimeoutMS=5000, 
        connectTimeoutMS=5000,
        maxPoolSize=50,
        retryWrites=False
    )
    db = client["UserbotCommunity"]
    
    users_db = db["users"]
    subs_db = db["subscriptions"]
    state_db = db["game_state"]
    banned_db = db["banned_users"]
    
    log.info("✅ Async MongoDB Connected Successfully!")
except Exception as e:
    log.error(f"❌ MongoDB Connection Error: {e}")

# --- USER SESSION FUNCTIONS (RE-ADDED) ---

async def save_user_session(user_id, string_session):
    """User ki string session save ya update karne ke liye"""
    try:
        await users_db.update_one(
            {"user_id": user_id},
            {"$set": {
                "session": string_session, 
                "last_login": datetime.datetime.now()
            }},
            upsert=True
        )
    except Exception as e:
        log.error(f"DB Error (save_session): {e}")

async def get_user_session(user_id):
    """DB se user ki string nikalne ke liye"""
    try:
        user = await users_db.find_one({"user_id": user_id})
        return user.get("session") if user else None
    except Exception as e:
        log.error(f"DB Error (get_session): {e}")
        return None

# --- BAN SYSTEM ---

async def ban_user(user_id):
    """User ko bot se block karne ke liye"""
    await banned_db.update_one({"user_id": user_id}, {"$set": {"banned_at": datetime.datetime.now()}}, upsert=True)

async def unban_user(user_id):
    """User ko unblock karne ke liye"""
    await banned_db.delete_one({"user_id": user_id})

async def is_banned(user_id):
    """Check karega user block hai ya nahi"""
    user = await banned_db.find_one({"user_id": user_id})
    return True if user else False

# --- SUBSCRIPTION FUNCTIONS ---

async def is_subscribed(user_id):
    # ADMIN/OWNER hamesha bypass
    if user_id == ADMIN_ID:
        return True
    
    # Banned users can't use the bot
    if await is_banned(user_id):
        return False

    try:
        user_sub = await subs_db.find_one({"user_id": user_id})
        if user_sub and user_sub.get("status") == "active":
            expiry = user_sub.get("expiry_date")
            if expiry and expiry > datetime.datetime.now():
                return True
    except Exception as e:
        log.error(f"DB Error (is_subscribed): {e}")
    return False

async def add_subscription(user_id, days=0, hours=0, minutes=0):
    try:
        user_sub = await subs_db.find_one({"user_id": user_id})
        now = datetime.datetime.now()
        
        if user_sub and user_sub.get("expiry_date") and user_sub.get("expiry_date") > now:
            base_date = user_sub.get("expiry_date")
        else:
            base_date = now
            
        new_expiry = base_date + datetime.timedelta(days=days, hours=hours, minutes=minutes)
        
        await subs_db.update_one(
            {"user_id": user_id},
            {"$set": {"expiry_date": new_expiry, "status": "active"}},
            upsert=True
        )
        return new_expiry
    except Exception as e:
        log.error(f"DB Error (add_sub): {e}")
        return None

async def cancel_subscription(user_id):
    await subs_db.update_one({"user_id": user_id}, {"$set": {"status": "expired", "expiry_date": datetime.datetime.now()}})

async def transfer_subscription(from_id, to_id):
    source = await subs_db.find_one({"user_id": from_id})
    if not source or source.get("status") != "active":
        return False, "Source user has no active subscription."
    
    expiry = source.get("expiry_date")
    await cancel_subscription(from_id)
    await subs_db.update_one(
        {"user_id": to_id},
        {"$set": {"expiry_date": expiry, "status": "active"}},
        upsert=True
    )
    return True, "Successfully transferred."

async def get_sub_info(user_id):
    user_sub = await subs_db.find_one({"user_id": user_id})
    if not user_sub:
        return "No Plan", None
    
    expiry = user_sub.get("expiry_date")
    now = datetime.datetime.now()
    
    if expiry > now:
        time_left = expiry - now
        return "Active", time_left
    return "Expired", None

# --- GAME STATE FUNCTIONS ---

async def set_game_state(user_id, game_name, data):
    try:
        await state_db.update_one({"user_id": user_id, "game": game_name}, {"$set": {"data": data, "updated_at": datetime.datetime.now()}}, upsert=True)
    except: pass

async def get_game_state(user_id, game_name):
    try:
        state = await state_db.find_one({"user_id": user_id, "game": game_name})
        return state["data"] if state else {}
    except: return {}
