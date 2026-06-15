from bot_instance import bot
from telethon import events, Button
from database import global_security_check, is_banned

# --- 1. ENTRY POINT (/commands) ---

@bot.on(events.NewMessage(pattern=r'(?i)^/commands'))
async def commands_handler(event):
    if not event.is_private:
        return await event.reply("❌ **Access Denied!**\n\nPlease use this command in Private DM.")
    
    if not await global_security_check(event): return

    text = (
        "📖 **𝐄ᴍᴘɪʀᴇ 𝐂ᴏᴍᴍᴧɴᴅ 𝐂ᴇɴᴛᴇʀ**\n\n"
        "Welcome to the Master Guide. Select a category below to explore all commands "
        "available in your Userbot Suite. Use these in your **Saved Messages**."
    )
    buttons = [
        [Button.inline("🛡️ Management", data="cmd_manage"), Button.inline("🥳 Fun Suite", data="cmd_fun")],
        [Button.inline("🎮 Game Solvers", data="cmd_games")],
        [Button.inline("🔙 Back to Menu", data="start_back")]
    ]
    await event.reply(text, buttons=buttons)

# --- 2. MANAGEMENT CATEGORY ---

@bot.on(events.CallbackQuery(data="cmd_manage"))
async def help_manage(event):
    text = (
        "🛡️ **Userbot Management Modules**\n\n"
        "**Group Admin Tools:**\n"
        "• `.ban` - Reply to a user to ban them.\n"
        "• `.mute` - Reply to a user to mute them.\n"
        "• `.warn` - Give a warning (3 warns = Auto Ban).\n"
        "• `.banall` - Clean a group (Bans all non-admins).\n\n"
        "**General Info Tools:**\n"
        "• `.id` - Get Chat/User ID.\n"
        "• `.info` - Reply to see full user details.\n\n"
        "**📢 Tagging Tools:**\n"
        "• `.tagall <msg>` - Mention everyone in the group.\n"
        "• `.stopall` - Stop the active tag process.\n"
        "• `.tagdelay <sec>` - Set delay (Default 3s).\n\n"
        "**🕵️ Stealth Monitor (New):**\n"
        "• `.snatcher on/off` — Auto-save view-once media.\n"
        "• `.antidelete on/off` — Log deleted messages in Saved Msg."
    )
    await event.edit(text, buttons=[[Button.inline("🔙 Back", data="cmd_back_main")]])

# --- 3. FUN CATEGORY ---

@bot.on(events.CallbackQuery(data="cmd_fun"))
async def help_fun(event):
    text = (
        "🥳 **𝐔sᴇʀʙᴏᴛ 𝐅ᴜɴ 𝐒ᴜɪᴛᴇ**\n\n"
        "👤 **𝐈ᴅᴇɴᴛɪᴛʏ & 𝐀𝐅𝐊:**\n"
        "• `.clone` — Copy a profile. | `.revert` — Restore.\n"
        "• `.afk [msg]` — Set auto-reply for DMs/Mentions.\n\n"
        "🖼️ **𝐒ᴛɪᴄᴋᴇʀs & 𝐌ᴇᴍɪꜰʏ:**\n"
        "• `.kang [name]` — Create a new sticker pack.\n"
        "• `.add [name]` — Add sticker to your existing pack.\n"
        "• `.pack [name]` — Get your custom pack link.\n"
        "• `.delsticker [name]` — Remove sticker from pack.\n"
        "• `.delpack [name]` — Delete full pack from Telegram.\n"
        "• `.mm [Top] ; [Bottom]` — Create meme from media.\n\n"
        "🎭 **𝐀ᴜᴛᴏ-𝐑ᴇᴧᴄᴛɪᴏɴ:**\n"
        "• `.autoreact [emoji]` — Target user (Reply) or GC.\n"
        "• `.stopreact` — Stop auto-reactions in chat.\n\n"
        "✨ **𝐄xᴛʀᴧ 𝐅ᴜɴ (𝐀𝐒𝐂𝐈𝐈 & 𝐋𝐨ᴏ𝐩𝐬):**\n"
        "• `.hi` | `.hello` | `.bear` | `.fuck` | `.gn` | `.gm` — Arts.\n"
        "• `.hehe` | `.sad` | `.heart` | `.sleep` — Emoji Loops.\n"
        "• `.hack` — Hacking Anim. | `.greet` — Random Wish.\n"
        "• `.alive` — Check your userbot online status.\n\n"
        "⚔️ **𝐑ᴧɪᴅ 𝐒ᴜɪᴛᴇ (𝐀𝐠𝐠𝐫𝐞𝐬𝐬𝐢𝐯𝐞):**\n"
        "• `.spam [count] [text]` — High-speed message spam.\n"
        "• `.raid [count] [target]` — Insult raid on a user.\n"
        "• `.replyraid` (Reply) — Auto-insult reply engine.\n"
        "• `.delayraid [delay] [count] [target]` — Safe raid.\n"
        "• `.stop` — Kill raids. | `.clear` — Delete 100 msgs.\n"
        "• `.photo` — Download all profile photos of a user."
    )
    await event.edit(text, buttons=[[Button.inline("🔙 Back", data="cmd_back_main")]])

# --- 4. GAMES CATEGORY (Your Full Text) ---

@bot.on(events.CallbackQuery(data="cmd_games"))
async def help_games(event):
    text = (
        "🎮 **Userbot Game Modules**\n\n"
        "Deploy high-speed solvers. Use these commands in saved message once active:\n\n"
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
        "• `.octo on`- before starting game command\n"
        "• after starting choose rounds and mode\n"
        "• `.octo off`- it will stop the bot\n"
        "• `.octo delay 2.6 3.2` — Adjust Timing\n\n"
        "⛓️ **WordChain Pro:**\n"
        "• `on1`, `on2`... — Join specific game ID remember this id to perform command to play in multi gc\n"
        "• `ban y` | `ban y onx` — ban letter ending from y or any letter u want onx is the gc id u get in starting\n"
        "• `unban y`| `unban y onx` — unban letter ending from y or any letter u want\n"
        "• `spam random` | `spam <char>` — Ending mode\n"
        "• `spam longest` — Spam longest words\n"
        "• `settime 1 3 onx` — Set Min/Max delay\n"
        "• `status onx` — Check  and status regarding about ban and spam for specific gc\n"
        "• `status` — Check all active games and status regarding about ban and spam"
    )
    await event.edit(text, buttons=[[Button.inline("🔙 Back", data="cmd_back_main")]])

# --- 5. NAVIGATION HELPERS ---

@bot.on(events.CallbackQuery(data="cmd_back_main"))
async def help_back(event):
    text = (
        "📖 **𝐄ᴍᴘɪʀᴇ 𝐂ᴏᴍᴍᴧɴᴅ 𝐂ᴇɴᴛᴇʀ**\n\n"
        "Select a category below to explore all commands."
    )
    buttons = [
        [Button.inline("🛡️ Management", data="cmd_manage"), Button.inline("🥳 Fun Suite", data="cmd_fun")],
        [Button.inline("🎮 Game Solvers", data="cmd_games")],
        [Button.inline("🔙 Back to Menu", data="start_back")]
    ]
    await event.edit(text, buttons=buttons)

# Basic /help for quick info
@bot.on(events.NewMessage(pattern=r'(?i)^/help'))
async def quick_help(event):
    if not event.is_private: return
    text = (
        "📖 **Empire Help Guide**\n\n"
        "• `/start` - Main Menu\n"
        "• `/commands` - Full Command List\n"
        "• `/modules` - Manage Your Bots"
    )
    await event.reply(text, buttons=[[Button.inline("📜 View Commands", data="cmd_back_main")]])
