import re
import json
import random
import asyncio
import os
from collections import Counter
from telethon import events
from telethon.tl.types import User
from wordfreq import top_n_list, zipf_frequency

# =========================================================
# SHARED DICTIONARY (Loaded once to save server RAM)
# =========================================================
FOLDER = os.path.dirname(__file__)
CUSTOM_DICT_FILE = os.path.join(FOLDER, "octopus_words.json")

print("🐙 Octopus: Loading Shared Dictionary...")
english_words = top_n_list("en", 120000)
all_words = set()
for w in english_words:
    w = w.lower().strip()
    if w.isalpha() and len(w) >= 3 and zipf_frequency(w, "en") > 2:
        all_words.add(w)

# Load learned words into shared memory
learned_words = {}
if os.path.exists(CUSTOM_DICT_FILE):
    try:
        with open(CUSTOM_DICT_FILE, "r") as f:
            learned_words = json.load(f)
            for w in learned_words:
                if w.isalpha(): all_words.add(w.lower().strip())
    except: pass

print(f"🐙 Octopus: Shared Memory Ready ({len(all_words)} words)")

# =========================================================
# THE MODULE REGISTER
# =========================================================
def register(client):
    # --- Per-User State (Isolated) ---
    client.o_chat = None
    client.o_running = False
    client.o_answers = []
    client.o_guess_idx = 0
    client.o_waiting = False
    client.o_delay_min = 2.6
    client.o_delay_max = 3.2
    client.o_retry_int = 4.5

    # --- HELPERS (Logic Unchanged) ---
    def save_learned_word(word):
        word = word.lower().strip()
        if not word.isalpha() or len(word) <= 1: return
        if word not in learned_words: learned_words[word] = 1
        else: learned_words[word] += 1
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
            
            # Scoring Logic (Exactly as yours)
            score = learned_words.get(word, 0) * 10000
            score += int(zipf_frequency(word, "en") * 100)
            score += sum(word.count(c) for c in "etaoinshrdlu")
            score += 20 - len(word)
            results.append((word, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return [x[0] for x in results[:5]]

    async def click_button(event, keywords):
        if not event.buttons: return False
        for row in event.buttons:
            for btn in row:
                if any(k.lower() in btn.text.lower() for k in keywords):
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                    try: await event.click(text=btn.text); return True
                    except: pass
        return False

    async def skip_round(event):
        if not event.buttons: return
        for row in event.buttons:
            for btn in row:
                if any(x in btn.text.lower() for x in ["skip", "♻", "pass"]):
                    await asyncio.sleep(random.uniform(client.o_delay_min, client.o_delay_max))
                    try: await event.click(text=btn.text); return
                    except: pass
        try: await event.click(0)
        except: pass

    async def retry_guesses(event):
        client.o_waiting = True
        while client.o_waiting:
            await asyncio.sleep(client.o_retry_int)
            if not client.o_waiting: return
            if client.o_guess_idx < len(client.o_answers):
                answer = client.o_answers[client.o_guess_idx]
                client.o_guess_idx += 1
                async with client.action(client.o_chat, "typing"):
                    await asyncio.sleep(random.uniform(client.o_delay_min, client.o_delay_max))
                await client.send_message(client.o_chat, answer)
            else:
                await skip_round(event)
                client.o_waiting = False

    # =========================================================
    # HANDLERS
    # =========================================================
    @client.on(events.NewMessage(outgoing=True))
    async def octopus_commands(event):
        text = event.raw_text.strip()
        if text == "/game@OctopusEN_Bot":
            client.o_chat = event.chat_id
            client.o_running = True
            await client.send_message("me", f"🐙 **Octopus Target:** `{event.chat_id}`")
        
        elif text.startswith(".octo delay"):
            parts = text.split()
            if len(parts) == 3:
                client.o_delay_min, client.o_delay_max = float(parts[1]), float(parts[2])
                await event.edit(f"✅ **Octo Delay:** {client.o_delay_min}-{client.o_delay_max}")

    @client.on(events.NewMessage)
    async def octopus_engine(event):
        if not client.o_running or event.chat_id != client.o_chat: return
        sender = await event.get_sender()
        if not isinstance(sender, User) or sender.username != "OctopusEN_Bot": return

        text = event.raw_text
        low = text.lower()

        # Turn detection
        if any(x in low for x in ["round:", "point:", "letters:"]):
            client.o_waiting = False

        # Menu handling
        if "choose a game type" in low:
            await click_button(event, ["gap", "🔠"])
        elif "how many rounds" in low:
            await click_button(event, ["50"])
        elif "difficulty" in low:
            await click_button(event, ["hard", "💣"])

        # Puzzle solver
        pattern_match = re.search(r"([A-Za-z](?:\s+[A-Za-z_])+)", text)
        if pattern_match and "_" in pattern_match.group(1):
            pattern = pattern_match.group(1).strip()
            letters_match = re.search(r"(?:letters:|letter:)\s*(.+)", text, re.I)
            letters = letters_match.group(1) if letters_match else ""
            
            ans = solve_puzzle(pattern, letters)
            client.o_answers = ans
            client.o_guess_idx = 0
            
            if ans:
                word = client.o_answers[client.o_guess_idx]
                client.o_guess_idx += 1
                async with client.action(client.o_chat, "typing"):
                    await asyncio.sleep(random.uniform(client.o_delay_min, client.o_delay_max))
                await client.send_message(client.o_chat, word)
                asyncio.create_task(retry_guesses(event))
            else:
                await skip_round(event)

        # Learning system
        if any(x in low for x in ["correct answer", "passed the word", "got it right"]):
            m = re.search(r"(?:→|⟶)\s*([A-Za-z]+)", text)
            if m: save_learned_word(m.group(1))

        if "game ended" in low:
            client.o_running = False
