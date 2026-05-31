import importlib
import logging
import os

log = logging.getLogger(__name__)

# Ye function games ko user ke client par "Register" karega
async def load_all_modules(client):
    # Modules ki list (Tu yahan naye games add kar sakta hai)
    modules_to_load = [
        "modules.games.wordly.wordly",
        "modules.games.wordseek.wordseek",
        "modules.games.wordchain.wordchain",
        "modules.games.octopus.octopus"
    ]
    
    for module_path in modules_to_load:
        try:
            # Game ki file ko import karna
            module = importlib.import_module(module_path)
            # Uske 'register' function ko call karna
            module.register(client)
            log.info(f"Successfully registered: {module_path}")
        except Exception as e:
            log.error(f"Failed to load module {module_path}: {e}")

# Note: Agar future mein koi naya game dalo, toh bas upar list mein naam add kar dena.
