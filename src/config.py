import sys
import io
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DAILY_DIR = DATA_DIR / "daily"
WEEKLY_DIR = DATA_DIR / "weekly"
CONFIG_DIR = BASE_DIR / "config"
TEMPLATES_DIR = BASE_DIR / "templates"
DASHBOARD_DIR = BASE_DIR / "dashboard"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_KEYS_ENV = os.getenv("GEMINI_API_KEYS", "")
if GEMINI_API_KEYS_ENV:
    GEMINI_API_KEYS = [k.strip() for k in GEMINI_API_KEYS_ENV.split(",") if k.strip()]
elif GEMINI_API_KEY:
    GEMINI_API_KEYS = [GEMINI_API_KEY]
else:
    GEMINI_API_KEYS = []

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PAGES_URL = os.getenv("PAGES_URL", "https://example.github.io/dashboard")

def load_feeds() -> dict:
    with open(CONFIG_DIR / "feeds.json", "r") as f:
        return json.load(f)

def load_scoring() -> dict:
    with open(CONFIG_DIR / "scoring.json", "r") as f:
        return json.load(f)

# Ensure data directories exist
for d in [DAILY_DIR, WEEKLY_DIR, DASHBOARD_DIR]:
    d.mkdir(parents=True, exist_ok=True)
