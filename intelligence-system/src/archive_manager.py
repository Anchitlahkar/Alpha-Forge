from src.config import DAILY_DIR
from src.utils import get_today_str, save_json

def save_daily_archive(insights: list[dict]):
    today = get_today_str()
    archive_path = DAILY_DIR / f"{today}.json"
    save_json(insights, archive_path)
    print(f"Archive saved to {archive_path}")
