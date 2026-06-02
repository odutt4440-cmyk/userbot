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
        await event.reply(
            "❌ **Access Denied!**\n\n"
            "This bot is configured to work only in **Private DM** for security.\n\n"
            "👉 Please click the button below to use me in private.",
            buttons=[[Button.url("📩 Open Private Chat", "t.me/YourBotUsername")]] # Update username
        )
        return False
    return True

# --- 1. MAIN MENU LOGIC ---
async def send_start_menu(event, edit=False):
    global START_MEDIA
    welcome_text = (
        "👋 **Welcome to Userbot Community!**\n\n"
        "Transform your Telegram account into a powerful userbot empire. "
        "High-speed games, automation tools, and management modules at your fingertips.\n\n"
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

# --- 2. COMMAND HANDLERS ---
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
    help_text = "📖 **Help Guide**\n\nUse buttons below to explore and activate premium modules."
    await event.reply(help_text, buttons=[[Button.inline("⚙️ Open Modules", data="modules_main")]])

@bot.on(events.NewMessage(pattern=r'(?i)^/modules'))
async def modules_cmd(event):
    if not await is_private_only(event): return
    await modules_main(event, edit=False)

# --- 3. CATEGORY HANDLERS ---
@bot.on(events.CallbackQuery(data="modules_main"))
async def modules_main(event, edit=True):
    text = "📂 **Select a Category:**\n\nChoose the type of automation you want to deploy."
    buttons = [
        [Button.inline("🛡️ Management", data="management_ub"), Button.inline("🥳 Fun Tools", data="fun_ub")],
        [Button.inline("🎮 Game Bots", data="games_ub")],
        [Button.inline("🔙 Back to Menu", data="start_back")]
    ]
    if edit: await event.edit(text, buttons=buttons)
    else: await event.respond(text, buttons=buttons)

# --- 4. MANAGEMENT TOOLS MENU ---
@bot.on(events.CallbackQuery(data="management_ub"))
async def management_menu(event):
    text = (
        "🛡️ **Userbot Management Modules**\n\n"
        "**Group Admin Tools:**\n"
        "• `.ban` - Reply to a user to ban them.\n"
        "• `.mute` - Reply to a user to mute them.\n"
        "• `.warn` - Give a warning (3 warns = Auto Ban).\n"
        "• `.banall` - Clean a group (Bans all non-admins).\n\n"
        "**General Info Tools:**\n"
        "• `.id` - Get Chat/User ID.\n"
        "• `.info` - Reply to see full user details."
        "**📢 Tagging Tools:**\n"
        "• `.tagall <msg>` - Mention everyone in the group.\n"
        "• `.stopall` - Stop the active tag process.\n"
        "• `.tagdelay <sec>` - Set delay (Default 3s)."
    )
    buttons = [
        [Button.inline("Deploy Management", data="mod_management")],
        [Button.inline("🔙 Back", data="modules_main")]
    ]
    await event.edit(text, buttons=buttons)

# --- 5. FUN TOOLS MENU ---
@bot.on(events.CallbackQuery(data="fun_ub"))
async def fun_menu(event):
    text = (
        "🥳 **Userbot Fun Modules**\n\n"
        "**Identity Clone Tool:**\n"
        "• `.clone` - Reply to any user to steal their Name, Bio, and Photo.\n"
        "• `.revert` - Reset your profile back to original identity."
    )
    buttons = [
        [Button.inline("Deploy Clone Tool", data="mod_clone")],
        [Button.inline("🔙 Back", data="modules_main")]
    ]
    await event.edit(text, buttons=buttons)

@bot.on(events.CallbackQuery(data="games_ub"))
async def games_menu(event):
    # Professional list of ALL available commands inside the files
    text = (
        "🎮 **Userbot Game Modules**\n\n"
        "Deploy high-speed solvers. Use these commands in any chat once active:\n\n"
        "🧩 **WordSeek Solver:**\n"
        "• `.ws on` | `.ws off` — Toggle Solver\n"
        "• `.ws loop on` | `.ws loop off` — Auto Restart\n"
        "• `.ws delay 0.5 1.5` — Set Min/Max speed\n\n"
        "📝 **Wordly Master:**\n"
        "• `.won` | `.woff` — Toggle Automation\n"
        "• `.wloop on` | `.wloop off` — Auto New Game\n"
        "• `.wdelay 0.5` — Set Typing Delay\n"
        "• `.wstatus` — Check Round Stats\n\n"
        "🐙 **Octopus Engine:**\n"
        "• `/game@OctopusEN_Bot` — Lock & Solve\n"
        "• `.octo delay 2.6 3.2` — Adjust Timing\n\n"
        "⛓️ **WordChain Pro:**\n"
        "• `on1`, `on2`... — Join specific game ID\n"
        "• `yes` — Join last detected game\n"
        "• `autoplay on` | `off` — Toggle Auto-play\n"
        "• `spam random` | `spam <char>` — Ending mode\n"
        "• `settime 1 3` — Set Min/Max delay\n"
        "• `status` — Check all active games"
    )
    
    buttons = [
        [Button.inline("WordSeek", data="mod_wordseek"), Button.inline("WordChain", data="mod_wordchain")],
        [Button.inline("Octopus", data="mod_octopus"), Button.inline("Wordly", data="mod_wordly")],
        [Button.inline("🔙 Back to Categories", data="modules_main")]
    ]
    
    await event.edit(text, buttons=buttons)

# --- 7. TRIAL & CALLBACKS ---
@bot.on(events.CallbackQuery(data="claim_trial_btn"))
async def trial_handler(event):
    user_id = event.sender_id
    if await has_claimed_trial(user_id):
        await event.answer("⚠️ You have already used your free trial!", alert=True)
        return
    success, result = await claim_trial(user_id)
    if success:
        await event.answer("🎉 24-Hour Trial Activated!", alert=True)
        await event.edit("🎁 **Free Trial Activated!**\n\nAccess granted for 24 hours. Start your userbot now! 🚀", 
                         buttons=[[Button.inline("⚙️ Open Modules", data="modules_main")]])
    else:
        await event.answer(f"❌ Error: {result}", alert=True)

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode("utf-8")
    if data == "start_back":
        await send_start_menu(event, edit=True)
    elif data == "rules":
        await event.answer("1. One trial per user.\n2. No spamming commands.\n3. Respect community", alert=True)
    elif data == "dev_info":
        await event.answer("Developed by: @YourUsername\nSystem: SQLite Fast Engine v2.5", alert=True)
