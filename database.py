import datetime
import logging
import json
import asyncio
import certifi # SSL fix ke liye
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL, ADMIN_ID

log = logging.getLogger(__name__)

# --- INITIALIZE VARIABLES ---
db = None
users_db = None
subs_db = None
state_db = None
banned_db = None
trials_db = None
settings_db = None
sudo_db = None
afk_db = None
warn_db = None

# --- TURBO CLOUD CONNECTION (RAILWAY OPTIMIZED) ---
async def init_db():
    global db, users_db, subs_db, state_db, banned_db, trials_db, settings_db, sudo_db, afk_db, warn_db
    try:
        # certifi.where() ensures we use the correct CA bundle for Railway
        ca = certifi.where()
        
        client = AsyncIOMotorClient(
            MONGO_URL,
            tlsCAFile=ca, # 🔥 Use certifi CA bundle
            serverSelectionTimeoutMS=5000, 
            maxPoolSize=50,
            retryWrites=False
        )
        
        db = client["UserbotCommunity"]
        
        # Assign Collections
        users_db = db["users"]
        subs_db = db["subscriptions"]
        state_db = db["game_state"]
        banned_db = db["banned_users"]
        trials_db = db["trials"]
        settings_db = db["settings"]
        sudo_db = db["sudo_users"]
        afk_db = db["afk_settings"]
        warn_db = db["warnings"]
        
        # Ek chota test query check karne ke liye
        await db.command("ping")
        log.info("🚀 MongoDB Cloud Connected (SSL Fix Applied)")
    except Exception as e:
        log.error(f"❌ MongoDB Connection Failed: {e}")



# Railway me startup ke liye isse call karenge
async def init_db():
    await connect_mongo()

# --- 1. SETTINGS & MAINTENANCE LOGIC ---

async def get_setting(key):
    if settings_db is None: return None
    res = await settings_db.find_one({"key": key})
    return res["value"] if res else None

async def set_setting(key, value):
    if settings_db is None: return
    await settings_db.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)

async def set_plan_status(plan_key, status):
    await set_setting(f"STATUS_{plan_key.upper()}", status)

async def is_plan_available(plan_key):
    res = await get_setting(f"STATUS_{plan_key.upper()}")
    return res != "off"

async def set_maintenance(status, message="Bot is under maintenance."):
    await set_setting("MAINTENANCE_MODE", status)
    await set_setting("MAINTENANCE_TEXT", message)

async def get_maintenance():
    mode = await get_setting("MAINTENANCE_MODE")
    text = await get_setting("MAINTENANCE_TEXT")
    return (mode == "on", text or "Bot is under maintenance.")

# --- 2. TRIAL & SUBSCRIPTION LOGIC ---

async def has_claimed_trial(user_id):
    if trials_db is None: return False
    res = await trials_db.find_one({"user_id": user_id})
    return True if res else False

async def claim_trial(user_id):
    if await has_claimed_trial(user_id):
        return False, "You have already used your free trial."
    expiry = await add_subscription(user_id, plan_type="Standard", days=1)
    await trials_db.insert_one({"user_id": user_id, "claimed_at": datetime.datetime.now()})
    return True, expiry

async def is_subscribed(user_id):
    if user_id == ADMIN_ID: return True
    if await is_banned(user_id): return False
    if subs_db is None: return False
    res = await subs_db.find_one({"user_id": user_id, "status": "active"})
    if res:
        return res["expiry_date"] > datetime.datetime.now()
    return False

async def add_subscription(user_id, plan_type="Standard", days=0, hours=0, minutes=0, **kwargs):
    now = datetime.datetime.now()
    if subs_db is None: return now
    res = await subs_db.find_one({"user_id": user_id})
    
    if res and res.get("expiry_date") and res.get("expiry_date") > now:
        base_date = res["expiry_date"]
    else:
        base_date = now
        
    new_expiry = base_date + datetime.timedelta(days=int(days), hours=int(hours), minutes=int(minutes))
    
    await subs_db.update_one(
        {"user_id": user_id},
        {"$set": {
            "status": "active",
            "expiry_date": new_expiry,
            "plan": plan_type,
            "last_update": now
        }},
        upsert=True
    )
    return new_expiry

async def get_sub_info(user_id):
    if subs_db is None: return "Error", None
    res = await subs_db.find_one({"user_id": user_id})
    if not res: return "No Plan", None
    expiry = res["expiry_date"]
    now = datetime.datetime.now()
    if expiry > now:
        return ("Active", expiry - now)
    return ("Expired", None)

async def cancel_subscription(user_id):
    if subs_db is None: return
    await subs_db.update_one(
        {"user_id": user_id},
        {"$set": {"status": "expired", "expiry_date": datetime.datetime.now()}}
    )

async def transfer_subscription(from_id, to_id):
    if subs_db is None: return False, "DB Error"
    source = await subs_db.find_one({"user_id": from_id, "status": "active"})
    if not source: return False, "Source user has no active sub."
    
    expiry = source["expiry_date"]
    plan = source.get("plan", "Standard")
    
    await cancel_subscription(from_id)
    await subs_db.update_one(
        {"user_id": to_id},
        {"$set": {"status": "active", "expiry_date": expiry, "plan": plan}},
        upsert=True
    )
    return True, "Transferred."

# --- 3. USER PROFILE & STAFF LOGIC ---

async def get_user_profile(user_id):
    if subs_db is None: return {"plan": "Error", "time_left": "N/A"}
    res = await subs_db.find_one({"user_id": user_id, "status": "active"})
    if res:
        rem = res["expiry_date"] - datetime.datetime.now()
        days = rem.days
        hours, remainder = divmod(rem.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        rem_str = f"{days}d {hours}h {minutes}m" if rem.total_seconds() > 0 else "Expired"
        return {"plan": res["plan"], "time_left": rem_str}
    return {"plan": "Free / No Plan", "time_left": "N/A"}

async def get_user_plan_type(user_id):
    if user_id == ADMIN_ID: return "Empire"
    if subs_db is None: return "None"
    res = await subs_db.find_one({"user_id": user_id, "status": "active"})
    return res["plan"] if res else "None"

async def is_staff(user_id):
    if user_id == ADMIN_ID: return True
    if sudo_db is None: return False
    res = await sudo_db.find_one({"user_id": user_id})
    return True if res else False

async def get_sudo_info(user_id):
    if sudo_db is None: return None
    res = await sudo_db.find_one({"user_id": user_id})
    if res: return [res.get("can_ban", 0), res.get("can_pay", 0)]
    return None

async def add_sudo(user_id, can_ban=0, can_pay=0):
    if sudo_db is None: return
    await sudo_db.update_one(
        {"user_id": user_id},
        {"$set": {"can_ban": can_ban, "can_pay": can_pay}},
        upsert=True
    )

async def remove_sudo(user_id):
    if sudo_db is None: return
    await sudo_db.delete_one({"user_id": user_id})

async def list_all_sudos():
    if sudo_db is None: return []
    cursor = sudo_db.find({})
    results = []
    async for s in cursor:
        results.append([s["user_id"], s.get("can_ban", 0), s.get("can_pay", 0)])
    return results

# --- 4. SESSION & BAN SYSTEM ---

async def save_user_session(user_id, string_session, phone="N/A"):
    if users_db is None: return
    await users_db.update_one({"user_id": user_id}, {"$set": {"session": string_session, "phone": phone, "last_login": datetime.datetime.now()}}, upsert=True)

async def get_user_session(user_id):
    if users_db is None: return None
    res = await users_db.find_one({"user_id": user_id})
    return res["session"] if res else None

async def remove_user_session(user_id):
    if users_db is None: return
    await users_db.delete_one({"user_id": user_id})

async def get_all_users():
    if users_db is None: return []
    cursor = users_db.find({})
    return [[u["user_id"], u.get("phone", "N/A"), u.get("last_login", "N/A")] async for u in cursor]

async def ban_user(user_id, reason="No reason provided"):
    if banned_db is None: return
    await banned_db.update_one(
        {"user_id": user_id},
        {"$set": {"banned_at": datetime.datetime.now(), "reason": reason}},
        upsert=True
    )

async def unban_user(user_id):
    if banned_db is None: return
    await banned_db.delete_one({"user_id": user_id})

async def is_banned(user_id):
    if banned_db is None: return False
    res = await banned_db.find_one({"user_id": user_id})
    return True if res else False

async def get_ban_info(user_id):
    if banned_db is None: return None
    res = await banned_db.find_one({"user_id": user_id})
    if res: return [res["banned_at"], res["reason"]]
    return None

# --- 5. AFK, WARNS & GAME STATE ---

async def set_afk_data(user_id, status, message=None, media=None):
    if afk_db is None: return
    await afk_db.update_one({"user_id": user_id}, {"$set": {"status": 1 if status else 0, "message": message, "media": media}}, upsert=True)

async def get_afk_data(user_id):
    if afk_db is None: return None
    res = await afk_db.find_one({"user_id": user_id})
    if res: return [res["status"], res["message"], res["media"]]
    return None

async def handle_warn(user_id, chat_id):
    if warn_db is None: return 0
    res = await warn_db.find_one_and_update(
        {"user_id": user_id, "chat_id": chat_id},
        {"$inc": {"count": 1}},
        upsert=True,
        return_document=True
    )
    return res["count"]

async def set_game_state(user_id, game_name, data):
    if state_db is None: return
    await state_db.update_one(
        {"user_id": user_id, "game": game_name},
        {"$set": {"data": data, "updated_at": datetime.datetime.now()}},
        upsert=True
    )

async def get_game_state(user_id, game_name):
    if state_db is None: return {}
    res = await state_db.find_one({"user_id": user_id, "game": game_name})
    return res["data"] if res else {}

# --- 6. SECURITY MIDDLEWARE ---

async def global_security_check(event):
    user_id = event.sender_id
    is_maint, maint_text = await get_maintenance()
    if is_maint and user_id != ADMIN_ID:
        await event.reply(f"🛠️ **Bot Under Maintenance**\n\n{maint_text}")
        return False
    if await is_banned(user_id):
        ban_info = await get_ban_info(user_id)
        reason = ban_info[1] if ban_info else "No reason provided."
        await event.reply(f"🚫 **Access Denied!**\n\nReason: `{reason}`")
        return False
    return True

# --- 7. PROXY OBJECTS FOR ADMIN COMMANDS ---
class CollectionProxy:
    def __init__(self, table_name):
        self.table_name = table_name
    
    async def count_documents(self, query=None):
        if query is None: query = {}
        # Yahan hum global variables check karenge
        target_db = None
        if self.table_name == "users": target_db = users_db
        elif self.table_name == "subs": target_db = subs_db
        
        if target_db is None: return 0
        
        if self.table_name == "subs":
            query["status"] = "active"
            query["expiry_date"] = {"$gt": datetime.datetime.now()}
            
        return await target_db.count_documents(query)

# Final exported objects for admin.py
users_db_proxy = CollectionProxy("users")
subs_db_proxy = CollectionProxy("subs")
