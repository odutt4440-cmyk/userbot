from main import bot
from telethon import events, Button
from config import ADMIN_ID, START_PIC
from database import add_subscription

# Tracking users who are about to send a screenshot
WAITING_FOR_PAYMENT = {}

# --- 1. JAB USER 'PAY NOW' PAR CLICK KARE ---
@bot.on(events.CallbackQuery(data="pay_now"))
async def pay_now(event):
    user_id = event.sender_id
    WAITING_FOR_PAYMENT[user_id] = True
    
    pay_text = (
        "💳 **Payment Method (₹10/Month)**\n\n"
        "pay ₹10 given below :\n"
        "👉 `yourupi@upi` \n\n"
        "✅ send **Screenshot** after payment in this chat.\n"
        "admin will approve soon."
    )
    
    # Tum yahan apna QR code image bhi bhej sakte ho START_PIC ki jagah
    await event.edit(pay_text, buttons=[Button.inline("❌ Cancel", data="start_back")])

# --- 2. JAB USER SCREENSHOT BHEJE ---
@bot.on(events.NewMessage)
async def receive_screenshot(event):
    user_id = event.sender_id
    
    # Check karein kya user payment process mein hai aur usne photo bheji hai
    if user_id in WAITING_FOR_PAYMENT and event.photo:
        # User ko reply karein
        await event.reply("✅ **Screenshot Received!**\nVerification has been send to admins")
        
        # Admin ko forward karein details ke saath
        admin_text = (
            "🔔 **New Payment Request!**\n\n"
            f"👤 User: {event.sender.first_name}\n"
            f"🆔 ID: `{user_id}`\n\n"
            "Kya aap is payment ko approve karna chahte hain?"
        )
        
        # Admin ko photo bhejna Approval button ke saath
        await bot.send_file(
            ADMIN_ID,
            event.photo,
            caption=admin_text,
            buttons=[
                [Button.inline("✅ Approve", data=f"approve_{user_id}")],
                [Button.inline("❌ Reject", data=f"reject_{user_id}")]
            ]
        )
        
        # Waiting list se hata dein
        del WAITING_FOR_PAYMENT[user_id]

# --- 3. ADMIN APPROVAL LOGIC ---
@bot.on(events.CallbackQuery(pattern=r"approve_"))
async def approve_payment(event):
    # Check karein ki click karne wala Admin hi hai
    if event.sender_id != ADMIN_ID:
        await event.answer("⚠️ you are not an admin", alert=True)
        return

    # User ID nikalna data se
