import datetime
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL, ADMIN_ID

log = logging.getLogger(__name__)

# --- ULTRA FAST MONGODB CONNECTION ---
try:
    client = AsyncIOMotorClient(
        MONGO_URL,
        tlsAllowInvalidCertificates=True,
        tlsInsecure=True,
        serverSelectionTimeoutMS=5000, 
        connectTimeoutMS=5000,
        maxPoolSize=50
    )
    db = client["UserbotCommunity"]
    
    users_db = db["users"]
    subs_db = db["subscriptions"]
    state_db = db["game_state"]
    banned_db = db["banned_users"] # New collection for bans
    
    log.info("✅ Async MongoDB Connected (SaaS Admin Logic Active)")
except Exception as e:
    log.error(f"❌ MongoDB Connection Error: {e}")

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
    
    # Banned users can't use the bot even if they paid
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
    """Ab tu granular time add kar sakta hai (days, hours, minutes)"""
    try:
        user_sub = await subs_db.find_one({"user_id": user_id})
        now = datetime.datetime.now()
        
        # Agar sub active hai toh purani date ke aage add hoga, warna aaj se
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
    """User ki subscription turant khatam karne ke liye"""
    await subs_db.update_one({"user_id": user_id}, {"$set": {"status": "expired", "expiry_date": datetime.datetime.now()}})

async def transfer_subscription(from_id, to_id):
    """Ek account se dusre account me sub transfer karna"""
    source = await subs_db.find_one({"user_id": from_id})
    if not source or source.get("status") != "active":
        return False, "Source user has no active subscription."
    
    expiry = source.get("expiry_date")
    # Source ko band karo
    await cancel_subscription(from_id)
    # Target ko active karo
    await subs_db.update_one(
        {"user_id": to_id},
        {"$set": {"expiry_date": expiry, "status": "active"}},
        upsert=True
    )
    return True, "Successfully transferred."

async def get_sub_info(user_id):
    """Status aur bacha hua time check karne ke liye"""
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
# (Wahi purane functions bina change ke)
async def set_game_state(user_id, game_name, data):
    try:
        await state_db.update_one({"user_id": user_id, "game": game_name}, {"$set": {"data": data, "updated_at": datetime.datetime.now()}}, upsert=True)
    except: pass

async def get_game_state(user_id, game_name):
    try:
        state = await state_db.find_one({"user_id": user_id, "game": game_name})
        return state["data"] if state else {}
    except: return {}
