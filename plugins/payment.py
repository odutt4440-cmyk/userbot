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
    user = await event.get_sender()
    WAITING_FOR_PAYMENT[user_id] = True
    
    # Intent Log: Let admins know someone is looking at the payment page
    if LOG_GROUP:
        try:
            name = user.first_name
            username = f"@{user.username}" if user.username else "N/A"
            await bot.send_message(
                LOG_GROUP, 
                f"💳 **Payment Intent:** User `{name}` ({user_id}) is viewing the payment instructions."
            )
        except: pass

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
        user = await event.get_sender()
        # Confirm to the user immediately
        await event.reply(
            "✅ **Screenshot Received!**\n"
            "Your payment has been sent to our verification group. "
            "You will receive a notification here once it is approved."
        )
        
        # Prepare log message for Log GC
        admin_text = (
            "🔔 **NEW PAYMENT VERIFICATION**\n\n"
            f"👤 **User:** {user.first_name}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"🔗 **Username:** @{user.username if user.username else 'N/A'}\n\n"
            "**Action Required:** Check the screenshot and approve if valid. 👇"
        )
        
        # Send to LOG_GROUP for Sudo users to see
        if LOG_GROUP:
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
                # Fallback to Admin DM if Log Group fails
                await bot.send_file(ADMIN_ID, event.photo, caption=admin_text + f"\n\n*(Error: {e})*")
        
        del WAITING_FOR_PAYMENT[user_id]

# --- 3. SUDO APPROVAL LOGIC (From Log GC) ---
@bot.on(events.CallbackQuery(pattern=r"approve_"))
async def approve_payment(event):
    # Only Sudo users can approve
    if event.sender_id not in SUDO_USERS:
        await event.answer("⚠️ Access Denied: You are not a Sudo user.", alert=True)
        return

    target_user_id = int(event.data.decode("utf-8").replace("approve_", ""))
    admin_name = event.sender.first_name
    
    # Update Database using SQLite (30 Days Default)
    expiry = await add_subscription(target_user_id, days=30)
    
    # Update the Log message to show completion
    await event.edit(
        f"✅ **Payment Approved**\n\n"
        f"🆔 **User ID:** `{target_user_id}`\n"
        f"👮 **Admin:** {admin_name}\n"
        f"📅 **Expiry:** `{expiry.strftime('%Y-%m-%d %H:%M:%S')}`\n"
        f"✨ Access granted for 30 days."
    )
    
    # Notify User
    try:
        success_msg = (
            "🎉 **Subscription Activated!**\n\n"
            "Your premium payment has been approved. You now have **30 days** of full access.\n"
            "Go to the Modules section and fire up your userbot! 🚀"
        )
        await bot.send_message(target_user_id, success_msg, buttons=[Button.inline("⚙️ Open Modules", data="modules_main")])
    except:
        pass

# --- 4. SUDO REJECT LOGIC ---
@bot.on(events.CallbackQuery(pattern=r"reject_"))
async def reject_payment(event):
    if event.sender_id not in SUDO_USERS:
        await event.answer("⚠️ Unauthorized.", alert=True)
        return
    
    target_user_id = int(event.data.decode("utf-8").replace("reject_", ""))
    admin_name = event.sender.first_name

    # Update Log Message
    await event.edit(
        f"❌ **Payment Rejected**\n\n"
        f"🆔 **User ID:** `{target_user_id}`\n"
        f"👮 **Admin:** {admin_name}\n"
        f"Status: Transaction declined."
    )
    
    # Notify User
    try:
        reject_msg = (
            "⚠️ **Payment Rejected**\n\n"
            "Your payment screenshot was rejected by our admins. "
            "Please ensure you send a valid transaction receipt.\n\n"
            "If you think this is a mistake, contact our support."
        )
        await bot.send_message(target_user_id, reject_msg)
    except:
        pass
