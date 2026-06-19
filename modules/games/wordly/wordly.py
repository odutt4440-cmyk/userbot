import time
import requests
import re
import asyncio
import os
from collections import Counter
from telethon import events, functions, types

# =========================================
# LOAD DICTIONARY (6-12 letters only)
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
            if 6 <= len(w) <= 12 and w.isalpha():
                valid.append(w)
    return valid

WORDS_DB = load_words()

def register(client):
    # State tracking per BOT (to play multiple bots in same GC)
    # Format: {bot_id: {'letters': str, 'used': set(), 'can_repeat': bool}}
    client.w_game_states = {}
    client.w_enabled = True
    client.w_loop = False
    client.w_delay = 0.5

    # --- ADVANCED SOLVER ---
    def solve(bot_id):
        state = client.w_game_states.get(bot_id)
        if not state or not state['letters']: return None
        
        allowed_set = set(state['letters'].lower())
        board_counts = Counter(state['letters'].lower())
        
        for word in WORDS_DB:
            if word in state['used']: continue
            
            word_set = set(word)
            if word_set.issubset(allowed_set):
                if not state['can_repeat']:
                    word_counts = Counter(word)
                    if all(word_counts[c] <= board_counts[c] for c in word_counts):
                        state['used'].add(word)
                        return word.capitalize()
                else:
                    state['used'].add(word)
                    return word.capitalize()
        return None

    # --- ROBUST LETTER EXTRACTOR ---
    def extract_letters(text):
        text_up = text.upper()
        if "," in text: # WordgamezBot
            match = re.search(r"(?:^|\n)\s*([A-Z],\s*)+[A-Z]\s*(?:\n|$)", text_up)
            if match: return "".join(re.findall(r"[A-Z]", match.group(0)))
        # WordlyGamingBot
        match = re.search(r"[\(\u2934]\s*([A-Z\s]+)\s*[\)\u2935]", text_up)
        if match: return "".join(re.findall(r"[A-Z]", match.group(1)))
        return "".join(re.findall(r"\b[A-Z]\b", text_up))

    # =========================================
    # CONTROL PANEL (.won, .woff, .wloop, .wdelay)
    # =========================================
    @client.on(events.NewMessage(chats='me'))
    async def control_panel(event):
        text = event.raw_text.lower().strip()
        if text == ".won":
            client.w_enabled = True
            await event.edit("✅ **Wordly Master: ONLINE**")
        elif text == ".woff":
            client.w_enabled = False
            await event.edit("❌ **Wordly Master: OFFLINE**")
        elif text.startswith(".wloop"):
            client.w_loop = "on" in text
            await event.edit(f"{'🔄' if client.w_loop else '❌'} **Auto-Loop:** {'ON' if client.w_loop else 'OFF'}")
        elif text.startswith(".wdelay"):
            try:
                client.w_delay = float(text.split()[1])
                await event.edit(f"⚡ **Delay:** {client.w_delay}s")
            except: pass

    # =========================================
    # GAME ENGINE
    # =========================================
    @client.on(events.NewMessage)
    async def game_handler(event):
        if not client.w_enabled or event.out: return
        
        msg = event.raw_text
        msg_up = msg.upper()
        bot_id = event.sender_id

        # 1. Catch SYNC/REJECTION (Wait, someone found it? Or invalid word?)
        # Matches: "found 'Word'", "Accept! ... — WORD", "WORD is already found", "WORD is not a valid"
        rejection_match = re.search(r'(?i)FOUND ["«](\w+)["»]|—\s*(\w+)|(\w+)\s*IS ALREADY FOUND|«(\w+)»\s*IS NOT A VALID', msg)
        if rejection_match:
            # Find which group captured the word
            found_word = next(w for w in rejection_match.groups() if w).lower()
            if bot_id in client.w_game_states:
                client.w_game_states[bot_id]['used'].add(found_word)
                # 🔥 CRITICAL FIX: Agar Userbot ka bheja word reject hua, turant naya try karo
                if "ALREADY FOUND" in msg_up or "NOT A VALID" in msg_up:
                    word = solve(bot_id)
                    if word:
                        async with client.action(event.chat_id, 'typing'):
                            await asyncio.sleep(client.w_delay)
                            await event.reply(word)
            return

        # 2. Board Detection & Progress
        progress_match = re.search(r"(\d+)\s*/\s*(\d+)", msg)
        is_board = "LETTERS BOARD" in msg_up or "MODE IS LIVE" in msg_up or progress_match

        if is_board:
            letters = extract_letters(msg)
            if not letters: return

            # Initialize or Reset Bot State
            if bot_id not in client.w_game_states or "0/" in msg:
                client.w_game_states[bot_id] = {
                    'letters': letters,
                    'used': set(),
                    'can_repeat': "LETTERS CAN BE REPEATED" in msg_up,
                    'goal': int(progress_match.group(2)) if progress_match else 20
                }
            else:
                client.w_game_states[bot_id]['letters'] = letters

            # Solve if not finished
            if progress_match:
                curr, goal = int(progress_match.group(1)), int(progress_match.group(2))
                if curr >= goal:
                    if client.w_loop:
                        await asyncio.sleep(5)
                        await client.send_message(event.chat_id, "/new")
                    return

            word = solve(bot_id)
            if word:
                async with client.action(event.chat_id, 'typing'):
                    await asyncio.sleep(client.w_delay)
                    await event.reply(word)

        # 3. Game Over Loop
        elif any(x in msg_up for x in ["GAME OVER", "CONGRATS"]):
            if client.w_loop:
                await asyncio.sleep(5)
                await client.send_message(event.chat_id, "/new")
