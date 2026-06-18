import sys
import os
from pathlib import Path

# Ensure the project root is in sys.path for robust imports in CI/CD
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

import argparse
import json
from src.config import DAILY_DIR
from src.utils import get_today_str
from src.fetch_sources import fetch_rss_feeds
from src.article_parser import parse_and_analyze
from src.deduplicate import deduplicate_insights
from src.signal_filter import filter_high_signal
from src.relevance_ranker import rank_insights
from src.dashboard_generator import generate_dashboard
from src.telegram_alert import send_alert
from src.archive_manager import save_daily_archive
from src.weekly_synthesis import generate_weekly_synthesis

def run_daily():
    print("Starting daily intelligence gathering...")
    raw_articles = fetch_rss_feeds()
    
    insights = []
    for article in raw_articles:
        try:
            insight = parse_and_analyze(article)
            if insight:
                insights.append(insight)
        except Exception as e:
            print(f"Error processing article {article.get('title')}: {e}")
            
    if not insights:
        print("No articles parsed successfully.")
        send_alert({"title": "No articles could be parsed today."})
        return

    deduped = deduplicate_insights(insights)
    high_signal = filter_high_signal(deduped)
    ranked = rank_insights(high_signal)
    
    save_daily_archive(ranked)
    generate_dashboard(ranked)
    
    if ranked:
        send_alert(ranked[0])
    else:
        send_alert({"title": "No high signal insights today."})
        
    print("Daily run complete.")

def run_weekly():
    print("Starting weekly synthesis...")
    generate_weekly_synthesis()
    
    today = get_today_str()
    today_file = DAILY_DIR / f"{today}.json"
    insights = []
    if today_file.exists():
        with open(today_file, "r", encoding="utf-8") as f:
            insights = json.load(f)
            
    generate_dashboard(insights)
    print("Weekly run complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekly", action="store_true", help="Run weekly synthesis")
    args = parser.parse_args()
    
    if args.weekly:
        run_weekly()
    else:
        run_daily()
