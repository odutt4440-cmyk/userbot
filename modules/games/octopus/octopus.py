import re
import json
import random
import asyncio
import os
import time
from collections import Counter
from telethon import events
from telethon.tl.types import User
from wordfreq import top_n_list, zipf_frequency

# =========================================================
# SHARED ENGINE
# =========================================================
FOLDER = os.path.dirname(__file__)
CUSTOM_DICT_FILE = os.path.join(FOLDER, "octopus_words.json")

print("🐙 Octopus Engine: Initializing Emoji-Proof Core...")
english_words = top_n_list("en", 120000)
all_words = set()
for w in english_words:
    w = w.lower().strip()
    if (w.isalpha() and len(w) >= 3 and zipf_frequency(w, "en") > 2):
        all_words.add(w)

learned_words = {}
if os.path.exists(CUSTOM_DICT_FILE):
    try:
        with open(CUSTOM_DICT_FILE, "r") as f:
            learned_words = json.load(f)
            for w in learned_words:
                if w.isalpha(): all_words.add(w.lower().strip())
    except: pass

# =========================================================
# THE MODULE REGISTER
# =========================================================
def register(client):
    client.o_chat = None        
    client.o_running = False     
    client.o_answers = []
    client.o_guess_idx = 0
    client.o_waiting = False    
    client.o_last_msg_id = 0
    
    client.o_min_delay = 3.1 
    client.o_max_delay = 3.6
    client.o_retry_int = 4.5
    client.o_max_guesses = 5

    def save_learned_word(word):
        word = word.lower().strip()
        if not word.isalpha() or len(word) <= 1: return
        learned_words[word] = learned_words.get(word, 0) + 1
        all_words.add(word)
        try:
            with open(CUSTOM_DICT_FILE, "w") as f:
                json.dump(learned_words, f, indent=2)
        except: pass

    def solve_puzzle(pattern_line, letters_line):
        pattern = re.sub(r"[^A-Za-z_]", "", pattern_line).lower()
        letters = re.findall(r"[A-Za-z]", letters_line)
        usable = [x.lower() for x in letters]
        for ch in pattern:
            if ch != "_": usable.append(ch)
        
        usable_counter = Counter(usable)
        results = []
        for word in all_words:
            if len(word) != len(pattern): continue
            if not all(p == "_" or p == w for p, w in zip(pattern, word)): continue
            wc = Counter(word)
            if any(wc[ch] > usable_counter[ch] for ch in wc): continue
            
            score = learned_words.get(word, 0) * 10000 + int(zipf_frequency(word, "en") * 100)
            for c in "etaoinshrdlu": score += word.count(c)
            score += 20 - len(word)
            results.append((word, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return [x[0] for x in results[:client.o_max_guesses]]

    async def retry_loop(event, msg_id):
        client.o_waiting = True
        while client.o_waiting and client.o_running:
            await asyncio.sleep(client.o_retry_int)
            if not client.o_waiting or client.o_last_msg_id != msg_id: break
            if client.o_guess_idx < len(client.o_answers):
                answer = client.o_answers[client.o_guess_idx]
                client.o_guess_idx += 1
                await client.send_message(client.o_chat, answer)
            else:
                client.o_waiting = False
                if event.buttons:
                    for row in event.buttons:
                        for btn in row:
                            if any(x in btn.text.lower() for x in ["skip", "♻", "pass"]):
                                try: await event.click(text=btn.text); return
                                except: pass
                break

    @client.on(events.NewMessage(chats='me', outgoing=True))
    async def control_panel(event):
        text = event.raw_text.lower().strip()
        if text == ".octo on":
            client.o_running = True
            client.o_chat = None
            await event.edit("🚀 **Octopus Engine: ARMED**\nEmoji-Proof mode active.")
        elif text == ".octo off":
            client.o_running = False
            await event.edit("🛑 **Octopus Engine: DISARMED**")

    @client.on(events.NewMessage(outgoing=True))
    async def detect_target(event):
        if client.o_running and "/game" in event.raw_text:
            client.o_chat = event.chat_id
            await client.send_message("me", f"🎯 **Target Locked:** `{event.chat_id}`")

    @client.on(events.NewMessage)
    @client.on(events.MessageEdited) 
    async def main_engine(event):
        if not client.o_running or client.o_chat is None: return
        if event.chat_id != client.o_chat: return
        
        sender = await event.get_sender()
        if not sender: return
        s_user = (getattr(sender, "username", "") or "").lower()
        
        if s_user != "octopusen_bot":
            if not event.out and len(event.raw_text or "") > 1: client.o_waiting = False
            return

        text = event.raw_text or ""
        low = text.lower()

        if any(x in low for x in ["got it right", "correct", "round:", "passed"]):
            client.o_waiting = False

        # --- EMOJI-PROOF DETECTION LOGIC ---
        pattern_line = None
        letters_line = None

        lines = text.splitlines()
        for line in lines:
            # 1. Detect Board (Line with underscores and letters)
            clean_l = re.sub(r"[^A-Za-z_ ]", "", line).strip()
            if "_" in clean_l and len(clean_l.replace(" ", "")) > 1:
                pattern_line = line
            
            # 2. Detect Letters Pool (Line with 'letter:' and characters)
            if "letter" in line.lower() and ":" in line:
                letters_line = line.split(":", 1)[1]

        if pattern_line:
            # Sync Check
            if event.id == client.o_last_msg_id and "Round:" not in text: return
            client.o_last_msg_id = event.id
            
            # If letters not found by word, fallback to regex search
            if not letters_line:
                letters_line = " ".join(re.findall(r"\b[A-Za-z]\b", text))

            ans = solve_puzzle(pattern_line, letters_line)
            client.o_answers = ans
            client.o_guess_idx = 0

            if ans:
                word = client.o_answers[client.o_guess_idx]
                client.o_guess_idx += 1
                async with client.action(client.o_chat, 'typing'):
                    await asyncio.sleep(random.uniform(client.o_min_delay, client.o_max_delay))
                await client.send_message(client.o_chat, word)
                asyncio.create_task(retry_loop(event, event.id))
            else:
                if event.buttons:
                    try: await event.click(0) # Emergency click first button (skip)
                    except: pass
            return

        if "game ended" in low: client.o_chat = None
