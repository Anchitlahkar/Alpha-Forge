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

def make_processed_key(url: str, title: str = "") -> str:
    """
    Dedupe key for the processed list.

    Keying on the URL alone meant one URL could only ever yield one article,
    so a listing or index page that later carries a different paper was blocked
    forever. Keying on URL + title lets the same URL return something new while
    still skipping a genuine repeat.

    Entries written before this change are bare URLs; those are still honoured
    as-is (they are article permalinks, where the same URL does not change
    content) and simply age out.
    """
    normalized_title = " ".join(str(title or "").split()).lower()
    if not normalized_title:
        return str(url)
    return f"{url}::{normalized_title}"


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
