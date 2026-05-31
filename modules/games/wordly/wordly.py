import pyautogui
import time
import requests
import re
from collections import Counter
from telethon import TelegramClient, events

# =========================
# TELEGRAM API
# =========================
api_id = 27309741
api_hash = "YOUR_API_HASH"

client = TelegramClient("scramble_session", api_id, api_hash)

# =========================
# CONFIG
# =========================
TARGET_CHAT_ID = -1002411036300

ROUNDS = 20
TYPING_SPEED = 0.000
MIN_LEN = 8
MAX_LEN = 12

used_words = set()
round_count = 0
current_letters = None

# =========================
# LOAD DICTIONARY
# =========================
def load_words():
    print("Downloading common dictionary...")

    url = "https://raw.githubusercontent.com/dolph/dictionary/master/enable1.txt"
    data = requests.get(url).text.splitlines()

    valid = []

    for w in data:

        w = w.lower().strip()

        if MIN_LEN <= len(w) <= MAX_LEN and w.isalpha():

            valid.append(
                (w, Counter(w))
            )

    print("Loaded:", len(valid))

    return valid


words = load_words()

# =========================
# SOLVER
# repeated letters allowed
# =========================
def solve(letters):

    allowed = set(letters.lower())

    candidates = []

    for word, wc in words:

        if word in used_words:
            continue

        if all(
            c in allowed
            for c in word
        ):
            candidates.append(word)

    if not candidates:
        return None

    candidates.sort(
        key=len,
        reverse=True
    )

    best = candidates[0]

    used_words.add(best)

    return best


# =========================
# EXTRACT:
# A,T,H,O,D,R,S,E
# =========================
def extract_letters(text):

    m = re.search(
        r'([A-Z](?:\s*,\s*[A-Z])+)',
        text.upper()
    )

    if not m:
        return None

    letters = m.group(1)

    return "".join(
        re.findall(r"[A-Z]", letters)
    )

# =========================
# TELEGRAM
# =========================
@client.on(events.NewMessage(chats=TARGET_CHAT_ID))
async def handler(event):

    global round_count
    global current_letters
    global used_words

    msg = event.message.message

    if not msg:
        return

    text = msg.upper()

    # New game starts
    if "TOTAL: 0/20" in text:

        current_letters = extract_letters(msg)

        if not current_letters:
            return

        round_count = 0
        used_words.clear()

        print("\n🎮 NEW GAME")
        print("Letters:", current_letters)

    if not current_letters:
        return

    if round_count >= ROUNDS:

        print("\n✅ Finished 20 rounds")

        current_letters = None
        return

    word = solve(current_letters)

    if not word:
        print("No word left")

        current_letters = None
        return

    round_count += 1

    print(f"\n🔥 Round {round_count}/{ROUNDS}")
    print("Typing:", word)

    for ch in word:
        pyautogui.write(ch)
        time.sleep(TYPING_SPEED)

    pyautogui.press("enter")

print("🚀 Bot started")

client.start()
client.run_until_disconnected()