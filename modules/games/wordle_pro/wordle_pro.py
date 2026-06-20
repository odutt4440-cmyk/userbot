import json
import random
import asyncio
import unicodedata
import os
import re
from collections import Counter
from telethon import events, functions, types, errors

# =========================================
# LOAD WORDLISTS
# =========================================
FOLDER = os.path.dirname(__file__)
WORDS_DIR = os.path.join(FOLDER, "words")

def load_json(filename):
    path = os.path.join(WORDS_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data["words"] if isinstance(data, dict) else data
    return []

STARTERS = {
    3: "The", 4: "Care", 5: "Slate", 6: "Retain", 7: "Staring"
}

FILE_MAP = {
    3: "three", 4: "four", 5: "five", 6: "six", 7: "seven"
}

def register(client):
    client.wd_enabled = True
    client.wd_chat = None
    client.wd_delay_min = 1.0 
    client.wd_delay_max = 2.0 
    client.wd_mode = 5
    client.wd_loop = False
    client.wd_loop_cmd = "/new" 
    
    client.wd_used = set()
    client.wd_green = {}  # pos: char
    client.wd_yellow = {} # char: {pos}
    client.wd_black = set()
    client.wd_last_guess = None

    # --- 🛠️ HELPERS ---
    async def safe_edit(event, text):
        try:
            await event.edit(text)
        except:
            pass

    def reset_state():
        client.wd_green = {}
        client.wd_yellow = {}
        client.wd_black = set()
        client.wd_used = set()
        client.wd_last_guess = None

    def parse_feedback(text):
        """Specifically tuned for @wordlegameprobot (🟥🟥🟥 TEN)"""
        lines = text.splitlines()
        for line in reversed(lines):
            # Regex to find emojis (with or without spaces) and the word
            # Matches: 🟥🟥🟥 TEN or 🟥 🟩 🟥 THE
            match = re.search(r"([🟩🟨🟥⬜⬛\s]+)\s+([A-Z]{3,7})", line.upper())
            if match:
                raw_emojis = match.group(1).replace(" ", "") # Remove spaces between emojis
                emojis = list(raw_emojis) # Convert string to list of emojis
                guess = match.group(2).lower()
                if len(emojis) == len(guess):
                    return guess, emojis
        return None

    def apply_constraints(guess, feedback):
        temp_green_chars = set()
        for i, emoji in enumerate(feedback):
            char = guess[i]
            if emoji == "🟩":
                client.wd_green[i] = char
                temp_green_chars.add(char)
        
        for i, emoji in enumerate(feedback):
            char = guess[i]
            if emoji == "🟨":
                if char not in client.wd_yellow: client.wd_yellow[char] = set()
                client.wd_yellow[char].add(i)
            elif emoji in ["🟥", "⬜", "⬛"]:
                if char not in temp_green_chars and char not in client.wd_yellow:
                    client.wd_black.add(char)

    def is_valid(word):
        word = word.lower()
        if len(word) != client.wd_mode: return False
        for pos, char in client.wd_green.items():
            if word[pos] != char: return False
        for char in client.wd_black:
            if char in word: return False
        for char, bad_positions in client.wd_yellow.items():
            if char not in word: return False
            for pos in bad_positions:
                if word[pos] == char: return False
        return True

    def get_next_guess():
        suffix = FILE_MAP.get(client.wd_mode, "five")
        common = load_json(f"common-{suffix}.json")
        all_words = load_json(f"all-{suffix}.json")
        
        if not client.wd_used:
            return STARTERS.get(client.wd_mode, 3)

        candidates = [w for w in common if is_valid(w) and w.lower() not in client.wd_used]
        if not candidates:
            candidates = [w for w in all_words if is_valid(w) and w.lower() not in client.wd_used]
        
        if not candidates: return None

        # Smart Entropy Sorting
        freq = Counter("".join(candidates))
        candidates.sort(key=lambda w: sum(freq[c] for c in set(w.lower())), reverse=True)
        return candidates[0].capitalize()

    # --- COMMANDS ---
    @client.on(events.NewMessage(chats='me', pattern=r"(?i)^\.wd (on|off)$"))
    async def toggle_wd(event):
        client.wd_enabled = event.pattern_match.group(1).lower() == "on"
        await safe_edit(event, f"🧩 **Wordle Pro: {'ON' if client.wd_enabled else 'OFF'}**")

    @client.on(events.NewMessage(chats='me', pattern=r"(?i)^\.wd loop (on|off)$"))
    async def toggle_loop(event):
        client.wd_loop = event.pattern_match.group(1).lower() == "on"
        await safe_edit(event, f"♻️ **Loop Mode: {'ON' if client.wd_loop else 'OFF'}**")

    # --- ENGINE ---
    @client.on(events.NewMessage(outgoing=True))
    async def detect_new(event):
        if not client.wd_enabled: return
        text = event.raw_text.lower().strip()
        if text.startswith("/new"):
            client.wd_chat = event.chat_id
            client.wd_loop_cmd = text
            digit = re.findall(r"\d", text)
            client.wd_mode = int(digit[0]) if digit else 5
            reset_state()
            await client.send_message("me", f"🎯 **Wordle Pro Target:** `{event.chat_id}` (Mode: {client.wd_mode})")

    @client.on(events.NewMessage)
    async def game_handler(event):
        if not client.wd_enabled or event.chat_id != client.wd_chat: return
        
        sender = await event.get_sender()
        if not sender or (getattr(sender, 'username', '') or '').lower() != "wordlegameprobot":
            return
            
        text = event.raw_text
        
        # 1. End Detection
        if any(x in text for x in ["Congratulations", "Game Over", "Correct word was"]):
            reset_state()
            if client.wd_loop:
                await asyncio.sleep(7)
                await client.send_message(client.wd_chat, client.wd_loop_cmd)
            return

        # 2. Solver Trigger
        # Emojis detection with improved flexible logic
        if any(emoji in text for emoji in ["🟩", "🟨", "🟥", "⬜", "⬛"]) or "Start guessing" in text:
            feedback = parse_feedback(text)
            if feedback:
                guess, emojis = feedback
                if guess == client.wd_last_guess: return
                client.wd_last_guess = guess
                apply_constraints(guess, emojis)
            
            next_w = get_next_guess()
            if next_w:
                client.wd_used.add(next_w.lower())
                async with client.action(event.chat_id, "typing"):
                    await asyncio.sleep(random.uniform(client.wd_delay_min, client.wd_delay_max))
                    await client.send_message(event.chat_id, next_w)
