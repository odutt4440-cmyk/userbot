import os
from bot_instance import bot 
from telethon import events, Button
from config import START_PIC, ADMIN_ID, LOG_GROUP
from database import claim_trial, has_claimed_trial, get_setting, set_setting

# --- 1. MAIN MENU LOGIC (Instant Speed) ---
async def send_start_menu(event, edit=False):
    welcome_text = (
        "👋 **Welcome to Userbot Community!**\n\n"
        "Transform your Telegram account into a powerful userbot empire. "
        "Experience high-speed games, automation tools, and fun modules.\n\n"
        "Navigate using the buttons below to get started. 👇"
    )
    
    buttons = [
        [Button.inline("⚙️ Modules", data="modules_main")],
        [Button.inline("🎁 Claim 1-Day Trial", data="claim_trial_btn")],
        [Button.inline("📜 Rules", data="rules"), Button.inline("👨‍💻 Developer", data="dev_info")],
        [Button.inline("🔑 Generate String", data="gen_string_internal")] 
    ]

    try:
        # Check database if we already have the File ID for the start picture
        cached_file_id = await get_setting("START_PIC_ID")
        file_to_send = cached_file_id if cached_file_id else START_PIC
        
        if edit:
            # If it was a button click, we can't 'edit' a photo into text easily, 
            # so we just update the text or send a new menu.
            await event.edit(welcome_text, buttons=buttons)
        else:
            sent_msg = await bot.send_file(
                event.chat_id, 
                file_to_send, 
                caption=welcome_text, 
                buttons=buttons
            )
            # If we didn't have a cached ID, save it now for next time
            if not cached_file_id and sent_msg.photo:
                await set_setting("START_PIC_ID", str(sent_msg.photo.id))
                
    except Exception as e:
        print(f"Error in Start Menu: {e}")
        # Fallback to plain text if photo fails
        if edit: await event.edit(welcome_text, buttons=buttons)
        else: await event.respond(welcome_text, buttons=buttons)

# --- 2. START HANDLER + LOGGER ---
@bot.on(events.NewMessage(pattern=r'(?i)^/start'))
async def start_handler(event):
    user = await event.get_sender()
    user_id = event.sender_id
    name = user.first_name if user.first_name else "User"
    username = f"@{user.username}" if user.username else "No Username"

    # LOGGING: Notify Admin Group
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
        await event.answer("⚠️ You have already claimed your free trial!", alert=True)
        return

    # Claim the 24-hour trial via database
    success, result = await claim_trial(user_id)
    
    if success:
        # result is the expiry datetime object
        expiry_str = result.strftime('%Y-%m-%d %H:%M:%S')
        await event.answer("🎉 1-Day Trial Activated!", alert=True)
        await event.edit(
            f"🎁 **Free Trial Activated!**\n\n"
            f"You now have **24 hours** of premium access to all modules.\n"
            f"**Expires on:** `{expiry_str}`\n\n"
            "Open Modules and start your userbot now! 🚀",
            buttons=[[Button.inline("⚙️ Open Modules", data="modules_main")]]
        )
        # Log trial usage
        if LOG_GROUP:
            await bot.send_message(LOG_GROUP, f"🎁 **Trial Claimed:** `{user_id}` has activated 24h access.")
    else:
        await event.answer(f"❌ Error: {result}", alert=True)

# --- 4. MODULES MENU (Command + Button) ---
async def send_modules_menu(event, edit=False):
    text = (
        "📂 **Select Module Type**\n\n"
        "Explore our high-speed premium modules. "
        "Ensure you have an active subscription or trial."
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
        "High-performance solvers for your favorite games. "
        "Select one below to begin installation."
    )
    buttons = [
        [Button.inline("WordSeek", data="mod_wordseek"), Button.inline("WordChain", data="mod_wordchain")],
        [Button.inline("Octopus", data="mod_octopus"), Button.inline("Wordly", data="mod_wordly")],
        [Button.inline("🔙 Back", data="modules_main")]
    ]
    await event.edit(text, buttons=buttons)

# --- 6. CALLBACK HANDLERS ---
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode("utf-8")
    if data == "start_back":
        await send_start_menu(event, edit=True)
    elif data == "rules":
        await event.answer("1. No spamming\n2. One trial per user\n3. Respect the community", alert=True)
    elif data == "dev_info":
        await event.answer("Developed by: @YourUsername\nBackend: SQLite Fast Engine", alert=True)
