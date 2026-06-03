# =========================================================
# OCTOPUS USERBOT - FINAL STABLE RETRY VERSION
# =========================================================
# pip install telethon wordfreq nltk
# =========================================================

import re
import json
import random
import asyncio

from collections import Counter

from telethon import TelegramClient, events
from telethon.tl.types import User

from wordfreq import (
    top_n_list,
    zipf_frequency
)



BOT_USERNAME = "OctopusEN_Bot"

ROUNDS = "50"

DIFFICULTY_KEYWORDS = [
    "hard",
    "💣"
]

CUSTOM_DICT_FILE = "octopus_words.json"

AUTO_SKIP = True

# =========================================================
# ANSWER SPEED
# =========================================================

MIN_DELAY = 2.6
MAX_DELAY = 3.2

# retry system
MAX_GUESSES = 5

RETRY_INTERVAL = 4.5

# =========================================================
# THE MODULE REGISTER (SaaS Isolation)
# =========================================================
def register(client):
    # --- State Management (Isolating per user) ---
    client.o_chat = None
    client.o_running = False
    client.o_answers = []
    client.o_guess_idx = 0
    client.o_waiting = False
    client.o_last_msg_id = 0
    client.o_start_msg_id = 0
    client.o_my_name = None
    
    # Speed & Reliability Config
    client.o_min_delay = 3.1 # To avoid 'thinking' warning
    client.o_max_delay = 3.6
    client.o_retry_int = 4.2

# =========================================================
# LOAD LEARNED WORDS
# =========================================================

try:

    with open(CUSTOM_DICT_FILE, "r") as f:

        learned_words = json.load(f)

except:

    learned_words = {}

# =========================================================
# LOAD ENGLISH WORDS
# =========================================================

print("Loading dictionary...")

english_words = top_n_list(
    "en",
    120000
)

all_words = set()

for w in english_words:

    w = w.lower().strip()

    if (
        w.isalpha()
        and len(w) >= 3
        and zipf_frequency(w, "en") > 2
    ):

        all_words.add(w)

# learned words add
for w in learned_words:

    w = w.lower().strip()

    if w.isalpha():

        all_words.add(w)

print(f"\nLoaded {len(all_words)} words\n")

# =========================================================
# SAVE WORD
# =========================================================

def save_word(word):

    word = word.lower().strip()

    if not word.isalpha():
        return

    if len(word) <= 1:
        return

    if word not in learned_words:

        learned_words[word] = 1

    else:

        learned_words[word] += 1

    all_words.add(word)

    with open(CUSTOM_DICT_FILE, "w") as f:

        json.dump(
            learned_words,
            f,
            indent=2
        )

# =========================================================
# SOLVER
# =========================================================

def solve_puzzle(pattern_line, letters_line):

    pattern = re.sub(
        r"[^A-Za-z_]",
        "",
        pattern_line
    ).lower()

    letters = re.findall(
        r"[A-Za-z]",
        letters_line
    )

    letters = [
        x.lower()
        for x in letters
    ]

    usable = letters.copy()

    for ch in pattern:

        if ch != "_":

            usable.append(ch)

    usable_counter = Counter(usable)

    results = []

    for word in all_words:

        word = word.lower()

        # same length
        if len(word) != len(pattern):
            continue

        # fixed chars check
        ok = True

        for p, w in zip(pattern, word):

            if p != "_" and p != w:

                ok = False
                break

        if not ok:
            continue

        # full letter usage check
        wc = Counter(word)

        valid = True

        for ch in wc:

            if wc[ch] > usable_counter[ch]:

                valid = False
                break

        if not valid:
            continue

        # =========================================
        # SCORING
        # =========================================

        score = 0

        # learned words huge priority
        if word in learned_words:

            score += (
                learned_words[word]
                * 10000
            )

        # english frequency
        score += int(
            zipf_frequency(
                word,
                "en"
            ) * 100
        )

        # common letters
        common = "etaoinshrdlu"

        for c in common:

            score += word.count(c)

        # length preference
        score += 20 - len(word)

        results.append(
            (word, score)
        )

    results.sort(
        key=lambda x: x[1],
        reverse=True
    )

    if results:

        print(
            f"\nTop Guesses => {results[:10]}\n"
        )

        return [x[0] for x in results[:MAX_GUESSES]]

    return []

# =========================================================
# BUTTON CLICK
# =========================================================

async def click_turbo(event, target_text, avoid_text=None):
        """Instantly finds and clicks setup buttons."""
        if not event.buttons: return False
        for row in event.buttons:
            for btn in row:
                txt = btn.text.lower()
                if target_text.lower() in txt:
                    if avoid_text and avoid_text.lower() in txt: continue
                    try:
                        await event.click() # Snap click
                        return True
                    except: pass
        return False

# =========================================================
# SEND ANSWER
# =========================================================

async def send_answer(answer):

    print(f"Typing => {answer}")

    try:

        async with client.action(
            selected_chat,
            "typing"
        ):

            await asyncio.sleep(
                random.uniform(
                    MIN_DELAY,
                    MAX_DELAY
                )
            )

        print(f"Sending => {answer}")

        await client.send_message(
            selected_chat,
            answer
        )

        print("Answer sent")

    except Exception as e:

        print(
            "Send failed:",
            e
        )

# =========================================================
# SKIP ROUND
# =========================================================

async def skip_round(event):

    if not AUTO_SKIP:
        return

    clicked = False

    if event.buttons:

        for row in event.buttons:

            for btn in row:

                try:

                    txt = btn.text.lower()

                    print(
                        f"Skip Button => {btn.text}"
                    )

                    if (
                        "skip" in txt
                        or "♻" in txt
                        or "pass" in txt
                    ):

                        await asyncio.sleep(
                            random.uniform(
                                MIN_DELAY,
                                MAX_DELAY
                            )
                        )

                        await event.click(
                            text=btn.text
                        )

                        print(
                            f"Clicked Skip => {btn.text}"
                        )

                        clicked = True
                        return

                except Exception as e:

                    print(
                        "Skip Error:",
                        e
                    )

    if not clicked and event.buttons:

        try:

            await event.click(0)

            print(
                "Fallback button clicked"
            )

        except Exception as e:

            print(
                "Fallback failed:",
                e
            )

# =========================================================
# RETRY SYSTEM
# =========================================================

async def retry_loop(event, msg_id):
        client.o_waiting = True
        while client.o_waiting and client.o_running:
            await asyncio.sleep(client.o_retry_int)
            
            # 🔥 Fix: Agar round badal gaya (Message ID change), toh ye loop mar jayega
            if not client.o_waiting or client.o_last_msg_id != msg_id:
                break

            if client.o_guess_idx < len(client.o_answers):
                answer = client.o_answers[client.o_guess_idx]
                client.o_guess_idx += 1
                await client.send_message(client.o_chat, answer)
            else:
                # Guesses khatam hone ke baad hi skip maarega
                client.o_waiting = False
                await click_turbo(event, "skip")

# =========================================================
# DETECT GAME START
# =========================================================

@client.on(events.NewMessage(outgoing=True))
async def detect_game_start(event):

    global selected_chat
    global game_running

    text = event.raw_text.strip()

    if text == "/game@OctopusEN_Bot":

        selected_chat = event.chat_id
        game_running = True

        print("\n===================================")
        print(f"TARGET GROUP => {selected_chat}")
        print("===================================\n")

# =========================================================
# SAVED MESSAGE COMMANDS
# =========================================================

@client.on(events.NewMessage(outgoing=True))
async def saved_commands(event):

    global MIN_DELAY
    global MAX_DELAY
    global RETRY_INTERVAL

    if not event.is_private:
        return

    me = await client.get_me()

    if event.chat_id != me.id:
        return

    cmd = event.raw_text.lower().strip()

    # =====================================================
    # SET DELAY
    # =====================================================

    if cmd.startswith("setdelay"):

        try:

            parts = cmd.split()

            MIN_DELAY = float(parts[1])
            MAX_DELAY = float(parts[2])

            msg = (
                f"✅ Delay updated => "
                f"{MIN_DELAY}-{MAX_DELAY}"
            )

            print(f"\n{msg}\n")

            await event.reply(msg)

        except:

            await event.reply(
                "Usage: setdelay 1.0 1.5"
            )

        return

    # =====================================================
    # SET RETRY
    # =====================================================

    if cmd.startswith("setretry"):

        try:

            parts = cmd.split()

            RETRY_INTERVAL = float(parts[1])

            msg = (
                f"✅ Retry updated => "
                f"{RETRY_INTERVAL}"
            )

            print(f"\n{msg}\n")

            await event.reply(msg)

        except:

            await event.reply(
                "Usage: setretry 3"
            )

        return

# =========================================================
# MAIN HANDLER
# =========================================================

@client.on(events.NewMessage)
async def handler(event):

    global selected_chat
    global game_running
    global current_answers
    global guess_index
    global waiting_next_turn

    if not game_running:
        return

    if event.chat_id != selected_chat:
        return

    sender = await event.get_sender()

    if not isinstance(sender, User):
        return

    if sender.username != BOT_USERNAME:
        return

    text = event.raw_text
    lower = text.lower()

    print("\n====================")
    print(text)
    print("====================\n")

    # next turn detected
    if (
        "round:" in lower
        or "point:" in lower
        or "letters:" in lower
    ):

        waiting_next_turn = False

    # =====================================================
    # GAME TYPE
    # =====================================================

    if "choose a game type" in lower:

        success = await click_button(
            event,
            [
                "gap",
                "🔠"
            ]
        )

        print(
            f"Gap Result => {success}"
        )

        return

    # =====================================================
    # ROUNDS
    # =====================================================

    if "how many rounds" in lower:

        success = await click_button(
            event,
            [
                "50"
            ]
        )

        print(
            f"Rounds Result => {success}"
        )

        return

    # =====================================================
    # DIFFICULTY
    # =====================================================

    if (
        "what is the difficulty" in lower
        or "difficulty of the" in lower
    ):

        success = await click_button(
            event,
            DIFFICULTY_KEYWORDS
        )

        print(
            f"Difficulty Result => {success}"
        )

        return

    # =====================================================
    # PATTERN DETECTION
    # =====================================================

    pattern_line = None
    letters_line = ""

    pattern_matches = re.findall(
        r"([A-Za-z](?:\s+[A-Za-z_])+)",
        text
    )

    for m in pattern_matches:

        if "_" in m:

            pattern_line = m.strip()
            break

    letters_match = re.search(
        r"(?:letters:|letter:)\s*(.+)",
        text,
        re.IGNORECASE
    )

    if letters_match:

        letters_line = letters_match.group(1)

    if not letters_line:

        found_letters = re.findall(
            r"\b[A-Za-z]\b",
            text
        )

        if found_letters:

            letters_line = " ".join(
                found_letters
            )

    # =====================================================
    # SOLVE
    # =====================================================

    if pattern_line:

        print("\nPuzzle detected")

        print(
            f"Puzzle => {pattern_line}"
        )

        print(
            f"Letters => {letters_line}"
        )

        answers = solve_puzzle(
            pattern_line,
            letters_line
        )

        # reset retry data
        current_answers = answers
        guess_index = 0

        # =================================================
        # ANSWER FOUND
        # =================================================

        if answers:

            try:

                answer = current_answers[guess_index]
                guess_index += 1

                await send_answer(answer)

                # start retry watcher
                asyncio.create_task(
                    retry_guesses(event)
                )

            except Exception as e:

                print(
                    "Send failed:",
                    e
                )

        # =================================================
        # NO ANSWER => SKIP
        # =================================================

        else:

            print(
                "No answer found => skip"
            )

            await skip_round(event)

        return

    # =====================================================
    # LEARN ANSWERS
    # =====================================================

    if (
        "correct answer" in lower
        or "passed the word" in lower
        or "got it right" in lower
        or "game canceled" in lower
    ):

        try:

            match = re.search(
                r"(?:→|⟶)\s*([A-Za-z]+)",
                text
            )

            if match:

                word = match.group(1)

                print(
                    f"\nLEARNED => {word}\n"
                )

                save_word(word)

        except Exception as e:

            print(
                "Learn Error:",
                e
            )

        return

    # =====================================================
    # GAME END
    # =====================================================

    if "game ended" in lower:

        game_running = False

        print("\nGame Ended\n")

