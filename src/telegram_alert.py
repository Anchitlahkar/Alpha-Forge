import requests
from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GITHUB_PAGES_URL

def send_alert(top_insight: dict):
    # Proper validation of credentials and placeholders
    placeholders = ["your_telegram_bot_token_here", "your_telegram_chat_id_here", ""]
    
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN in placeholders:
        print("Telegram Bot Token is missing or using placeholder. Skipping alert.")
        return
        
    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID in placeholders:
        print("Telegram Chat ID is missing or using placeholder. Skipping alert.")
        return
        
    title = top_insight.get("title", "No insights today")
    
    message = (
        "📊 *Daily Intelligence Brief Ready*\n\n"
        f"🏆 *Top Insight:* {title}\n\n"
        f"🔗 *Dashboard:* [View Insights]({GITHUB_PAGES_URL})"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("Telegram alert sent successfully.")
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")
