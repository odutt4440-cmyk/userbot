from bot_instance import bot
from telethon import events, Button
from database import is_banned

# --- 1. HELP HANDLER ---
@bot.on(events.NewMessage(pattern=r'(?i)^/help'))
async def help_handler(event):
    # 🛡️ Security Check
    if not event.is_private:
        return await event.reply("❌ **Access Denied!**\n\nPlease use this command in **Private DM** for security.")
    
    if await is_banned(event.sender_id):
        return await event.reply("🚫 **Access Denied:** You are banned.")

    help_text = (
        "📖 **Empire Community Help Guide**\n\n"
        "**Available Commands:**\n"
        "• `/start` - Open Main Menu\n"
        "• `/modules` - Explore All Userbot Modules\n"
        "• `/help` - Show this Guide\n\n"
        "**Quick Setup:**\n"
        "1. Generate your **String Session** via the tool.\n"
        "2. Go to **Modules**, select a bot, and link your string.\n"
        "3. Claim your **Trial** or Pay ₹10 for premium access.\n"
        "4. Deploy and enjoy 24/7 automation!"
    )
    
    # Modules button yahan Callback trigger karega (No import needed)
    await event.reply(
        help_text, 
        buttons=[
            [Button.inline("⚙️ Open Modules", data="modules_main")],
            [Button.inline("📜 Rules", data="rules")]
        ]
    )

# Note: /modules command ko hum plugins/start.py me handle karenge taaki crash na ho.
