import os
from dotenv import load_dotenv

# .env file se data load karne ke liye
load_dotenv()

# --- Telegram API Credentials ---
# Inhe my.telegram.org se le sakte ho
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

# BotFather se mila hua Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# --- Database Settings ---
# MongoDB Atlas ka connection string yahan aayega
MONGO_URL = os.getenv("MONGO_URL", "")

# --- Admin & Security ---
# Tera Telegram User ID (Approve karne ke liye aur errors dekhne ke liye)
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# (Optional) Log Group ID jahan screenshots forward honge approval ke liye
LOG_GROUP = int(os.getenv("LOG_GROUP", "0"))

# --- Bot Customization ---
# Welcome Pic ka URL (Ya local path)
START_PIC = os.getenv("START_PIC", "https://telegra.ph/file/your_image_path.jpg")
