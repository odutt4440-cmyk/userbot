import datetime
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL

log = logging.getLogger(__name__)

# --- ULTRA FAST MONGODB CONNECTION ---
try:
    # 1. tlsAllowInvalidCertificates: SSL errors fix karne ke liye
    # 2. serverSelectionTimeoutMS: Agar DB down ho toh bot ko hang hone se rokne ke liye (5s)
    client = AsyncIOMotorClient(
        MONGO_URL,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=5000, 
        connectTimeoutMS=5000,
        maxPoolSize=50
    )
    db = client["UserbotCommunity"]
    
    users_db = db["users"]
    subs_db = db["subscriptions"]
    state_db = db["game_state"]
    
    log.info("✅ Async MongoDB Connected (Fast Mode)")
except Exception as e:
    log.error(f"❌ MongoDB Connection Error: {e}")

# --- USER FUNCTIONS ---

async def save_user_session(user_id, string_session):
    try:
        await users_db.update_one(
            {"user_id": user_id},
            {"$set": {"session": string_session, "last_login": datetime.datetime.now()}},
            upsert=True
        )
    except Exception as e:
        log.error(f"DB Error: {e}")

async def get_user_session(user_id):
    try:
        user = await users_db.find_one({"user_id": user_id})
        return user.get("session") if user else None
    except Exception as e:
        log.error(f"DB Error: {e}")
        return None

# --- SUBSCRIPTION FUNCTIONS ---

async def is_subscribed(user_id):
    try:
        # Check cache if possible, but for now direct async check
        user_sub = await subs_db.find_one({"user_id": user_id})
        if user_sub and user_sub.get("status") == "active":
            expiry = user_sub.get("expiry_date")
            if expiry and expiry > datetime.datetime.now():
                return True
    except Exception as e:
        log.error(f"DB Error (is_subscribed): {e}")
    return False

async def add_subscription(user_id, days=30):
    try:
        user_sub = await subs_db.find_one({"user_id": user_id})
        now = datetime.datetime.now()
        
        base_date = user_sub.get("expiry_date") if (user_sub and user_sub.get("expiry_date") and user_sub.get("expiry_date") > now) else now
        new_expiry = base_date + datetime.timedelta(days=days)
        
        await subs_db.update_one(
            {"user_id": user_id},
            {"$set": {"expiry_date": new_expiry, "status": "active"}},
            upsert=True
        )
    except Exception as e:
        log.error(f"DB Error: {e}")

# --- GAME STATE FUNCTIONS ---

async def set_game_state(user_id, game_name, data):
    try:
        await state_db.update_one(
            {"user_id": user_id, "game": game_name},
            {"$set": {"data": data, "updated_at": datetime.datetime.now()}},
            upsert=True
        )
    except Exception as e:
        log.error(f"DB Error: {e}")

async def get_game_state(user_id, game_name):
    try:
        state = await state_db.find_one({"user_id": user_id, "game": game_name})
        return state["data"] if state else {}
    except Exception as e:
        log.error(f"DB Error: {e}")
        return {}
