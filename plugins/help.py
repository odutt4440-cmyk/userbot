from bot_instance import bot
from telethon import events, Button

@bot.on(events.NewMessage(pattern=r'(?i)^/help'))
async def help_handler(event):
    help_text = (
        "📖 **Userbot Community Help Guide**\n\n"
        "**Basic Commands:**\n"
        "• `/start` - Open main menu\n"
        "• `/help` - Show this guide\n"
        "• `/modules` - List available userbots\n\n"
        "**How to use?**\n"
        "1. Generate your String Session using our tool.\n"
        "2. Choose a Module (e.g. Wordly) and paste your string.\n"
        "3. Complete the ₹10 subscription payment.\n"
        "4. Click 'Activate' and enjoy 24/7 automation.\n\n"
        "**Subscription:**\n"
        "Fee: ₹10 per 30 days.\n"
        "Includes: All game modules + high speed servers."
    )
    
    await event.reply(
        help_text, 
        buttons=[[Button.inline("📜 View Rules", data="rules"), Button.inline("⚙️ Modules", data="modules_main")]]
    )

@bot.on(events.NewMessage(pattern=r'(?i)^/modules'))
async def modules_cmd_handler(event):
    # Seedha modules menu par bhej dega
    from plugins.start import modules_main
    await modules_main(event)
