from bot_instance import bot
from telethon import events, Button
from database import global_security_check

# --- PRICING PLANS COMMAND: /plan ---
@bot.on(events.NewMessage(pattern=r'(?i)^/plan'))
async def plans_command_handler(event):
    # 🛡️ Security Check (Private Only + Ban Check)
    if not event.is_private:
        return
    
    if not await global_security_check(event):
        return

    plan_text = (
        "💎 **Empire Userbot Premium Plans**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "✨ **Standard Tiers** (1 Module at a time)\n"
        "• 15 Days ➔ **₹10**\n"
        "• 30 Days ➔ **₹30**\n\n"
        "🚀 **Empire Tiers** (All Modules active)\n"
        "• 15 Days ➔ **₹15**\n"
        "• 30 Days ➔ **₹35**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎁 **New User?** Claim your 24h Free Trial first!\n\n"
        "👇 Click below to select a plan and get payment details:"
    )

    buttons = [
        [Button.inline("💳 Buy / Upgrade Plan", data="pay_now")],
        [Button.inline("🎁 Claim Free Trial", data="claim_trial_btn")],
        [Button.inline("🔙 Main Menu", data="start_back")]
    ]

    await event.reply(plan_text, buttons=buttons)
