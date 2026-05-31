from bot_instance import bot 
from telethon import events, Button
from database import save_user_session, get_user_session

# Ek temporary dictionary taaki bot ko pata rahe kaunsa user string bhej raha hai
WAITING_FOR_STR = {}

# --- 1. JAB USER KISI MODULE PE CLICK KARE ---
@bot.on(events.CallbackQuery(pattern=r"mod_"))
async def login_step_1(event):
    user_id = event.sender_id
    # Button data se game ka naam nikalna (e.g., mod_wordseek -> wordseek)
    module_name = event.data.decode("utf-8").replace("mod_", "")
    
    # Check karein ki user ki string pehle se hai ya nahi
    existing_session = await get_user_session(user_id)
    
    if existing_session:
        # Agar string pehle se hai, toh direct payment ya activation dikhao
        await event.edit(
            f"✅ **Session Found!**\nModule: `{module_name.capitalize()}`\n\n"
            "Aapka account pehle se logged in hai. "
            "Kya aap isse activate karna chahte hain?",
            buttons=[
                [Button.inline("🚀 Activate Now", data=f"activate_{module_name}")],
                [Button.inline("🔄 Change String", data=f"relog_{module_name}")]
            ]
        )
    else:
        # Agar string nahi hai, toh mango
        WAITING_FOR_STR[user_id] = module_name
        await event.edit(
            f"🔑 **Login Required for {module_name.capitalize()}**\n\n"
            "Apne userbot ko chalane ke liye mujhe apni **Telethon String Session** bhejein.\n\n"
            "⚠️ **Note:** String session ko niche chat mein paste karein.",
            buttons=[Button.inline("❌ Cancel", data="start_back")]
        )

# --- 2. JAB USER STRING SESSION BHEJE ---
@bot.on(events.NewMessage)
async def receive_string(event):
    user_id = event.sender_id
    
    # Check karein ki kya hum is user se string expect kar rahe hain
    if user_id in WAITING_FOR_STR:
        string_session = event.text.strip()
        module = WAITING_FOR_STR[user_id]
        
        # Basic validation (Telethon strings lambi hoti hain)
        if len(string_session) < 50:
            await event.reply("❌ **Invalid String!**\nTelethon string kafi lambi hoti hai. Kripya sahi string bhejein.")
            return
        
        # Database mein save karein
        await save_user_session(user_id, string_session)
        
        # Confirmation message
        await event.reply(
            f"✅ **String Saved Successfully!**\n\n"
            f"Ab aap `{module.capitalize()}` module use karne ke liye taiyar hain.\n"
            "Lekin isse activate karne ke liye aapko subscription (₹10) chahiye.",
            buttons=[[Button.inline("💳 Pay ₹10", data="pay_now")]]
        )
        
        # Waiting list se user ko hata dein
        del WAITING_FOR_STR[user_id]

# --- 3. RELOG LOGIC (String badalne ke liye) ---
@bot.on(events.CallbackQuery(pattern=r"relog_"))
async def relog(event):
    user_id = event.sender_id
    module = event.data.decode("utf-8").replace("relog_", "")
    WAITING_FOR_STR[user_id] = module
    await event.edit("🔄 **Change String:**\nNayi Telethon String Session bhejein:")
