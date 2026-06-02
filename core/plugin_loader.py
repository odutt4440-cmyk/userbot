import importlib
import logging
import os

log = logging.getLogger(__name__)

# Ye function saare userbot modules (Games, Fun, Admin) ko client par register karta hai
async def load_all_modules(client):
    # Modules ki list - Yahan humne Fun category ka Clone tool add kiya hai
    modules_to_load = [
        # --- Game Modules ---
        "modules.games.wordly.wordly",
        "modules.games.wordseek.wordseek",
        "modules.games.wordchain.wordchain",
        "modules.games.octopus.octopus",
        
        # --- Fun Modules ---
        "modules.fun.clone" # <--- Naya Clone Tool yahan add ho gaya
    ]
    
    for module_path in modules_to_load:
        try:
            # Module ko dynamic import karna
            module = importlib.import_module(module_path)
            # Har module mein 'register' function hona zaroori hai
            module.register(client)
            log.info(f"Successfully registered: {module_path}")
        except Exception as e:
            log.error(f"Failed to load module {module_path}: {e}")

# Hint: Future mein agar 'BanAll' ya 'PMPermit' jaise tools banaoge, 
# toh bas unka path is list mein daal dena.
