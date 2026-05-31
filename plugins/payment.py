import asyncio
from bot_instance import bot 
from telethon import events, Button
from config import ADMIN_ID, LOG_GROUP, SUDO_USERS
from database import add_subscription

# Tracking users currently in the payment process
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
        "🛡️ Our support team will verify and activate your account shortly."
    )
    
    await event.edit(pay_text, buttons=[Button.inline("❌ Cancel", data="start_back")])

# --- 2. WHEN USER SENDS SCREENSHOT ---
@bot.on(events.NewMessage)
async def receive_screenshot(event):
    user_id = event.sender_id
    
    if user_id in WAITING_FOR_PAYMENT and event.photo:
        # Confirm to the user immediately
        await event.reply(
            "✅ **Screenshot Received!**\n"
            "Your payment has been sent to our verification group. "
            "You will receive a notification here once it is approved."
        )
        
        # Prepare log message for Log GC
        admin_text = (
            "🔔 **NEW PAYMENT REQUEST**\n\n"
            f"👤 **User:** {event.sender.first_name}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"🔗 **Username:** @{event.sender.username if event.sender.username else 'N/A'}\n\n"
            "**Action Required:** Verify the receipt and approve below. 👇"
        )
        
        # Send to LOG_GROUP instead of Admin DM
        try:
            await bot.send_file(
                LOG_GROUP,
                event.photo,
                caption=admin_text,
                buttons=[
                    [Button.inline("✅ Approve", data=f"approve_{user_id}")],
                    [Button.inline("❌ Reject", data=f"reject_{user_id}")]
                ]
            )
        except Exception as e:
            print(f"Log Group Error: {e}")
            # Fallback to Admin ID if Log Group fails
            await bot.send_file(ADMIN_ID, event.photo, caption=admin_text + "\n\n*(Log Group Failed)*")
        
        del WAITING_FOR_PAYMENT[user_id]

# --- 3. SUDO APPROVAL LOGIC (Log GC) ---
@bot.on(events.CallbackQuery(pattern=r"approve_"))
async def approve_payment(event):
    # Permission Check: Is the person clicking a Sudo user?
    if event.sender_id not in SUDO_USERS:
        await event.answer("⚠️ You are not authorized to approve payments.", alert=True)
        return

    target_user_id = int(event.data.decode("utf-8").replace("approve_", ""))
    admin_name = event.sender.first_name
    
    # Update Database (Default 30 days)
    await add_subscription(target_user_id, days=30)
    
    # Update Log GC Message
    await event.edit(
        f"✅ **Payment Approved**\n\n"
        f"🆔 **User ID:** `{target_user_id}`\n"
        f"👮 **Approved By:** {admin_name}\n"
        f"📅 **Status:** 30 Days Access Granted"
    )
    
    # Notify User
    try:
        success_msg = (
            "🎉 **Access Granted!**\n\n"
            "Your premium subscription has been approved by our team. "
            "You can now activate any module from the menu."
        )
        await bot.send_message(target_user_id, success_msg, buttons=[Button.inline("⚙️ Open Modules", data="modules_main")])
    except:
        pass

# --- 4. SUDO REJECT LOGIC (Log GC) ---
@bot.on(events.CallbackQuery(pattern=r"reject_"))
async def reject_payment(event):
    if event.sender_id not in SUDO_USERS:
        await event.answer("⚠️ Unauthorized.", alert=True)
        return
    
    target_user_id = int(event.data.decode("utf-8").replace("reject_", ""))
    admin_name = event.sender.first_name

    # Update Log GC Message
    await event.edit(
        f"❌ **Payment Rejected**\n\n"
        f"🆔 **User ID:** `{target_user_id}`\n"
        f"👮 **Rejected By:** {admin_name}"
    )
    
    # Notify User
    try:
        reject_msg = (
            "⚠️ **Payment Verification Failed**\n\n"
            "Your screenshot was rejected by our team. "
            "Please ensure you send a clear and valid transaction receipt. "
            "Contact support if you think this is a mistake."
        )
        await bot.send_message(target_user_id, reject_msg)
    except:
        pass
