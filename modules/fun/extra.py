import asyncio
from telethon import events

# --- 🎨 ASCII ARTS DICTIONARY (Clean Look) ---
ARTS = {
    "hi": """
⠀⠀⠀⠀⠀⢀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⢰⣿⡿⠗⠀⠠⠄⡀⠀⠀⠀⠀
⠀⠀⠀⠀⡜⠁⠀⠀⠀⠀⠀⠈⠑⢶⣶⡄
⢀⣶⣦⣸⠀⢼⣟⡇⠀⠀⢀⣀⠀⠘⡿⠃
⠀⢿⣿⣿⣄⠒⠀⠠⢶⡂⢫⣿⢇⢀⠃⠀
⠀⠈⠻⣿⣿⣿⣶⣤⣀⣀⣀⣂⡠⠊⠀⠀
⠀⠀⠀⠃⠀⠀⠉⠙⠛⠿⣿⣿⣧⠀⠀⠀
⠀⠀⠘⡀⠀⠀⠀⠀⠀⠀⠘⣿⣿⡇⠀⠀
⠀⠀⠀⣷⣄⡀⠀⠀⠀⢀⣴⡟⠿⠃⠀⠀
⠀⠀⠀⢻⣿⣿⠉⠉⢹⣿⣿⠁⠀⠀⠀⠀ HELLO GUYSIS
⠀⠀⠀⠀⠉⠁⠀⠀⠀⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀
""",

    "hello": """
╔┓┏╦━━╦┓╔┓╔━━╗
║┗┛║┗━╣┃║┃║╯╰║     
║┏┓║┏━╣┗╣┗╣╰╯║      
╚┛┗╩━━╩━╩━╩━━╝
""",

    "gn": """
∩――――∩     ˗ˏˋ ★ ˎˊ˗
|    ∧  ﾍ        |
|    (* ´ ▽`)     |  < ᴳᵒᵒᵈᴺⁱᵍʜᴛ   ♡
|ﾉ^⌒⌒づ￣  ＼
(　ノ　　⌒ ヽ ＼
＼　　|￣￣￣￣￣|
　 ＼,ﾉ|
""",

    "gm": """
Good morning!
     へ   +        —̳͟͞͞💗
૮  -   ̫ ՛ )つ  —̳͟͞͞ 💗         —̳͟͞͞💗 +
(つ    <                —̳͟͞͞💗
｜  _   つ      +  —̳͟͞͞💗         —̳͟͞͞💗 ˚
`し´
""",

    "bear": """
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⣰⣿⣿⣿⣿⣦⣀⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢿⣿⠟⠋⠉⠀⠀⠀⠀⠉⠑⠢⣄⡀⠀⠀⠀⠀⠀                
⠀⠀⠀⠀⠀⢠⠞⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢿⣿⣿⣦⡀                
⠀⣀⠀⠀⢀⡏⠀⢀⣴⣶⣶⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⣿⣿⠇
⣾⣿⣿⣦⣼⡀⠀⢺⣿⣿⡿⠃⠀⠀⠀⠀⣠⣤⣄⠀⠀⠈⡿⠋⠀
⢿⣿⣿⣿⣿⣇⠀⠤⠌⠁⠀⡀⢲⡶⠄⢸⣏⣿⣿⠀⠀⠀⡇⠀⠀
⠈⢿⣿⣿⣿⣿⣷⣄⡀⠀⠀⠈⠉⠓⠂⠀⠙⠛⠛⠠⠀⡸⠁⠀⠀
⠀⠀⠻⣿⣿⣿⣿⣿⣿⣷⣦⣄⣀⠀⠀⠀⠀⠑⠀⣠⠞⠁⠀⠀⠀
⠀⠀⠀⢸⡏⠉⠛⠛⠛⠿⠿⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⠀⠀⠀⠀
⠀⠀⠀⠸⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠛⢿⣿⣿⣿⣿⡄⠀⠀⠀⠀
⠀⠀⠀⢷      𝐈𝐂𝐄 𝐁𝐄𝐀𝐑 🐻‍❄️      ⠈⢻⣿⣿⣿⣿⡀⠀⠀⠀
⠀⠀⠀⢸⣆⠀⠀⠀⠀⠀      ⠀⠀⣿⣿⣿⣿⡇⠀⠀⠀
⠀⠀⠀⢸⣿⣦⣀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⡟⠻⠿⠟⡀⠀⠀⠀
⠀⠀ ⠀⣿⣿⣿⣿⣶⠶⠤⠤⢤⣶⣾⣿⣿⡇⠀
⠀⠀⠀⠀⠹⣿⣿⣿⠏⠀⠀⠀⠈⢿⣿⣿⡿⠁⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠈⠉⠉⠀⠀⠀⠀⠀⠀⠉⠉⠀
""",

    "fuck": """
 ⢀⣴⡿⠿⣦⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⢸⡿⣀⠠⠇⢧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⢷⠀⢀⣀⠘⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠈⣇⠉⠀⠀⠹⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⢠⢾⡄⠀⠀⠀⢻⠞⠓⢺⠉⠓⣦⡀⠀⠀⠀
⠀⣠⡾⢂⣱⠐⠛⠭⠀⢃⠀⠀⠡⡀⠈⠳⣄⠀⠀
⣴⠫⠛⠀⠈⢇⠀⠀⠀⠀⠆⠀⠀⢡⠀⠀⠘⣆⠀
⣇⢇⠀⠀⠀⠀⢆⠀⠀⠀⠈⡄⠀⠀⢧⠀⠀⢸⡆
⢻⠸⡀⠀⠀⠀⢸⡆⠀⠀⠀⠐⠀⠀⠀⠀⢀⡞⠀
⢸⠀⢳⠀⠀⠀⠀⠋⠀⠀⠀⠀⠀⠀⠀⣣⠾⠀⠀
⠈⠳⣄⢆⠀⠀⠀⠀⠆⠀⠀⠀⣠⡦⠞⠃⠀F*CK YOU
⠀⠀⠈⠛⠷⠤⠤⠖⠚⠒⠒⠚⠁⠀⠀⠀⠀⠀⠀⠀
"""
}

def register(client):

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.(hi|hello|gn|gm|bear|fuck)"))
    async def ascii_handler(event):
        cmd = event.pattern_match.group(1).lower()
        # Fuck command ke liye special multi-step edit
        if cmd == "fuck":
            await event.edit("F*ck You Baby 🖕")
            await asyncio.sleep(1.5)
            await event.edit("Baby, Ohh.. Yes 👅")
            await asyncio.sleep(1.5)
            
        await event.edit(f"<code>{ARTS[cmd]}</code>", parse_mode='html')

    # --- 2. EMOJI LOOPS ---
    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.(hehe|sad|heart|sleep)"))
    async def emoji_handler(event):
        cmd = event.pattern_match.group(1).lower()
        lists = {
            "hehe": ["😀", "😃", "😄", "😁", "😎", "😅", "🤣", "😂", "😛", "😜", "🤪", "😝", "🤫", "🫡", "😶", "😆"],
            "sad": ["🙂", "🙃", "🥲", "😐", "😕", "🙁", "☹️", "😰", "😥", "😢", "😭", "😣", "😞", "😩"],
            "heart": ["💌", "💘", "💝", "💖", "💗", "💓", "💞", "💕", "💟", "❣️", "❤️‍🔥", "❤️‍🩹", "❤️", "🩷", "🧡", "💛", "💚", "💙", "🩵", "💜", "🤎", "🖤", "🩶", "🤍"],
            "sleep": ["😴🥱😴🥱", "🥱😴🥱😴", "😴🥱😴🥱", "🥱😴😴🥱"]
        }
        for emoji in lists[cmd]:
            await event.edit(emoji)
            await asyncio.sleep(0.8)
        if cmd == "heart": await event.edit("You Are So Cute 🙈")

    # --- 3. HACKING ANIMATION ---
    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.hack"))
    async def hack_handler(event):
        await event.edit("`Trying to get the weakness...` ")
        await asyncio.sleep(1.5)
        await event.edit("`Found Some INFORMATION...` ")
        await asyncio.sleep(1)
        for i in range(0, 101, 10):
            await event.edit(f"<code>[Processing... {'#'*(i//10)}{' '*(10-i//10)}] {i}%</code>", parse_mode='html')
            await asyncio.sleep(0.4)
        await event.edit("`Gained Access... You are Hacked Buddy!` 😈")
