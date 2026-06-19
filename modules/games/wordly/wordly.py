import time
import requests
import re
import asyncio
import os
from collections import Counter
from telethon import events

# =========================================
# LOAD DICTIONARY
# =========================================
FOLDER = os.path.dirname(__file__)
DICT_CACHE = os.path.join(FOLDER, "wordly_dict.txt")

def load_words():
    valid = []
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

def register(client):
    # State management
    client.w_target_chat = None
    client.w_enabled = True
    client.w_loop = False
    client.w_loop_cmd = "/new" 
    client.w_delay = 0.5
    client.w_used_words = set()
    client.w_current_letters = None
    client.w_can_repeat = False # New rule detection

    # --- ADVANCED SOLVER ---
    def solve(letters):
        if not letters: return None
        allowed_set = set(letters.lower())
        board_counts = Counter(letters.lower())
        
        candidates = []
        for word in WORDS_DB:
            if word in client.w_used_words: continue
            
            word_set = set(word)
            # Rule check: Kya word ke saare letters board par hain?
            if word_set.issubset(allowed_set):
                # Agar repeat allowed nahi hai (WordgamezBot rule)
                if not client.w_can_repeat:
                    word_counts = Counter(word)
                    if all(word_counts[c] <= board_counts[c] for c in word_counts):
                        candidates.append(word)
                else:
                    # Agar repeat allowed hai (WordlyGamingBot rule)
                    candidates.append(word)
        
        if not candidates: return None
        # Solve longest available word
        candidates.sort(key=len, reverse=True)
        best = candidates[0]
        client.w_used_words.add(best)
        return best

    # --- SMART LETTER EXTRACTOR (Support Both Bots) ---
    def extract_letters(text):
        text_up = text.upper()
        
        # Mode 1: @WordgamezBot (Look for line with most commas)
        lines = text_up.splitlines()
        for line in lines:
            if line.count(",") >= 4:
                return "".join(re.findall(r"[A-Z]", line))
        
        # Mode 2: @WordlyGamingBot (Look for letters inside brackets or special emojis)
        # Regex to find letters between ( ) or emojis
        match = re.search(r"[\(\u2934]\s*([A-Z\s]+)\s*[\)\u2935]", text_up)
        if match:
            return "".join(re.findall(r"[A-Z]", match.group(1)))
            
        # Fallback: Just get the biggest block of single letters
        all_caps = re.findall(r"\b[A-Z]\b", text_up)
        if len(all_caps) >= 5:
            return "".join(all_caps)
            
        return None

    # =========================================
    # CONTROL PANEL (.won, .woff, .wloop, .wdelay, .wstatus)
    # =========================================
    @client.on(events.NewMessage(chats='me'))
    async def control_panel(event):
        text = event.raw_text.lower().strip()
        if text == ".won":
            client.w_enabled = True
            await event.edit("✅ **Wordly Master: Online**")
        elif text == ".woff":
            client.w_enabled = False
            await event.edit("❌ **Wordly Master: Offline**")
        elif text.startswith(".wloop"):
            client.w_loop = "on" in text
            await event.edit(f"{'🔄' if client.w_loop else '❌'} **Auto-Loop:** {'ON' if client.w_loop else 'OFF'}")
        elif text.startswith(".wdelay"):
            try:
                client.w_delay = float(text.split()[1])
                await event.edit(f"⚡ **Delay Set to:** {client.w_delay}s")
            except: pass
        elif text == ".wstatus":
            await event.edit(f"📊 **Wordly Stats**\nEnabled: `{client.w_enabled}`\nTarget Chat: `{client.w_target_chat}`\nRepeat Allowed: `{client.w_can_repeat}`")

    # =========================================
    # TARGET & SOLVE LOGIC
    # =========================================
    @client.on(events.NewMessage(outgoing=True))
    async def detect_target(event):
        if event.raw_text.lower().startswith("/new"):
            client.w_target_chat = event.chat_id
            client.w_loop_cmd = event.raw_text
            client.w_used_words.clear()
            await client.send_message("me", f"🎯 **Wordly Locked:** `{event.chat_id}`\nCommand: `{client.w_loop_cmd}`")

    @client.on(events.NewMessage)
    async def game_handler(event):
        if not client.w_enabled or not client.w_target_chat: return
        if event.chat_id != client.w_target_chat: return
        if event.out: return # Bot should not reply to itself

        msg = event.raw_text
        msg_up = msg.upper()

        # Detection: Is it a game board?
        is_game = "TOTAL:" in msg_up or "LETTERS BOARD" in msg_up or "REMAINING TIME" in msg_up or "MODE IS LIVE" in msg_up
        
        if is_game:
            # Rule detection: Can letters repeat?
            client.w_can_repeat = "LETTERS CAN BE REPEATED" in msg_up
            
            letters = extract_letters(msg)
            if letters:
                # If it's a new round (Total 0), reset used words
                if "TOTAL: 0/" in msg_up or "0/20" in msg_up:
                    client.w_used_words.clear()
                
                client.w_current_letters = letters
                word = solve(client.w_current_letters)
                if word:
                    if client.w_delay > 0: await asyncio.sleep(client.w_delay)
                    await client.send_message(event.chat_id, word)
            return

        # Auto-Restart Round
        if any(x in msg_up for x in ["GAME OVER", "CONGRATS", "20/20"]):
            if client.w_loop:
                await asyncio.sleep(5)
                await client.send_message(client.w_target_chat, client.w_loop_cmd)
