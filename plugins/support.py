import datetime
from bot_instance import bot
from telethon import events, Button
from config import LOG_GROUP
from database import is_banned, global_security_check # Purana security logic

# State tracker to know if user is writing a report
SUPPORT_WAITING = {}

# --- 1. SUPPORT MAIN MENU ---
@bot.on(events.CallbackQuery(data="support_main"))
async def support_menu(event):
    if not await global_security_check(event): return
    
    text = (
        "📢 **Support & Community Feedback**\n\n"
        "We value your input! Please select the type of submission you'd like to make below:"
    )
    buttons = [
        [Button.inline("🐛 Bug Report", data="sup_bug"), Button.inline("💡 Feature Request", data="sup_feat")],
        [Button.inline("📩 General Complaint", data="sup_comp")],
        [Button.inline("🔙 Back to Menu", data="start_back")]
    ]
    await event.edit(text, buttons=buttons)

# --- 2. START THE CAPTURE PROCESS ---
@bot.on(events.CallbackQuery(pattern=r"sup_"))
async def start_support_input(event):
    user_id = event.sender_id
    sup_type = event.data.decode("utf-8").replace("sup_", "")
    
    type_map = {
        "bug": "BUG REPORT 🐛",
        "feat": "FEATURE REQUEST 💡",
        "comp": "COMPLAINT 📩"
    }
    
    SUPPORT_WAITING[user_id] = type_map[sup_type]
    
    await event.edit(
        f"📝 **You are submitting a {type_map[sup_type]}**\n\n"
        "Please type your detailed message below and send it. Our admins will be notified instantly.",
        buttons=[Button.inline("❌ Cancel", data="support_main")]
    )

# --- 3. RECEIVE AND FORWARD TO LOG GC ---
@bot.on(events.NewMessage)
async def handle_support_message(event):
    user_id = event.sender_id
    
    # Check if we are waiting for a support message from this user
    if user_id in SUPPORT_WAITING and event.is_private:
        if event.text.startswith('/'): return # Commands ignore karo
        
        report_type = SUPPORT_WAITING[user_id]
        report_text = event.raw_text
        user = await event.get_sender()
        name = user.first_name if user.first_name else "User"
        username = f"@{user.username}" if user.username else "N/A"
        time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # --- FORMAT MESSAGE FOR LOG GROUP ---
        log_message = (
            f"📢 **NEW COMMUNITY SUBMISSION**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 **Type:** `{report_type}`\n"
            f"👤 **From:** {name} ({username})\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"⏰ **Time:** `{time_now}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📝 **Message:**\n{report_text}"
        )

        if LOG_GROUP:
            try:
                await bot.send_message(LOG_GROUP, log_message)
                # Confirm to user
                await event.reply(
                    "✅ **Submission Successful!**\n\n"
                    "Thank you for your feedback. Our team has been notified and will review your message shortly.",
                    buttons=[[Button.inline("🔙 Main Menu", data="start_back")]]
                )
            except Exception as e:
                await event.reply(f"❌ **Error:** Failed to send to Admin Group. `{e}`")
        
        # Clear state
        del SUPPORT_WAITING[user_id]
