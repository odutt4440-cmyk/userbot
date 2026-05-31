from main import bot
from telethon import events, Button
from config import START_PIC, ADMIN_ID

# --- 1. MAIN MENU (Start Command) ---
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    # Welcome Text
    welcome_text = (
        "👋 **Welcome to Userbot Community!**\n\n"
        "Main aapka help karunga apne account ko ek powerful "
        "userbot mein convert karne mein.\n\n"
        "Niche diye gaye buttons se navigate karein. 👇"
    )
    
    # Buttons logic
    buttons = [
        [Button.inline("⚙️ Modules", data="modules_main")],
        [Button.inline("📜 Rules", data="rules"), Button.inline("👨‍💻 Developer", data="dev_info")],
        [Button.url("🔑 String Gen", "https://t.me/YourStringGenBot")] # Apna string gen bot link dalo
    ]
    
    # Send Photo with Caption and Buttons
    await bot.send_file(
        event.chat_id,
        START_PIC,
        caption=welcome_text,
        buttons=buttons
    )

# --- 2. MODULES MENU (Main Sub-Menu) ---
@bot.on(events.CallbackQuery(data="modules_main"))
async def modules_main(event):
    text = "📂 **Select Module Type:**\nChoose a category to explore available userbots."
    buttons = [
        [Button.inline("👮 Admin Userbot", data="admin_ub"), Button.inline("🥳 Fun Userbot", data="fun_ub")],
        [Button.inline("🎮 Games Userbot", data="games_ub")],
        [Button.inline("🔙 Back to Menu", data="start_back")]
    ]
    await event.edit(text, buttons=buttons)

# --- 3. GAMES MENU (Specific Games) ---
@bot.on(events.CallbackQuery(data="games_ub"))
async def games_menu(event):
    text = "🎮 **Games Userbot Modules:**\nClick on a game to login and activate it."
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
        # Start menu par wapas jane ke liye logic
        await start(event) # Yeh naya message bhejega, edit ke liye alag logic lagta hai
        await event.delete() # Purana wala delete kar dega clean look ke liye

    elif data == "rules":
        await event.answer("1. No spamming.\n2. ₹10 monthly fee.\n3. Respect developers.", alert=True)

    elif data == "dev_info":
        await event.answer("Developer: @YourUsername\nPowered by: Userbot Community", alert=True)
