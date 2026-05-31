from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL
import datetime

# MongoDB Connection Setup
client = AsyncIOMotorClient(MONGO_URL)
db = client["UserbotCommunity"]

# Collections (Tables)
users_db = db["users"]          # Yahan users ki string session save hogi
subs_db = db["subscriptions"]    # Yahan ₹10 wala payment aur expiry data hoga
state_db = db["game_state"]      # Yahan games ka current status (mismatch rokne ke liye)

# --- USER FUNCTIONS ---

async def save_user_session(user_id, string_session):
    """User ki string session save ya update karne ke liye"""
    await users_db.update_one(
        {"user_id": user_id},
        {"$set": {"session": string_session, "last_login": datetime.datetime.now()}},
        upsert=True
    )

async def get_user_session(user_id):
    """DB se user ki string nikalne ke liye"""
    user = await users_db.find_one({"user_id": user_id})
    return user["session"] if user else None

# --- SUBSCRIPTION FUNCTIONS (The ₹10 System) ---

async def is_subscribed(user_id):
    """Check karega ki user ne pay kiya hai aur plan expired toh nahi hai"""
    user_sub = await subs_db.find_one({"user_id": user_id})
    if user_sub:
        expiry = user_sub.get("expiry_date")
        if expiry and expiry > datetime.datetime.now():
            return True
    return False

async def add_subscription(user_id, days=30):
    """Admin jab approve karega toh 30 din ka time badhane ke liye"""
    new_expiry = datetime.datetime.now() + datetime.timedelta(days=days)
    await subs_db.update_one(
        {"user_id": user_id},
        {"$set": {"expiry_date": new_expiry, "status": "active"}},
        upsert=True
    )

# --- GAME STATE FUNCTIONS (Mismatch Rokne ke liye) ---

async def set_game_state(user_id, game_name, data):
    """Har user ka game data alag save karne ke liye (mismatch prevention)"""
    await state_db.update_one(
        {"user_id": user_id, "game": game_name},
        {"$set": {"data": data}},
        upsert=True
    )

async def get_game_state(user_id, game_name):
    """User ka specific game data nikalne ke liye"""
    state = await state_db.find_one({"user_id": user_id, "game": game_name})
    return state["data"] if state else {}
