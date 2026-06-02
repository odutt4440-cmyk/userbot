import os
from bot_instance import bot 
from telethon import events, Button
from config import START_PIC, ADMIN_ID, LOG_GROUP
from database import claim_trial, has_claimed_trial, get_setting, set_setting

# Photo caching handle
START_MEDIA = None

# --- HELPER: PRIVATE ONLY CHECK ---
async def is_private_only(event):
    if not event.is_private:
        # Group me bot sirf ye message bhejega agar koi command use karega
        await event.reply("❌ **Security Alert!**\n\nFor your account safety, this bot only works in **Private DM**.\n\n👉 [Click here to start bot](t.me/YourBotUsername)")
        return False
    return True

# --- 1. MAIN MENU LOGIC ---
async def send_start_menu(event, edit=False):
    global START_MEDIA
    welcome_text = (
        "👋 **Welcome to Userbot Community!**\n\n"
        "Transform your Telegram account into a powerful userbot empire. "
        "High-speed games, automation tools, and fun modules at your fingertips.\n\n"
        "Navigate using the buttons below to get started. 👇"
    )
    
    buttons = [
        [Button.inline("⚙️ Explore Modules", data="modules_main")],
        [Button.inline("🎁 Claim 1-Day Trial", data="claim_trial_btn")],
        [Button.inline("📜 Rules", data="rules"), Button.inline("👨‍💻 Developer", data="dev_info")],
        [Button.inline("🔑 Generate String", data="gen_string_internal")] 
    ]

    try:
        if not START_MEDIA:
            START_MEDIA = await get_setting("START_PIC_ID")

        if edit:
            await event.edit(welcome_text, buttons=buttons)
        else:
            sent_msg = await bot.send_file(
                event.chat_id, 
                START_MEDIA if START_MEDIA else START_PIC, 
                caption=welcome_text, 
                buttons=buttons
            )
            if not START_MEDIA and sent_msg.media:
                START_MEDIA = str(sent_msg.media)
                await set_setting("START_PIC_ID", START_MEDIA)
                
    except Exception as e:
        print(f"Start Menu Error: {e}")
        if edit: await event.edit(welcome_text, buttons=buttons)
        else: await event.respond(welcome_text, buttons=buttons)

# --- 2. COMMAND HANDLERS (/start, /help, /modules) ---

@bot.on(events.NewMessage(pattern=r'(?i)^/start'))
async def start_handler(event):
    if not await is_private_only(event): return
    if LOG_GROUP:
        user = await event.get_sender()
        name = user.first_name if user.first_name else "User"
        await bot.send_message(LOG_GROUP, f"👤 **Bot Started:** {name} (`{event.sender_id}`)")
    await send_start_menu(event)

@bot.on(events.NewMessage(pattern=r'(?i)^/help'))
async def help_handler(event):
    if not await is_private_only(event): return
    help_text = (
        "📖 **Empire Community Help Guide**\n\n"
        "**Available Commands:**\n"
        "• `/start` - Main Menu\n"
        "• `/modules` - Modules List\n"
        "• `/help` - Help Guide\n\n"
        "**Setup Steps:**\n"
        "1. Generate String Session.\n"
        "2. Choose Module and Link String.\n"
        "3. Claim Trial or Pay ₹10.\n"
        "4. Click Activate."
    )
    await event.reply(help_text, buttons=[[Button.inline("⚙️ Open Modules", data="modules_main")]])

@bot.on(events.NewMessage(pattern=r'(?i)^/modules'))
async def modules_cmd(event):
    if not await is_private_only(event): return
    # Seedha modules menu dikhayega
    await modules_main(event, edit=False)

# --- 3. CALLBACK HANDLERS ---

@bot.on(events.CallbackQuery(data="modules_main"))
async def modules_main(event, edit=True):
    text = "📂 **Select a Category:**\n\nChoose the type of automation you want to deploy."
    buttons = [
        [Button.inline("👮 Admin Tools", data="admin_ub"), Button.inline("🎮 Game Bots", data="games_ub")],
        [Button.inline("🔙 Back to Menu", data="start_back")]
    ]
    if edit: await event.edit(text, buttons=buttons)
    else: await event.respond(text, buttons=buttons)

@bot.on(events.CallbackQuery(data="games_ub"))
async def games_menu(event):
    text = (
        "🎮 **Userbot Game Modules**\n\n"
        "**WordSeek Solver:**\n"
        "Commands: `.ws on` | `.ws loop on` | `.ws delay 0.5 1.5`\n\n"
        "**WordChain Pro:**\n"
        "Commands: `on1` | `yes` | `autoplay on` | `spam random` | `settime 1 3`\n\n"
        "**Octopus Engine:**\n"
        "Commands: `/game@OctopusEN_Bot` | `.octo delay 2.6 3.2`\n\n"
        "**Wordly Master:**\n"
        "Commands: `.won` | `.woff` | `.wloop on` | `.wstatus`"
    )
    buttons = [
        [Button.inline("WordSeek", data="mod_wordseek"), Button.inline("WordChain", data="mod_wordchain")],
        [Button.inline("Octopus", data="mod_octopus"), Button.inline("Wordly", data="mod_wordly")],
        [Button.inline("🔙 Back", data="modules_main")]
    ]
    await event.edit(text, buttons=buttons)

@bot.on(events.CallbackQuery(data="claim_trial_btn"))
async def trial_handler(event):
    user_id = event.sender_id
    if await has_claimed_trial(user_id):
        await event.answer("⚠️ You have already claimed your trial!", alert=True)
        return
    success, result = await claim_trial(user_id)
    if success:
        await event.answer("🎉 24-Hour Trial Activated!", alert=True)
        await event.edit("🎁 **Free Trial Activated!**\n\nAccess granted for 24 hours. Go to modules and start your userbot now! 🚀", 
                         buttons=[[Button.inline("⚙️ Open Modules", data="modules_main")]])
    else:
        await event.answer(f"❌ Error: {result}", alert=True)

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode("utf-8")
    if data == "start_back":
        await send_start_menu(event, edit=True)
    elif data == "rules":
        await event.answer("1. No spamming\n2. Maintain subscription\n3. Respect community", alert=True)
    elif data == "dev_info":
        await event.answer("Developed by: @YourUsername\nSystem: SQLite Fast Engine v2.0", alert=True)
