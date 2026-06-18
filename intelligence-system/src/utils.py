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
