import os
from bot_instance import bot 
from telethon import events, Button
from config import START_PIC, ADMIN_ID, LOG_GROUP
from database import claim_trial, has_claimed_trial

# Global variable to cache File ID for instant loading
START_FILE_ID = None

# --- 1. MAIN MENU LOGIC ---
async def send_start_menu(event, edit=False):
    global START_FILE_ID
    welcome_text = (
        "👋 **Welcome to Userbot Community!**\n\n"
        "Transform your Telegram account into a powerful userbot empire. "
        "Experience high-speed games, automation tools, and fun modules.\n\n"
        "Navigate using the buttons below to get started. 👇"
    )
    
    # Adding the 1-Day Trial Button here
    buttons = [
        [Button.inline("⚙️ Modules", data="modules_main")],
        [Button.inline("🎁 Claim 1-Day Trial", data="claim_trial_btn")],
        [Button.inline("📜 Rules", data="rules"), Button.inline("👨‍💻 Developer", data="dev_info")],
        [Button.inline("🔑 Generate String", data="gen_string_internal")] 
    ]

    try:
        file_to_send = START_FILE_ID if START_FILE_ID else START_PIC
        
        if edit:
            # Edit text only if it's a callback, or send new file if needed
            await event.edit(welcome_text, buttons=buttons)
        else:
            sent_msg = await bot.send_file(
                event.chat_id, 
                file_to_send, 
                caption=welcome_text, 
                buttons=buttons
            )
            # Cache the file ID for next time speed
            if not START_FILE_ID and sent_msg.photo:
                START_FILE_ID = sent_msg.photo
    except Exception as e:
        print(f"Error in Start Menu: {e}")
        if edit: await event.edit(welcome_text, buttons=buttons)
        else: await event.respond(welcome_text, buttons=buttons)

# --- 2. START HANDLER + LOGGER ---
@bot.on(events.NewMessage(pattern=r'(?i)^/start'))
async def start_handler(event):
    user = await event.get_sender()
    user_id = event.sender_id
    name = user.first_name
    username = f"@{user.username}" if user.username else "No Username"

    # LOGGING: Send details to Log Group
    if LOG_GROUP:
        log_msg = (
            "👤 **User Started Bot**\n\n"
            f"**Name:** {name}\n"
            f"**ID:** `{user_id}`\n"
            f"**Username:** {username}"
        )
        try:
            await bot.send_message(LOG_GROUP, log_msg)
        except: pass

    await send_start_menu(event)

# --- 3. TRIAL SYSTEM CALLBACK ---
@bot.on(events.CallbackQuery(data="claim_trial_btn"))
async def trial_handler(event):
    user_id = event.sender_id
    
    # Check if user already used trial
    if await has_claimed_trial(user_id):
        await event.answer("⚠️ You have already used your free trial!", alert=True)
        return

    # Claim the 24-hour trial
    success, result = await claim_trial(user_id)
    
    if success:
        expiry_str = result.strftime('%Y-%m-%d %H:%M:%S')
        await event.answer("🎉 1-Day Trial Activated Successfully!", alert=True)
        await event.edit(
            f"🎁 **Free Trial Activated!**\n\n"
            f"You have been granted **24 hours** of premium access.\n"
            f"**Expiry:** `{expiry_str}`\n\n"
            "Go to Modules and start your userbot now! 🚀",
            buttons=[[Button.inline("⚙️ Open Modules", data="modules_main")]]
        )
        # Log the trial claim
        if LOG_GROUP:
            await bot.send_message(LOG_GROUP, f"🎁 **Trial Claimed:** `{user_id}` has activated 1-day free access.")
    else:
        await event.answer(f"❌ Error: {result}", alert=True)

# --- 4. MODULES MENU ---
async def send_modules_menu(event, edit=False):
    text = (
        "📂 **Select Module Type**\n\n"
        "Choose a category to explore premium modules. "
        "Subscription/Trial is required to activate them."
    )
    buttons = [
        [Button.inline("👮 Admin Userbot", data="admin_ub"), Button.inline("🥳 Fun Userbot", data="fun_ub")],
        [Button.inline("🎮 Games Userbot", data="games_ub")],
        [Button.inline("🔙 Back to Menu", data="start_back")]
    ]
    if edit: await event.edit(text, buttons=buttons)
    else: await event.respond(text, buttons=buttons)

@bot.on(events.NewMessage(pattern=r'(?i)^/modules'))
async def modules_cmd(event):
    await send_modules_menu(event)

@bot.on(events.CallbackQuery(data="modules_main"))
async def modules_callback(event):
    await send_modules_menu(event, edit=True)

# --- 5. GAMES MENU ---
@bot.on(events.CallbackQuery(data="games_ub"))
async def games_menu(event):
    text = (
        "🎮 **Games Userbot Modules**\n\n"
        "Select a game. If you are a new user, claim your **Free Trial** first "
        "or pay ₹10 for full access."
    )
    buttons = [
        [Button.inline("WordSeek", data="mod_wordseek"), Button.inline("WordChain", data="mod_wordchain")],
        [Button.inline("Octopus", data="mod_octopus"), Button.inline("Wordly", data="mod_wordly")],
        [Button.inline("🔙 Back", data="modules_main")]
    ]
    await event.edit(text, buttons=buttons)

# --- CALLBACKS ---
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode("utf-8")
    if data == "start_back":
        await send_start_menu(event, edit=True)
    elif data == "rules":
        await event.answer("1. No spamming\n2. Maintain subscription\n3. Respect community", alert=True)
    elif data == "dev_info":
        await event.answer("Developed by: @YourUsername\nSystem: SQLite Fast Engine", alert=True)
