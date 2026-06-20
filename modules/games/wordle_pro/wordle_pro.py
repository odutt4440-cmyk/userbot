import json
import random
import asyncio
import unicodedata
import os
import re
from collections import Counter
from telethon import events, functions, types

# =========================================
# LOAD WORDLISTS (Multi-Length Support)
# =========================================
FOLDER = os.path.dirname(__file__)
WORDS_DIR = os.path.join(FOLDER, "words")

def load_json(filename):
    path = os.path.join(WORDS_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Support both list and dict formats
            return data["words"] if isinstance(data, dict) else data
    return []

# Starters for different lengths
STARTERS = {
    3: "The", 4: "Care", 5: "Slate", 6: "Retain", 7: "Staring"
}

# Mapping length to filenames
FILE_MAP = {
    3: "three", 4: "four", 5: "five", 6: "six", 7: "seven"
}

def register(client):
    # --- Per-User State ---
    client.wd_enabled = True
    client.wd_chat = None
    client.wd_delay_min = 1.5 
    client.wd_delay_max = 3.0 
    client.wd_mode = 5
    client.wd_loop = False
    client.wd_loop_cmd = "/new" 
    
    client.wd_used = set()
    client.wd_green = {}
    client.wd_yellow = {}
    client.wd_black = set()
    client.wd_last_guess = None

    # --- HELPERS ---
    def reset_state():
        client.wd_green = {}
        client.wd_yellow = {}
        client.wd_black = set()
        client.wd_used = set()
        client.wd_last_guess = None

    def clean_word(word):
        return "".join(c.lower() for c in unicodedata.normalize("NFKD", word) if c.isalpha())

    def parse_feedback(text):
        """Extracts the last word and its emoji feedback row"""
        lines = text.splitlines()
        feedback_row = None
        word_row = None
        
        for i, line in enumerate(lines):
            if any(emoji in line for emoji in ["🟩", "🟨", "🟥"]):
                feedback_row = line.strip().split()
                if i > 0:
                    word_row = clean_word(lines[i-1].replace(" ", ""))
                break
        
        if not word_row or not feedback_row or len(word_row) != len(feedback_row):
            return None
        return word_row, feedback_row

    def apply_constraints(guess, feedback):
        confirmed = Counter()
        # Pass 1: Greens
        for i, state in enumerate(feedback):
            char = guess[i]
            if state == "🟩":
                client.wd_green[i] = char
                confirmed[char] += 1
        # Pass 2: Yellows
        for i, state in enumerate(feedback):
            char = guess[i]
            if state == "🟨":
                if char not in client.wd_yellow: client.wd_yellow[char] = set()
                client.wd_yellow[char].add(i)
                confirmed[char] += 1
        # Pass 3: Reds
        for i, state in enumerate(feedback):
            char = guess[i]
            if state == "🟥":
                if confirmed[char] == 0: client.wd_black.add(char)

    def is_valid(word):
        word = word.lower()
        if len(word) != client.wd_mode: return False
        for pos, char in client.wd_green.items():
            if word[pos] != char: return False
        for char, bad_pos in client.wd_yellow.items():
            if char not in word: return False
            for p in bad_pos:
                if word[p] == char: return False
        for char in client.wd_black:
            if char in word and char not in client.wd_yellow and char not in client.wd_green.values():
                return False
        return True

    def get_next_guess():
        suffix = FILE_MAP.get(client.wd_mode, "five")
        common = load_json(f"common-{suffix}.json")
        all_words = load_json(f"all-{suffix}.json")
        
        v_common = [w for w in common if is_valid(w) and w.lower() not in client.wd_used]
        v_all = [w for w in all_words if is_valid(w) and w.lower() not in client.wd_used]
        
        if not client.wd_used: return STARTERS.get(client.wd_mode, "Slate")
        
        pool = v_common if v_common else v_all
        if not pool: return None
        
        # Sort by letter frequency (Smart Guessing)
        freq = Counter("".join(pool))
        pool.sort(key=lambda w: sum(freq[c] for c in set(w.lower())), reverse=True)
        return pool[0].capitalize()

    # =========================================
    # COMMANDS (Saved Messages Only)
    # =========================================
    @client.on(events.NewMessage(chats='me', pattern=r"(?i)^\.wd (on|off)$"))
    async def toggle_wd(event):
        client.wd_enabled = event.pattern_match.group(1).lower() == "on"
        await event.edit(f"{'✅' if client.wd_enabled else '❌'} **Wordle Pro Solver {'Enabled' if client.wd_enabled else 'Disabled'}**")

    @client.on(events.NewMessage(chats='me', pattern=r"(?i)^\.wd loop (on|off)$"))
    async def toggle_loop(event):
        client.wd_loop = event.pattern_match.group(1).lower() == "on"
        await event.edit(f"{'♻️' if client.wd_loop else '❌'} **Wordle Auto-Loop {'Enabled' if client.wd_loop else 'Disabled'}**")

    @client.on(events.NewMessage(chats='me', pattern=r"(?i)^\.wd delay (\d+\.?\d*) (\d+\.?\d*)$"))
    async def set_delay(event):
        client.wd_delay_min = float(event.pattern_match.group(1))
        client.wd_delay_max = float(event.pattern_match.group(2))
        await event.edit(f"⚡ **Delay set to:** {client.wd_delay_min}s - {client.wd_delay_max}s")

    # =========================================
    # MAIN ENGINE
    # =========================================
    @client.on(events.NewMessage(outgoing=True))
    async def detect_new(event):
        if not client.wd_enabled: return
        text = event.raw_text.lower().strip()
        if text.startswith("/new"):
            client.wd_chat = event.chat_id
            client.wd_loop_cmd = text
            # Auto detect mode from command (e.g., /new7 -> mode 7)
            digit = re.findall(r"\d", text)
            client.wd_mode = int(digit[0]) if digit else 5
            reset_state()
            await client.send_message("me", f"🎯 **Wordle Pro Locked:** `{event.chat_id}`\nMode: `{client.wd_mode}`\nCommand: `{client.wd_loop_cmd}`")

    @client.on(events.NewMessage)
    async def game_handler(event):
        if not client.wd_enabled or event.chat_id != client.wd_chat: return
        
        sender = await event.get_sender()
        if not sender or (getattr(sender, 'username', '') or '').lower() != "wordlegameprobot":
            return
            
        text = event.raw_text
        
        # --- GAME END / LOOP ---
        if any(x in text for x in ["Congratulations", "Game Over", "Correct word was"]):
            reset_state()
            if client.wd_loop:
                await asyncio.sleep(random.uniform(5, 8))
                await client.send_message(client.wd_chat, client.wd_loop_cmd)
            return

        # --- GAME START / FEEDBACK ---
        if "Guess the" in text or "🟩" in text:
            res = parse_feedback(text)
            if res:
                guess, feedback = res
                if guess == client.wd_last_guess: return
                client.wd_last_guess = guess
                apply_constraints(guess, feedback)
            
            next_w = get_next_guess()
            if next_w:
                client.wd_used.add(next_w.lower())
                async with client.action(event.chat_id, "typing"):
                    await asyncio.sleep(random.uniform(client.wd_delay_min, client.wd_delay_max))
                    await client.send_message(event.chat_id, next_w)
