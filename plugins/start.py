import os
from main import bot
from telethon import events, Button
from config import START_PIC, ADMIN_ID

# --- 1. MAIN MENU (Start Command) ---
@bot.on(events.NewMessage(pattern=r'(?i)^/start'))
async def start(event):
    # English Welcome Text
    welcome_text = (
        "👋 **Welcome to Userbot Community!**\n\n"
        "I am here to help you transform your Telegram account into a powerful "
        "userbot empire. Experience the best automation tools, high-speed games, "
        "and fun modules with ease.\n\n"
        "Navigate using the buttons below to get started. 👇"
    )
    
    # Buttons logic
    buttons = [
        [Button.inline("⚙️ Modules", data="modules_main")],
        [Button.inline("📜 Rules", data="rules"), Button.inline("👨‍💻 Developer", data="dev_info")],
        [Button.url("🔑 String Gen", "https://t.me/YourStringGenBot")] 
    ]
    
    try:
        # Sending Photo with English Caption
        await bot.send_file(
            event.chat_id,
            START_PIC,
            caption=welcome_text,
            buttons=buttons
        )
    except Exception as e:
        # Fallback to text if image fails
        await event.respond(welcome_text, buttons=buttons)
        print(f"Error loading start pic: {e}")

# --- 2. MODULES MENU (Main Sub-Menu) ---
@bot.on(events.CallbackQuery(data="modules_main"))
async def modules_main(event):
    text = (
        "📂 **Select Module Type**\n\n"
        "Choose a category to explore our premium userbot modules. "
        "Make sure you have an active subscription to use them."
    )
    buttons = [
        [Button.inline("👮 Admin Userbot", data="admin_ub"), Button.inline("🥳 Fun Userbot", data="fun_ub")],
        [Button.inline("🎮 Games Userbot", data="games_ub")],
        [Button.inline("🔙 Back to Menu", data="start_back")]
    ]
    await event.edit(text, buttons=buttons)

# --- 3. GAMES MENU (Specific Games) ---
@bot.on(events.CallbackQuery(data="games_ub"))
async def games_menu(event):
    text = (
        "🎮 **Games Userbot Modules**\n\n"
        "Select a game to activate. If you haven't logged in yet, "
        "the bot will ask for your session string."
    )
    buttons = [
        [Button.inline("WordSeek", data="mod_wordseek"), Button.inline("WordChain", data="mod_wordchain")],
        [Button.inline("Octopus", data="mod_octopus"), Button.inline("Wordly", data="mod_wordly")],
        [Button.inline("🔙 Back", data="modules_main")]
    ]
    await event.edit(text, buttons=buttons)

# --- 4. CALLBACK FOR BACK BUTTONS & INFO ---
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode("utf-8")
    
    if data == "start_back":
        # Returns to the main start menu
        await start(event) 
        await event.delete() 

    elif data == "rules":
        rules_text = (
            "🚀 **Community Rules:**\n\n"
            "1. No spamming in public groups.\n"
            "2. Subscription fee is ₹10 per month.\n"
            "3. Do not misuse the automation tools.\n"
            "4. Respect the developers and the community."
        )
        await event.answer(rules_text, alert=True)

    elif data == "dev_info":
        dev_text = (
            "👨‍💻 **Developer Information:**\n\n"
            "Developed by: @YourUsername\n"
            "Powered by: Userbot Community SaaS\n"
            "Version: 1.0 (Stable)"
        )
        await event.answer(dev_text, alert=True)
