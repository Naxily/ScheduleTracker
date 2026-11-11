import json
import os

DOCUMENTS_DIR = os.path.join(os.path.expanduser("~"), "Documents", "ScheduleTracker")
CONFIG_PATH = os.path.join(DOCUMENTS_DIR, "config.json")

DEFAULT_CONFIG = {
    "group": None,  
    "theme": "dark",
    "cleanup_enabled": True
}

def init_dirs():
    os.makedirs(DOCUMENTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(DOCUMENTS_DIR, "schedules"), exist_ok=True)

def load_config():
    init_dirs()
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return DEFAULT_CONFIG

def save_config(config_data):
    init_dirs()
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)
