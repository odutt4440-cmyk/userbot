import time
import requests
import re
import asyncio
import os
from collections import Counter
from telethon import events, functions, types

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
            # 🔥 Updated to 6-12 letters for better scores
            if 6 <= len(w) <= 12 and w.isalpha():
                valid.append(w)
    return valid

WORDS_DB = load_words()

def register(client):
    # --- Per-User State ---
    client.w_target_chat = None
    client.w_enabled = True
    client.w_loop = False 
    client.w_loop_cmd = "/new" 
    client.w_delay = 0.5
    client.w_used_words = set()
    client.w_current_letters = None
    client.w_can_repeat = False

    # --- ACCURATE SOLVER ---
    def solve(letters):
        if not letters: return None
        allowed_set = set(letters.lower())
        board_counts = Counter(letters.lower())
        
        candidates = []
        for word in WORDS_DB:
            if word in client.w_used_words: continue
            word_set = set(word)
            if word_set.issubset(allowed_set):
                if not client.w_can_repeat:
                    word_counts = Counter(word)
                    if all(word_counts[c] <= board_counts[c] for c in word_counts):
                        candidates.append(word)
                else:
                    candidates.append(word)
        
        if not candidates: return None
        candidates.sort(key=len, reverse=True)
        best = candidates[0]
        client.w_used_words.add(best)
        return best.capitalize()

    # --- ROBUST LETTER EXTRACTOR ---
    def extract_letters(text):
        text_up = text.upper()
        if "," in text:
            match = re.search(r"(?:^|\n)\s*([A-Z],\s*)+[A-Z]\s*(?:\n|$)", text_up)
            if match: return "".join(re.findall(r"[A-Z]", match.group(0)))
        match = re.search(r"[\(\u2934]\s*([A-Z\s]+)\s*[\)\u2935]", text_up)
        if match: return "".join(re.findall(r"[A-Z]", match.group(1)))
        all_caps = re.findall(r"\b[A-Z]\b", text_up)
        return "".join(all_caps) if len(all_caps) >= 5 else None

    # =========================================
    # CONTROL PANEL
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
                await event.edit(f"⚡ **Delay:** {client.w_delay}s")
            except: pass
        elif text == ".wstatus":
            await event.edit(f"📊 **Wordly Stats**\nEnabled: `{client.w_enabled}`\nLoop: `{client.w_loop}`\nChat: `{client.w_target_chat}`")

    # =========================================
    # TARGET DETECTION & SOLVING
    # =========================================
    @client.on(events.NewMessage(outgoing=True))
    async def detect_target(event):
        if event.raw_text.lower().startswith("/new"):
            client.w_target_chat = event.chat_id
            client.w_loop_cmd = event.raw_text
            client.w_used_words.clear()
            await client.send_message("me", f"🎯 **Wordly Locked:** `{event.chat_id}`\nMode: `{client.w_loop_cmd}`")

    @client.on(events.NewMessage)
    async def game_handler(event):
        if not client.w_enabled or not client.w_target_chat: return
        if event.chat_id != client.w_target_chat: return

        msg = event.raw_text
        msg_up = msg.upper()

        # 🔥 SYNC: Catch words found by OTHERS to avoid repeats
        # Matches: found "Word" OR Accepted! ... — WORD OR Word is already found
        found_sync = re.search(r'FOUND "(\w+)"|—\s*(\w+)|(\w+)\s*IS ALREADY FOUND', msg_up)
        if found_sync:
            found_word = next(w for w in found_sync.groups() if w).lower()
            client.w_used_words.add(found_word)

        if event.out: return 

        progress_match = re.search(r"(\d+)\s*/\s*(\d+)", msg)
        
        if progress_match or "LETTERS BOARD" in msg_up or "MODE IS LIVE" in msg_up:
            current_found = int(progress_match.group(1)) if progress_match else 0
            total_goal = int(progress_match.group(2)) if progress_match else 20
            
            if progress_match and current_found >= total_goal:
                client.w_current_letters = None
                if client.w_loop:
                    await asyncio.sleep(5)
                    await client.send_message(client.w_target_chat, client.w_loop_cmd)
                return

            async with client.action(event.chat_id, 'typing'):
                client.w_can_repeat = "LETTERS CAN BE REPEATED" in msg_up
                letters = extract_letters(msg)
                
                if letters:
                    if "TOTAL: 0/" in msg_up or "0/20" in msg_up or "0/30" in msg_up:
                        client.w_used_words.clear()
                    
                    client.w_current_letters = letters
                    word = solve(client.w_current_letters)
                    if word:
                        if client.w_delay > 0: await asyncio.sleep(client.w_delay)
                        await client.send_message(event.chat_id, word)

        elif any(x in msg_up for x in ["GAME OVER", "CONGRATS"]):
            client.w_current_letters = None
            if client.w_loop:
                await asyncio.sleep(5)
                await client.send_message(client.w_target_chat, client.w_loop_cmd)
