import os
from bot_instance import bot 
from telethon import events, Button
from config import START_PIC, ADMIN_ID, LOG_GROUP
from database import claim_trial, has_claimed_trial, get_setting, set_setting, is_banned, get_ban_info, get_maintenance

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

# --- HELPER: SECURITY & MAINTENANCE CHECK ---
async def global_security_check(event):
    user_id = event.sender_id
    
    # 1. Maintenance Check (Admin is exempt)
    is_maint, maint_text = await get_maintenance()
    if is_maint and user_id != ADMIN_ID:
        await event.reply(f"🛠️ **Bot Under Maintenance**\n\n{maint_text}")
        return False
        
    # 2. Ban Check
    if await is_banned(user_id):
        ban_info = await get_ban_info(user_id) # Returns (time, reason)
        reason = ban_info[1] if ban_info else "No reason provided."
        await event.reply(f"🚫 **Access Denied!**\n\nYou have been banned from using this bot.\n\n**Reason:** `{reason}`\n**Contact:** @YourUsername for appeal.")
        return False
        
    return True

# --- 1. MAIN MENU LOGIC ---
async def send_start_menu(event, edit=False):
    global START_MEDIA
    welcome_text = (
        "𝐖ᴇʟᴄᴏᴍᴇ ᴛᴏ 𝐔sᴇʀʙᴏᴛ 𝐂ᴏᴍᴍᴜɴɪᴛʏ!\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "ᴛʀᴧɴsꜰᴏʀᴍ ʏᴏᴜʀ ᴏʀᴅɪɴᴧʀʏ ᴛᴇʟᴇɢʀᴧᴍ ᴧᴄᴄᴏᴜɴᴛ ɪɴᴛᴏ ᴧ ᴘᴏᴡᴇʀꜰᴜʟ ᴜsᴇʀʙᴏᴛ ᴇᴍᴘɪʀᴇ. "
        "ᴇxᴘᴇʀɪᴇɴᴄᴇ ʜɪɢʜ-sᴘᴇᴇᴅ ɢᴧᴍᴇs, ɴᴇxᴛ-ɢᴇɴ ᴧᴜᴛᴏᴍᴧᴛɪᴏɴ ᴛᴏᴏʟs, ᴧɴᴅ ᴧᴅᴠᴧɴᴄᴇᴅ ᴍᴧɴᴧɢᴇᴍᴇɴᴛ "
        "ᴍᴏᴅᴜʟᴇs ʀɪɢʜᴛ ᴧᴛ ʏᴏᴜʀ ꜰɪɴɢᴇʀᴛɪᴘs. ⚡️🔥"
    )
    
    buttons = [
        [Button.inline("𝐄xᴘʟᴏʀᴇ 𝐌ᴏᴅᴜʟᴇs ", data="modules_main")],
        [Button.inline("𝐂ʟᴧɪᴍ 𝟷-𝐃ᴧʏ 𝐓ʀɪᴧʟ ", data="claim_trial_btn")],
        [Button.inline("𝐒ᴜᴘᴘᴏʀᴛ", data="support_main")], # <--- Naya Button
        [Button.inline("𝐑ᴜʟᴇs  ", data="rules"), Button.inline(" 𝐃ᴇᴠᴇʟᴏᴘᴇʀ", data="dev_info")],
        [Button.inline("𝐆ᴇɴᴇʀᴧᴛᴇ 𝐒ᴇssɪᴏɴ", data="gen_string_internal")] 
    ]

    try:
        # DB se cache uthao
        cached_id = await get_setting("START_PIC_ID")
        
        # 🔥 AUTO-CLEANUP: Agar DB me purana "Kachra" (lambi string) hai, toh use ignore karo
        if cached_id and ("MessageMedia" in cached_id or "Photo(" in cached_id):
            cached_id = None

        if edit:
            await event.edit(welcome_text, buttons=buttons)
        else:
            try:
                # Try sending with Cached ID (Fast)
                sent_msg = await bot.send_file(
                    event.chat_id, 
                    cached_id if cached_id else START_PIC, 
                    caption=welcome_text, 
                    buttons=buttons
                )
                # Agar pehli baar hai ya ID galat thi, toh naya ID save karo
                if not cached_id and sent_msg and sent_msg.photo:
                    await set_setting("START_PIC_ID", str(sent_msg.photo.id))
            except Exception:
                # 🛡️ ULTIMATE FALLBACK: Agar ID fail ho jaye, toh local file se bhejo
                await bot.send_file(
                    event.chat_id, 
                    START_PIC, 
                    caption=welcome_text, 
                    buttons=buttons
                )
                
    except Exception as e:
        print(f"Start Menu Error: {e}")
        if edit: await event.edit(welcome_text, buttons=buttons)
        else: await event.respond(welcome_text, buttons=buttons)

# --- 2. COMMAND HANDLERS ---
@bot.on(events.NewMessage(pattern=r'(?i)^/start'))
async def start_handler(event):
    if not await is_private_only(event): return
    if not await global_security_check(event): return
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

# Command Handler (/modules)
@bot.on(events.NewMessage(pattern=r'(?i)^/modules'))
async def modules_cmd(event):
    if not await is_private_only(event): return
    if not await global_security_check(event): return
    
    # 🔥 FIX: modules_main ko modules_main_logic se replace kiya
    await modules_main_logic(event, edit=False)



# --- 3. CATEGORY HANDLERS (Add Empire Button here) ---

async def modules_main_logic(event, edit=False):
    """Universal logic for modules menu with Global Empire Button"""
    text = (
        "📂 **Select a Category:**\n\n"
        "Choose a module to deploy. Empire users can activate all features "
        "at once using the 'Turbo Deploy' button below."
    )
    buttons = [
        [Button.inline("🚀 Deploy Empire Mode (All Bots)", data="activate_all")], # <--- Yahan add kiya
        [Button.inline("🛡️ Management", data="management_ub"), Button.inline("🥳 Fun Tools", data="fun_ub")],
        [Button.inline("🎮 Game Bots", data="games_ub")],
        [Button.inline("🔙 Back to Menu", data="start_back")]
    ]
    
    if edit:
        try:
            return await event.edit(text, buttons=buttons)
        except:
            pass
    return await event.respond(text, buttons=buttons)



# Button Handler
@bot.on(events.CallbackQuery(data="modules_main"))
async def modules_callback(event):
    if not await global_security_check(event): return
    await modules_main_logic(event, edit=True)

# Command Handler (/modules)
@bot.on(events.NewMessage(pattern=r'(?i)^/modules'))
async def modules_cmd(event):
    if not await is_private_only(event): return
    if not await global_security_check(event): return
    # FIX: function name should be modules_main_logic
    await modules_main_logic(event, edit=False)

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
        [Button.inline("👮 Admin Tools", data="mod_admin")],
        [Button.inline("📢 Tagger (TagAll)", data="mod_tagger")],
        [Button.inline("🔍 Info Tools", data="mod_info")],
        [Button.inline("🔙 Back", data="modules_main")]
    ]
    await event.edit(text, buttons=buttons)

## --- 5. FUN TOOLS MENU (With Auto-Reaction Added!) ---
@bot.on(events.CallbackQuery(data="fun_ub"))
async def fun_menu(event):
    if not await global_security_check(event): return
    text = (
        "🥳 *𝐔sᴇʀʙᴏᴛ 𝐅ᴜɴ 𝐒ᴜɪᴛᴇ* \n\n"
        "👤 *𝐈ᴅᴇɴᴛɪᴛʏ 𝐂规ᴏɴᴇ:* \n"
        "• `.clone` — Reply to copy a profile.\n"
        "• `.revert` — Restore your original profile.\n\n"
        "💤 *𝐀𝐅Κ 𝐒ʏsᴛᴇᴍ:* \n"
        "• `.afk [msg]` — Auto-reply for DMs.\n\n"
        "🖼️ *𝐒ᴛɪᴄᴋᴇʀs & 𝐌ᴇᴍɪꜰʏ:* \n"
        "• `.kang` — Add any sticker/photo to your pack.\n"
        "• `.mm [text]` — Create memes from stickers.\n\n"
        "🎭 *𝐀ᴜᴛᴏ-𝐑ᴇᴧᴄᴛɪᴏɴ (Target/GC):* \n"
        "• `.autoreact [emoji]` — Reply to someone OR type openly in GC.\n"
        "• `.stopreact` — Stop auto-reactions in the current chat."
    )
    buttons = [
        [Button.inline("👤 Identity Clone", data="mod_clone"), Button.inline("💤 AFK Auto-Reply", data="mod_afk")],
        [Button.inline("🖼️ Stickers & Memify", data="mod_stickers"), Button.inline("🎭 Auto-Reaction", data="mod_reaction")],
        [Button.inline("🔙 𝐁ᴧᴄᴋ", data="modules_main")]
    ]
    await event.edit(text, buttons=buttons)

# --- 6. GAMES MENU (Full Long Text Fix) ---
@bot.on(events.CallbackQuery(data="games_ub"))
async def games_menu(event):
    if not await global_security_check(event): return

    # Tera ditto same lamba text
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
    
    buttons = [
        [Button.inline("WordSeek", data="mod_wordseek"), Button.inline("WordChain", data="mod_wordchain")],
        [Button.inline("Octopus", data="mod_octopus"), Button.inline("Wordly", data="mod_wordly")],
        [Button.inline("🔙 Back to Categories", data="modules_main")]
    ]

    try:
        await event.delete() 
        await bot.send_message(event.chat_id, text, buttons=buttons)
    except Exception as e:
        print(f"Error in Games Menu: {e}")
        
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

# --- callback_handler update karo ---
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    if not await global_security_check(event): return
    data = event.data.decode("utf-8")
    
    if data == "start_back":
        await send_start_menu(event, edit=True)
    
    # modules_main yahan se hata diya gaya hai kyunki uska apna @bot.on upar hai
    
    elif data == "rules":
        await event.answer("1. One trial per user.\n2. No spamming commands.\n3. Respect community", alert=True)
    elif data == "dev_info":
        await event.answer("Developed by: @YourUsername\nSystem: SQLite Fast Engine v2.5", alert=True)
        
    
