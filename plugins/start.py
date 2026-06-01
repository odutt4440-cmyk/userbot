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
        await event.reply("❌ **Security Notice:**\n\nThis bot commands only work in **Private Chat (DM)** for security reasons.\n\n👉 Please use me here: @YourBotUsername")
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
        [Button.inline("⚙️ Modules", data="modules_main")],
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

# --- 2. START HANDLER ---
@bot.on(events.NewMessage(pattern=r'(?i)^/start'))
async def start_handler(event):
    # 🛡️ Gatekeeper: Check if DM
    if not await is_private_only(event):
        return

    if LOG_GROUP:
        user = await event.get_sender()
        name = user.first_name if user.first_name else "User"
        username = f"@{user.username}" if user.username else "N/A"
        await bot.send_message(LOG_GROUP, f"👤 **New User Started:**\nName: {name}\nID: `{event.sender_id}`\nUser: {username}")
    
    await send_start_menu(event)

# --- 3. TRIAL SYSTEM ---
@bot.on(events.CallbackQuery(data="claim_trial_btn"))
async def trial_handler(event):
    user_id = event.sender_id
    if await has_claimed_trial(user_id):
        await event.answer("⚠️ You have already claimed your trial!", alert=True)
        return

    success, result = await claim_trial(user_id)
    if success:
        await event.answer("🎉 24-Hour Trial Activated!", alert=True)
        await event.edit(
            "🎁 **Free Trial Activated!**\n\nYou now have **full access** for 24 hours.\n"
            "Open the Modules menu and start your first bot! 🚀",
            buttons=[[Button.inline("⚙️ Open Modules", data="modules_main")]]
        )
    else:
        await event.answer(f"❌ Error: {result}", alert=True)

# --- 4. GAMES SUB-MENU WITH COMMANDS ---
@bot.on(events.CallbackQuery(data="games_ub"))
async def games_menu(event):
    text = (
        "🎮 **Userbot Games Center**\n\n"
        "Click a game to login. Commands for each game:\n\n"
        "🟢 **WordSeek:** `.ws on` | `.ws off` | `.ws loop on`\n"
        "🟢 **Wordly:** `.won` | `.woff` | `.wstatus` | `.wdelay 0.5`\n"
        "🟢 **Octopus:** `/game@OctopusEN_Bot` | `.octo delay 2.6 3.2`\n"
        "🟢 **WordChain:** `on1` | `autoplay on` | `status`"
    )
    buttons = [
        [Button.inline("WordSeek", data="mod_wordseek"), Button.inline("WordChain", data="mod_wordchain")],
        [Button.inline("Octopus", data="mod_octopus"), Button.inline("Wordly", data="mod_wordly")],
        [Button.inline("🔙 Back", data="modules_main")]
    ]
    await event.edit(text, buttons=buttons)

# --- 5. OTHER CALLBACKS ---
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode("utf-8")
    if data == "start_back":
        await send_start_menu(event, edit=True)
    elif data == "modules_main":
        text = "📂 **Select a Category:**"
        buttons = [
            [Button.inline("👮 Admin Tools", data="admin_ub"), Button.inline("🎮 Game Bots", data="games_ub")],
            [Button.inline("🔙 Back to Menu", data="start_back")]
        ]
        await event.edit(text, buttons=buttons)
    elif data == "rules":
        await event.answer("1. One trial per user.\n2. No spamming commands.\n3. Maintain sub to keep bot alive.", alert=True)
    elif data == "dev_info":
        await event.answer("Developed by: @YourUsername\nSaaS Userbot Engine v2.0", alert=True)
