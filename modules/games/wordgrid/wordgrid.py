import re, asyncio, gc, os, requests
from telethon import events
from .ocr_engine import extract_grid
from .solver import GridSolver

DICT_FILE = os.path.join(os.path.dirname(__file__), "wordgrid_dict.txt")
state = {"enabled": False, "target": None, "delay": 0.5}

def load_dict():
    if not os.path.exists(DICT_FILE):
        try:
            url = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
            data = requests.get(url).text.splitlines()
            with open(DICT_FILE, "w") as f: f.write("\n".join(data))
        except: return set()
    with open(DICT_FILE, "r") as f: return set(line.strip().upper() for line in f)

WORDS = load_dict()

def register(client):
    @client.on(events.NewMessage(chats='me', pattern=r'\.(wgon|wgoff|wgdelay)'))
    async def admin_cmds(event):
        cmd = event.pattern_match.group(1)
        if cmd == "wgon": state["enabled"] = True; await event.edit("✅ WordGrid: ON")
        elif cmd == "wgoff": state["enabled"] = False; await event.edit("❌ WordGrid: OFF")
        elif cmd == "wgdelay": state["delay"] = float(event.raw_text.split()[1]); await event.edit(f"⚡ Delay: {state['delay']}s")

    @client.on(events.NewMessage(outgoing=True))
    async def locker(event):
        if state["enabled"] and "/new" in event.raw_text:
            state["target"] = event.chat_id
            await client.send_message('me', f"🎯 **Locked to:** `{event.chat_id}`")

    @client.on(events.NewMessage)
    async def game_handler(event):
        if not state["enabled"] or event.chat_id != state["target"]: return
        if event.media:
            path = await event.download_media()
            grid = extract_grid(path)
            if not grid: await client.send_message('me', "⚠️ **OCR Failed.**"); return
            
            grid_str = "\n".join([" ".join(row) for row in grid])
            await client.send_message('me', f"🧩 **Grid Detected:**\n`{grid_str}`")
            
            solver = GridSolver(grid)
            clues = re.findall(r'([A-Z-]{3,})', event.raw_text.upper())
            lens = re.findall(r'\((\d+)\)', event.raw_text)
            
            for i, clue in enumerate(clues):
                target_len = int(lens[i]) if i < len(lens) else len(clue.replace('-', ''))
                pattern = f"^{clue.replace('-', '.')}$"
                for word in WORDS:
                    if len(word) == target_len and re.match(pattern, word) and solver.solve(word):
                        await client.send_message('me', f"✅ **Match Found:** `{word}`")
                        async with event.client.action(event.chat_id, 'typing'):
                            await asyncio.sleep(state["delay"])
                            await event.client.send_message(event.chat_id, word)
                        break
