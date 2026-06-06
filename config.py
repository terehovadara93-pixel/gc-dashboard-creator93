import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

DEFAULTS = {
    "gc_url": "",
    "gc_email": "",
    "gc_password": "",
    "tg_bot": "zerocoder_university_bot",
}

def load() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**DEFAULTS, **data}
    return dict(DEFAULTS)

def save(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
