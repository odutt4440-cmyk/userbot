import os
from bot_instance import bot 
from telethon import events, Button
from config import START_PIC, ADMIN_ID, LOG_GROUP
from database import claim_trial, has_claimed_trial, get_setting, set_setting

# Photo caching handle for instant speed
START_MEDIA = None

# --- HELPER: PRIVATE ONLY CHECK ---
async def is_private_only(event):
    if not event.is_private:
        # Userbot Community professional reply
        await event.reply(
            "❌ **Access Denied!**\n\n"
            "This bot is configured to work only in **Private DM** to ensure user data security.\n\n"
            "👉 Please click the button below to use me in private.",
            buttons=[[Button.url("📩 Open Private Chat", "t.me/YourBotUsername")]] # Update username here
        )
        return False
    return True

# --- 1. MAIN MENU LOGIC ---
async def send_start_menu(event, edit=False):
    global START_MEDIA
    welcome_text = (
        "👋 **Welcome to Userbot Community!**\n\n"
        "Transform your Telegram account into a powerful userbot empire. "
        "We provide high-speed automation tools, smart game solvers, and "
        "premium modules designed for 24/7 performance.\n\n"
        "Navigate using the buttons below to get started. 👇"
    )
    
    buttons = [
        [Button.inline("⚙️ Explore Modules", data="modules_main")],
        [Button.inline("🎁 Claim 1-Day Trial", data="claim_trial_btn")],
        [Button.inline("📜 Rules", data="rules"), Button.inline("👨‍💻 Developer", data="dev_info")],
        [Button.inline("🔑 Generate String", data="gen_string_internal")] 
    ]

    try:
        # Load cached media for lightning speed
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
            # Save media ID for future instant loads
            if not START_MEDIA and sent_msg.media:
                START_MEDIA = str(sent_msg.media)
                await set_setting("START_PIC_ID", START_MEDIA)
                
    except Exception as e:
        print(f"Start Menu Error: {e}")
        if edit: await event.edit(welcome_text, buttons=buttons)
        else: await event.respond(welcome_text, buttons=buttons)

# --- 2. START HANDLER + LOGGER ---
@bot.on(events.NewMessage(pattern=r'(?i)^/start'))
async def start_handler(event):
    if not await is_private_only(event):
        return

    if LOG_GROUP:
        user = await event.get_sender()
        name = user.first_name if user.first_name else "User"
        uid = event.sender_id
        username = f"@{user.username}" if user.username else "N/A"
        await bot.send_message(LOG_GROUP, f"👤 **Bot Started:**\nName: {name}\nID: `{uid}`\nUser: {username}")
    
    await send_start_menu(event)

# --- 3. TRIAL SYSTEM ---
@bot.on(events.CallbackQuery(data="claim_trial_btn"))
async def trial_handler(event):
    user_id = event.sender_id
    if await has_claimed_trial(user_id):
        await event.answer("⚠️ You have already used your free trial!", alert=True)
        return

    success, result = await claim_trial(user_id)
    if success:
        await event.answer("🎉 24-Hour Trial Activated!", alert=True)
        await event.edit(
            "🎁 **Free Trial Activated!**\n\n"
            "You now have **full premium access** for the next 24 hours.\n"
            "Explore the modules and deploy your first userbot now! 🚀",
            buttons=[[Button.inline("⚙️ Open Modules", data="modules_main")]]
        )
    else:
        await event.answer(f"❌ Error: {result}", alert=True)

# --- 4. GAMES SUB-MENU (Professional Command List) ---
@bot.on(events.CallbackQuery(data="games_ub"))
async def games_menu(event):
    text = (
        "🎮 **Userbot Game Modules**\n\n"
        "Select a game below to link your account. Once linked, use these commands in any chat:\n\n"
        "🧩 **WordSeek Solver:**\n"
        "• `.ws on` | `.ws off` - Toggle Solver\n"
        "• `.ws loop on` | `.ws loop off` - Auto Play\n\n"
        "📝 **Wordly Master:**\n"
        "• `.won` | `.woff` - Toggle Automation\n"
        "• `.wloop on` - Auto New Game\n"
        "• `.wdelay 0.5` - Set Speed\n\n"
        "🐙 **Octopus Engine:**\n"
        "• `/game@OctopusEN_Bot` - Trigger Solver\n"
        "• `.octo delay 2.6 3.2` - Custom Speed\n\n"
        "⛓️ **WordChain Pro:**\n"
        "• `on1` / `on2` - Join detected games\n"
        "• `autoplay on` - Fully automatic play\n"
        "• `spam random` or `spam x` - Set ending letter\n"
        "• `status` - Check active games"
    )
    buttons = [
        [Button.inline("WordSeek", data="mod_wordseek"), Button.inline("WordChain", data="mod_wordchain")],
        [Button.inline("Octopus", data="mod_octopus"), Button.inline("Wordly", data="mod_wordly")],
        [Button.inline("🔙 Back to Categories", data="modules_main")]
    ]
    await event.edit(text, buttons=buttons)

# --- 5. CATEGORY & UTILITY CALLBACKS ---
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode("utf-8")
    
    if data == "start_back":
        await send_start_menu(event, edit=True)
        
    elif data == "modules_main":
        text = (
            "📂 **Module Categories**\n\n"
            "Our engine supports multiple types of automation. "
            "Please select a category below to continue."
        )
        buttons = [
            [Button.inline("👮 Admin Tools", data="admin_ub"), Button.inline("🎮 Game Bots", data="games_ub")],
            [Button.inline("🔙 Back to Main Menu", data="start_back")]
        ]
        await event.edit(text, buttons=buttons)
        
    elif data == "rules":
        rules_text = (
            "🛡️ **Community Guidelines:**\n\n"
            "1. One Free Trial per user account.\n"
            "2. Do not flood or spam bot commands.\n"
            "3. Multi-accounting to exploit trials is forbidden.\n"
            "4. Subscription fee is ₹10 to support server costs."
        )
        await event.answer(rules_text, alert=True)
        
    elif data == "dev_info":
        dev_text = (
            "👨‍💻 **Developer Info:**\n\n"
            "Developed by: @YourUsername\n"
            "Engine: SQLite FastSync v2.0\n\n"
            "Join our community for updates and support!"
        )
        await event.answer(dev_text, alert=True)
