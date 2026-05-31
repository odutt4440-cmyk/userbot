import datetime
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL

log = logging.getLogger(__name__)

# MongoDB Connection Setup
try:
    # Adding SSL fix to prevent handshake timeout and bot freezing
    client = AsyncIOMotorClient(
        MONGO_URL,
        tlsAllowInvalidCertificates=True # <--- SSL Handshake Fix
    )
    db = client["UserbotCommunity"]
    
    # Collections
    users_db = db["users"]
    subs_db = db["subscriptions"]
    state_db = db["game_state"]
    
    log.info("✅ MongoDB Connection Established with SSL Fix.")
except Exception as e:
    log.error(f"❌ MongoDB Connection Error: {e}")

# --- USER FUNCTIONS ---

async def save_user_session(user_id, string_session):
    """User ki string session save ya update karne ke liye"""
    await users_db.update_one(
        {"user_id": user_id},
        {"$set": {
            "session": string_session, 
            "last_login": datetime.datetime.now()
        }},
        upsert=True
    )

async def get_user_session(user_id):
    """DB se user ki string nikalne ke liye"""
    try:
        user = await users_db.find_one({"user_id": user_id})
        if user and "session" in user:
            return user["session"]
    except Exception as e:
        log.error(f"Error fetching session: {e}")
    return None

# --- SUBSCRIPTION FUNCTIONS ---

async def is_subscribed(user_id):
    """Check karega ki user active hai ya expired"""
    try:
        user_sub = await subs_db.find_one({"user_id": user_id})
        if user_sub and user_sub.get("status") == "active":
            expiry = user_sub.get("expiry_date")
            if expiry and expiry > datetime.datetime.now():
                return True
    except Exception as e:
        log.error(f"Error checking subscription: {e}")
    return False

async def add_subscription(user_id, days=30):
    """Subscription activate ya renew karne ke liye"""
    user_sub = await subs_db.find_one({"user_id": user_id})
    now = datetime.datetime.now()
    
    if user_sub and user_sub.get("expiry_date") and user_sub.get("expiry_date") > now:
        base_date = user_sub.get("expiry_date")
    else:
        base_date = now
        
    new_expiry = base_date + datetime.timedelta(days=days)
    
    await subs_db.update_one(
        {"user_id": user_id},
        {"$set": {
            "expiry_date": new_expiry, 
            "status": "active",
            "last_payment": now
        }},
        upsert=True
    )

# --- GAME STATE FUNCTIONS ---

async def set_game_state(user_id, game_name, data):
    """Mismatch rokne ke liye har user ka alag data save karna"""
    await state_db.update_one(
        {"user_id": user_id, "game": game_name},
        {"$set": {"data": data, "updated_at": datetime.datetime.now()}},
        upsert=True
    )

async def get_game_state(user_id, game_name):
    try:
        state = await state_db.find_one({"user_id": user_id, "game": game_name})
        return state["data"] if state else {}
    except Exception as e:
        log.error(f"Error getting game state: {e}")
        return {}
