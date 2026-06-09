import asyncio
from bot_instance import bot 
from telethon import events, Button
from config import ADMIN_ID, LOG_GROUP, SUDO_USERS
from database import add_subscription, get_sudo_info

# Tracking users: {user_id: {"plan": str, "days": int, "price": int}}
WAITING_FOR_PAYMENT = {}

# --- HELPER: CHECK PAYMENT POWER ---
async def can_user_approve(user_id):
    if user_id == ADMIN_ID: return True
    info = await get_sudo_info(user_id)
    if info and info[1] == 1: # can_pay column
        return True
    return False

# --- 1. PLAN SELECTION MENU ---
@bot.on(events.CallbackQuery(data="pay_now"))
async def pay_menu(event):
    text = (
        "💎 **Empire Userbot Premium Plans**\n\n"
        "✨ **Standard Plan (One module at a time):**\n"
        "• 15 Days Access ➔ **₹10**\n"
        "• 30 Days Access ➔ **₹30**\n\n"
        "🚀 **Empire Plan (All modules simultaneously):**\n"
        "• 15 Days Access ➔ **₹15**\n"
        "• 30 Days Access ➔ **₹35**\n\n"
        "👇 **Select your preferred plan below:**"
    )
    buttons = [
        [Button.inline("💳 Standard (15d) - ₹10", data="plan_std_15"), Button.inline("💳 Standard (30d) - ₹30", data="plan_std_30")],
        [Button.inline("👑 Empire (15d) - ₹15", data="plan_emp_15"), Button.inline("👑 Empire (30d) - ₹35", data="plan_emp_30")],
        [Button.inline("🔙 Back to Menu", data="start_back")]
    ]
    await event.edit(text, buttons=buttons)

# --- 2. SHOW PAYMENT INFO ---
@bot.on(events.CallbackQuery(pattern=r"plan_(std|emp)_(\d+)"))
async def show_payment_info(event):
    user_id = event.sender_id
    plan_code = event.pattern_match.group(1) # std or emp
    days = int(event.pattern_match.group(2)) # 15 or 30
    
    plan_name = "STANDARD" if plan_code == "std" else "EMPIRE"
    # Price logic
    if plan_code == "std":
        price = 10 if days == 15 else 30
    else:
        price = 15 if days == 15 else 35
        
    # Save user state for verification
    WAITING_FOR_PAYMENT[user_id] = {"plan": plan_name, "days": days, "price": price}
    
    # Log Intent
    if LOG_GROUP:
        try:
            user = await event.get_sender()
            await bot.send_message(LOG_GROUP, f"💸 **Intent:** `{user.first_name}` is buying **{plan_name} ({days} Days)** for ₹{price}.")
        except: pass

    pay_text = (
        f"🎯 **Plan:** {plan_name} Mode\n"
        f"⏳ **Duration:** {days} Days\n"
        f"💰 **Amount:** ₹{price}\n\n"
        "Transfer the amount to the UPI ID below:\n"
        "👉 `yourupi@upi` (Tap to copy)\n\n"
        "✅ **IMPORTANT:** Send the **Screenshot** here after payment.\n"
        "🛡️ Our team will activate your account within 1-12 hours."
    )
    await event.edit(pay_text, buttons=[Button.inline("❌ Cancel / Change Plan", data="pay_now")])

# --- 3. RECEIVE SCREENSHOT ---
@bot.on(events.NewMessage)
async def receive_screenshot(event):
    user_id = event.sender_id
    
    if user_id in WAITING_FOR_PAYMENT and event.photo:
        data = WAITING_FOR_PAYMENT[user_id]
        user = await event.get_sender()
        
        await event.reply(
            f"✅ **Screenshot Received!**\n"
            f"Plan: `{data['plan']} ({data['days']} Days)`\n"
            "Admins are verifying your receipt. Please wait."
        )
        
        admin_text = (
            "🔔 **NEW PAYMENT REQUEST**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **User:** {user.first_name} (@{user.username if user.username else 'N/A'})\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"💎 **Plan:** `{data['plan']}`\n"
            f"⏳ **Days:** `{data['days']}`\n"
            f"💰 **Amount:** `₹{data['price']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            "Verify the payment and approve below: 👇"
        )
        
        # Approve data format: appr_PLAN_DAYS_USERID
        p_code = "std" if data['plan'] == "STANDARD" else "emp"
        
        if LOG_GROUP:
            await bot.send_file(
                LOG_GROUP,
                event.photo,
                caption=admin_text,
                buttons=[
                    [Button.inline(f"✅ Approve {data['plan']} ({data['days']}d)", data=f"appr_{p_code}_{data['days']}_{user_id}")],
                    [Button.inline("❌ Reject", data=f"reject_{user_id}")]
                ]
            )
        
        del WAITING_FOR_PAYMENT[user_id]

# --- 4. SUDO APPROVAL LOGIC ---
@bot.on(events.CallbackQuery(pattern=r"appr_(std|emp)_(\d+)_(\d+)"))
async def approve_payment(event):
    if not await can_user_approve(event.sender_id):
        await event.answer("⚠️ Access Denied: You don't have 'can_pay' permission.", alert=True)
        return

    # Extract Data: appr_std_15_12345
    parts = event.data.decode("utf-8").split("_")
    plan_code = parts[1]
    days = int(parts[2])
    target_user_id = int(parts[3])
    
    plan_type = "Standard" if plan_code == "std" else "Empire"
    admin_name = event.sender.first_name
    
    # Update Database with correct Days and Plan Type
    expiry = await add_subscription(target_user_id, plan_type=plan_type, days=days)
    
    await event.edit(
        f"✅ **{plan_type} ({days}d) Activated**\n"
        f"🆔 **User ID:** `{target_user_id}`\n"
        f"👮 **Admin:** {admin_name}\n"
        f"📅 **Expiry:** `{expiry.strftime('%Y-%m-%d %H:%M')}`"
    )
    
    try:
        success_msg = (
            f"🎉 **Premium Activated!**\n\n"
            f"**Plan:** {plan_type}\n"
            f"**Duration:** {days} Days\n\n"
            f"{'⚠️ Standard: 1 module at a time.' if plan_code == 'std' else '🚀 Empire: All modules simultaneous.'}\n\n"
            "Go to Modules and start your bot! 🚀"
        )
        await bot.send_message(target_user_id, success_msg, buttons=[Button.inline("⚙️ Modules", data="modules_main")])
    except: pass

# --- 5. SUDO REJECT LOGIC ---
@bot.on(events.CallbackQuery(pattern=r"reject_"))
async def reject_payment(event):
    if not await can_user_approve(event.sender_id):
        await event.answer("⚠️ Access Denied.", alert=True)
        return
    
    target_user_id = int(event.data.decode("utf-8").replace("reject_", ""))
    admin_name = event.sender.first_name
    await event.edit(f"❌ **Payment Rejected**\n🆔 User: `{target_user_id}`\n👮 Admin: {admin_name}")
    try:
        await bot.send_message(target_user_id, "⚠️ **Rejected:** Your screenshot was invalid. Please try again.")
    except: pass
