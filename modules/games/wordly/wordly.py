import time
import requests
import re
import asyncio
import os
from collections import Counter
from telethon import events

# =========================================
# LOAD DICTIONARY (Shared & Local Cache)
# =========================================
FOLDER = os.path.dirname(__file__)
DICT_CACHE = os.path.join(FOLDER, "wordly_dict.txt")

def load_words():
    valid = []
    # Dictionary cache check taaki startup fast ho
    if not os.path.exists(DICT_CACHE):
        url = "https://raw.githubusercontent.com/dolph/dictionary/master/enable1.txt"
        try:
            data = requests.get(url).text.splitlines()
            with open(DICT_CACHE, "w") as f:
                f.write("\n".join(data))
        except: return []

    with open(DICT_CACHE, "r") as f:
        for w in f:
            w = w.strip().lower()
            if 3 <= len(w) <= 12 and w.isalpha():
                valid.append(w)
    return valid

WORDS_DB = load_words()

# =========================
# THE MODULE REGISTER
# =========================
def register(client):
    # --- Per-User State ---
    client.w_target_chat = None
    client.w_enabled = True
    client.w_loop = False
    client.w_loop_cmd = "/new" 
    client.w_delay = 0.0 # Instant support
    client.w_used_words = set()
    client.w_current_letters = None

    # --- SOLVER ---
    def solve(letters):
        allowed = set(letters.lower())
        candidates = []
        for word in WORDS_DB:
            if word in client.w_used_words: continue
            # Game rule: Letters board me se hi word banna chahiye
            if all(c in allowed for c in word):
                candidates.append(word)
        
        if not candidates: return None
        candidates.sort(key=len, reverse=True)
        best = candidates[0]
        client.w_used_words.add(best)
        return best

    # --- ROBUST LETTER EXTRACTOR (Support for 2 Bots) ---
    def extract_letters(text):
        # Clean text for easier parsing
        text_up = text.upper()
        
        # Mode 1: @WordgamezBot (A, B, C, D format)
        if "," in text:
            return "".join(re.findall(r"[A-Z]", text_up))
        
        # Mode 2: @WordlyGamingBot (A B C D format after board header)
        lines = text_up.splitlines()
        for i, line in enumerate(lines):
            if "LETTERS BOARD" in line or "BOARD:" in line:
                if i + 1 < len(lines):
                    return "".join(re.findall(r"[A-Z]", lines[i+1]))
        
        # Fallback: Just grab all single uppercase letters
        return "".join(re.findall(r"\b[A-Z]\b", text_up))

    # =========================================
    # SAVED MESSAGES COMMANDS (Control Panel)
    # =========================================
    @client.on(events.NewMessage(chats='me'))
    async def control_panel(event):
        text = event.raw_text.lower().strip()
        
        if text == ".won":
            client.w_enabled = True
            await event.edit("✅ **Wordly Solver: ON**")
        elif text == ".woff":
            client.w_enabled = False
            await event.edit("❌ **Wordly Solver: OFF**")
        elif text.startswith(".wloop"):
            if "on" in text:
                client.w_loop = True
                await event.edit("🔄 **Auto-Loop: ON**")
            else:
                client.w_loop = False
                await event.edit("❌ **Auto-Loop: OFF**")
        elif text.startswith(".wdelay"):
            try:
                client.w_delay = float(text.split()[1])
                await event.edit(f"⚡ **Delay:** {client.w_delay}s")
            except: pass
        elif text == ".wstatus":
            status = (
                "📊 **Wordly Status**\n\n"
                f"**Target:** `{client.w_target_chat}`\n"
                f"**Enabled:** `{client.w_enabled}`\n"
                f"**Loop:** `{client.w_loop}`\n"
                f"**Delay:** `{client.w_delay}`"
            )
            await event.edit(status)

    # =========================================
    # AUTO TARGET DETECTION (Outgoing)
    # =========================================
    @client.on(events.NewMessage(outgoing=True))
    async def detect_target(event):
        text = event.raw_text.lower()
        if text.startswith("/new"):
            # Save chat and the EXACT command used (/new or /new@bot)
            client.w_target_chat = event.chat_id
            client.w_loop_cmd = event.raw_text
            client.w_used_words.clear()
            client.w_current_letters = None
            await client.send_message("me", f"🎯 **Wordly Locked:** `{event.chat_id}`\nLoop Command: `{client.w_loop_cmd}`")

    # =========================================
    # GAME HANDLER (The Engine)
    # =========================================
    @client.on(events.NewMessage)
    async def game_handler(event):
        if not client.w_enabled or client.w_target_chat is None: return
        if event.chat_id != client.w_target_chat: return

        msg = event.raw_text
        if not msg: return

        # 1. New Game Detection
        if "TOTAL: 0/" in msg or "MODE IS LIVE" in msg.upper():
            letters = extract_letters(msg)
            if letters:
                client.w_current_letters = letters
                client.w_used_words.clear()
                # Solve first word immediately
                word = solve(client.w_current_letters)
                if word:
                    async with client.action(event.chat_id, 'typing'):
                        if client.w_delay > 0: await asyncio.sleep(client.w_delay)
                        await client.send_message(event.chat_id, word)
            return

        # 2. Game End Detection (For Loop)
        if any(x in msg.upper() for x in ["GAME OVER", "CONGRATS", "TOTAL: 20/20"]):
            client.w_current_letters = None
            if client.w_loop:
                await asyncio.sleep(3)
                await client.send_message(client.w_target_chat, client.w_loop_cmd)
            return

        # 3. Continuous Solving
        if client.w_current_letters and ("TOTAL:" in msg or "remaining time" in msg.lower()):
            if event.out: return # Don't reply to self
            
            word = solve(client.w_current_letters)
            if word:
                async with client.action(event.chat_id, 'typing'):
                    if client.w_delay > 0: await asyncio.sleep(client.w_delay)
                    await client.send_message(event.chat_id, word)
