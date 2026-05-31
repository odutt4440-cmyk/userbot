from bot_instance import bot 
from telethon import events
from config import ADMIN_ID
from database import add_subscription, users_db, subs_db

# Command to Approve someone manually: /approve <user_id> <days>
@bot.on(events.NewMessage(pattern=r'/approve (\d+) (\d+)'))
async def manual_approve(event):
    if event.sender_id != ADMIN_ID:
        return # Sirf tu hi ye command chala sakta hai
    
    user_id = int(event.pattern_match.group(1))
    days = int(event.pattern_match.group(2))
    
    # Database update
    await add_subscription(user_id, days)
    
    await event.reply(f"✅ **Manual Approval Done!**\nUser: `{user_id}`\nPlan: `{days} Days` added.")
    
    # User ko notification bhejna
    try:
        await bot.send_message(user_id, f"🎉 **Special Access Granted!**\nAdmin has manually activated your subscription for {days} days.")
    except:
        pass

# Command to check stats: /stats
@bot.on(events.NewMessage(pattern='/stats'))
async def bot_stats(event):
    if event.sender_id != ADMIN_ID: return
    
    total_users = await users_db.count_documents({})
    active_subs = await subs_db.count_documents({"status": "active"})
    
    text = (
        "📊 **Empire Bot Stats**\n\n"
        f"👤 Total Users: `{total_users}`\n"
        f"💎 Active Subscriptions: `{active_subs}`"
    )
    await event.reply(text)

# Command to Check User Info: /info <user_id>
@bot.on(events.NewMessage(pattern=r'/info (\d+)'))
async def user_info(event):
    if event.sender_id != ADMIN_ID: return
    
    user_id = int(event.pattern_match.group(1))
    user_data = await users_db.find_one({"user_id": user_id})
    sub_data = await subs_db.find_one({"user_id": user_id})
    
    if not user_data:
        await event.reply("❌ User not found in database.")
        return
    
    status = sub_data.get("status", "N/A") if sub_data else "No Plan"
    expiry = sub_data.get("expiry_date", "N/A") if sub_data else "N/A"
    
    info_text = (
        "👤 **User Information**\n\n"
        f"ID: `{user_id}`\n"
        f"Session Saved: `{'Yes' if user_data.get('session') else 'No'}`\n"
        f"Plan Status: `{status}`\n"
        f"Expiry: `{expiry}`"
    )
    await event.reply(info_text)
