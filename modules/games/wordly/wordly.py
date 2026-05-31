import time
import requests
import re
import asyncio
from collections import Counter
from telethon import events

# =========================
# LOAD DICTIONARY (Shared)
# =========================
def load_words():
    # Dictionary loading is done once to save RAM across all users
    url = "https://raw.githubusercontent.com/dolph/dictionary/master/enable1.txt"
    try:
        data = requests.get(url).text.splitlines()
        valid = []
        for w in data:
            w = w.lower().strip()
            if 8 <= len(w) <= 12 and w.isalpha():
                valid.append((w, Counter(w)))
        return valid
    except Exception as e:
        print(f"Error loading dictionary: {e}")
        return []

WORDS_DB = load_words()

# =========================
# THE MODULE REGISTER
# =========================
def register(client):
    """
    This function is called by the session manager for each user.
    'client' is the individual user's account session.
    """

    # --- CONFIG (Per User State) ---
    client.w_rounds_limit = 20
    client.w_target_chat = None
    client.w_enabled = True
    client.w_loop = False
    client.w_delay = 0.0 

    client.w_used_words = set()
    client.w_round_count = 0
    client.w_current_letters = None

    # --- SOLVER ---
    def solve(letters):
        allowed = set(letters.lower())
        candidates = []
        for word, wc in WORDS_DB:
            if word in client.w_used_words:
                continue
            if all(c in allowed for c in word):
                candidates.append(word)
        
        if not candidates:
            return None

        candidates.sort(key=len, reverse=True)
        best = candidates[0]
        client.w_used_words.add(best)
        return best

    # --- LETTER EXTRACTOR ---
    def extract_letters(text):
        m = re.search(r'([A-Z](?:\s*,\s*[A-Z])+)', text.upper())
        if not m:
            return None
        return "".join(re.findall(r"[A-Z]", m.group(1)))

    # =========================
    # SAVED MESSAGES COMMANDS
    # =========================
    @client.on(events.NewMessage(chats='me'))
    async def control_panel(event):
        cmd = event.raw_text.lower().split()
        if not cmd:
            return

        if cmd[0] == ".won":
            client.w_enabled = True
            await event.edit("✅ **Wordly Enabled**")

        elif cmd[0] == ".woff":
            client.w_enabled = False
            await event.edit("❌ **Wordly Disabled**")

        elif cmd[0] == ".wloop":
            if len(cmd) > 1:
                client.w_loop = (cmd[1] == "on")
                await event.edit(f"🔄 **Loop:** {'ON' if client.w_loop else 'OFF'}")

        elif cmd[0] == ".wdelay":
            if len(cmd) > 1:
                try:
                    client.w_delay = float(cmd[1])
                    await event.edit(f"⚡ **Delay Set To:** {client.w_delay}s")
                except: pass

        elif cmd[0] == ".wstatus":
            status = (
                "📊 **WORDLY STATUS**\n\n"
                f"**Target:** `{client.w_target_chat}`\n"
                f"**Enabled:** `{client.w_enabled}`\n"
                f"**Loop:** `{client.w_loop}`\n"
                f"**Delay:** `{client.w_delay}`\n"
                f"**Rounds:** `{client.w_round_count}/{client.w_rounds_limit}`"
            )
            await event.edit(status)

    # =========================
    # AUTO TARGET DETECTION
    # =========================
    @client.on(events.NewMessage(outgoing=True))
    async def detect_target(event):
        text = event.raw_text.strip().lower()
        if text in ["/new", "/new@wordgamezbot"]:
            client.w_target_chat = event.chat_id
            client.w_round_count = 0
            client.w_current_letters = None
            client.w_used_words.clear()
            await client.send_message("me", f"🎯 **Target selected:** `{event.chat_id}`\nReady to solve Wordly rounds.")

    # =========================
    # GAME HANDLER
    # =========================
    @client.on(events.NewMessage)
    async def game_handler(event):
        if not client.w_enabled or client.w_target_chat is None:
            return

        if event.chat_id != client.w_target_chat:
            return

        msg = event.raw_text
        if not msg:
            return
        text = msg.upper()

        # NEW GAME DETECTION
        if "TOTAL: 0/20" in text:
            client.w_current_letters = extract_letters(msg)
            if not client.w_current_letters:
                return
            client.w_round_count = 0
            client.w_used_words.clear()
            return

        # GAME OVER DETECTION
        if "GAME OVER" in text or "TOTAL: 20/20" in text:
            client.w_current_letters = None
            if client.w_loop:
                await asyncio.sleep(3)
                await client.send_message(client.w_target_chat, "/new@WordgamezBot")
            return

        # SOLVING LOGIC
        if not client.w_current_letters or "TOTAL:" not in text:
            return

        if client.w_round_count >= client.w_rounds_limit:
            return

        word = solve(client.w_current_letters)
        if not word:
            return

        client.w_round_count += 1
        
        # Simulating human behavior
        async with client.action(event.chat_id, 'typing'):
            if client.w_delay > 0:
                await asyncio.sleep(client.w_delay)
            await client.send_message(event.chat_id, word)
