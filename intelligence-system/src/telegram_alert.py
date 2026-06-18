import requests
from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GITHUB_PAGES_URL

def send_alert(top_insight: dict):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not set. Skipping alert.")
        return
        
    title = top_insight.get("title", "No insights today")
    
    message = (
        "📊 *Daily Intelligence Brief Ready*\n\n"
        f"🏆 *Top Insight:* {title}\n\n"
        f"🔗 *Dashboard:* {GITHUB_PAGES_URL}"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Telegram alert sent successfully.")
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")
