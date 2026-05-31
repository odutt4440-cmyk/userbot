import asyncio
from bot_instance import bot 
from telethon import events, Button
from config import ADMIN_ID
from database import add_subscription

# Tracking users who are currently in the payment process
WAITING_FOR_PAYMENT = {}

# --- 1. WHEN USER CLICKS 'PAY ₹10' ---
@bot.on(events.CallbackQuery(data="pay_now"))
async def pay_now(event):
    user_id = event.sender_id
    WAITING_FOR_PAYMENT[user_id] = True
    
    pay_text = (
        "💳 **Premium Subscription (₹10/Month)**\n\n"
        "To keep your userbot running 24/7 on our high-speed servers, "
        "please complete the payment below:\n\n"
        "🎯 **UPI ID:** `yourupi@upi` (Tap to copy)\n"
        "💰 **Amount:** ₹10\n\n"
        "✅ **After Payment:** Send the **Screenshot** of the transaction here in this chat.\n\n"
        "🛡️ Our admin will verify and activate your account shortly."
    )
    
    await event.edit(pay_text, buttons=[Button.inline("❌ Cancel", data="start_back")])

# --- 2. WHEN USER SENDS SCREENSHOT ---
@bot.on(events.NewMessage)
async def receive_screenshot(event):
    user_id = event.sender_id
    
    # Check if we are expecting a payment screenshot from this user
    if user_id in WAITING_FOR_PAYMENT and event.photo:
        # Confirm to the user
        await event.reply(
            "✅ **Screenshot Received!**\n"
            "Your payment has been sent to our admins for verification. "
            "You will be notified once it's approved (usually within 1-12 hours)."
        )
        
        # Prepare text for Admin
        admin_text = (
            "🔔 **NEW PAYMENT REQUEST**\n\n"
            f"👤 **User:** {event.sender.first_name}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"🔗 **Username:** @{event.sender.username if event.sender.username else 'N/A'}\n\n"
            "Please verify the screenshot and take action below: 👇"
        )
        
        # Forward the photo to Admin with Action Buttons
        await bot.send_file(
            ADMIN_ID,
            event.photo,
            caption=admin_text,
            buttons=[
                [Button.inline("✅ Approve", data=f"approve_{user_id}")],
                [Button.inline("❌ Reject", data=f"reject_{user_id}")]
            ]
        )
        
        # Clean up the waiting list
        del WAITING_FOR_PAYMENT[user_id]

# --- 3. ADMIN APPROVAL LOGIC ---
@bot.on(events.CallbackQuery(pattern=r"approve_"))
async def approve_payment(event):
    # Only Admin can approve
    if event.sender_id != ADMIN_ID:
        await event.answer("⚠️ Access Denied: You are not an admin.", alert=True)
        return

    # Extract User ID from the callback data
    target_user_id = int(event.data.decode("utf-8").replace("approve_", ""))
    
    # Update Database: Add 30 days subscription
    await add_subscription(target_user_id, days=30)
    
    # Update Admin UI (Remove buttons to prevent double approval)
    await event.edit(f"✅ **Approved!**\nUser ID `{target_user_id}` has been granted 30 days of access.")
    
    # Notify the User
    try:
        success_msg = (
            "🎉 **Payment Approved!**\n\n"
            "Your premium subscription is now **Active** for 30 days. "
            "You can now go to the Modules section and activate your userbot!"
        )
        await bot.send_message(target_user_id, success_msg, buttons=[Button.inline("⚙️ Go to Modules", data="modules_main")])
    except Exception as e:
        print(f"Notification Error: {e}")

# --- 4. ADMIN REJECT LOGIC ---
@bot.on(events.CallbackQuery(pattern=r"reject_"))
async def reject_payment(event):
    if event.sender_id != ADMIN_ID:
        await event.answer("⚠️ Access Denied.", alert=True)
        return
    
    target_user_id = int(event.data.decode("utf-8").replace("reject_", ""))
    
    # Update Admin UI
    await event.edit(f"❌ **Rejected!**\nPayment for User `{target_user_id}` was declined.")
    
    # Notify the User
    try:
        reject_msg = (
            "⚠️ **Payment Rejected**\n\n"
            "Your recent payment screenshot was rejected by the admin. "
            "Please make sure you send a valid transaction receipt. "
            "If this is a mistake, contact the developer."
        )
        await bot.send_message(target_user_id, reject_msg)
    except Exception as e:
        print(f"Notification Error: {e}")
