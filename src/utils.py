import json
from datetime import datetime
from pathlib import Path

def save_json(data: dict | list, filepath: Path) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_json(filepath: Path) -> dict | list:
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def get_today_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")

def load_processed_urls() -> set:
    from src.config import DATA_DIR
    filepath = DATA_DIR / "processed_urls.json"
    if not filepath.exists():
        return set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return set(data)
    except Exception as e:
        print(f"Error loading processed URLs: {e}")
    return set()

def save_processed_urls(processed_urls: set) -> None:
    from src.config import DATA_DIR
    filepath = DATA_DIR / "processed_urls.json"
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(list(processed_urls), f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving processed URLs: {e}")
