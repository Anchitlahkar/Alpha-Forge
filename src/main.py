import sys
import os
from pathlib import Path

# Fix sys.path for production environments
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

import argparse
import json
from src.config import DAILY_DIR
from src.utils import get_today_str, load_processed_urls, save_processed_urls
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
    
    processed_urls = load_processed_urls()
    seen_urls = set()
    
    insights = []
    analyzed_count = 0
    
    for article in raw_articles:
        url = article.get("link")
        if not url:
            continue
            
        # Feature 2: Skip duplicate URL in current run
        if url in seen_urls:
            print(f"Skipping duplicate URL in current run: {url}")
            continue
        seen_urls.add(url)
        
        # Feature 2: Skip already processed URL from past runs
        if url in processed_urls:
            print(f"Skipping already processed URL: {url}")
            continue
            
        # Feature 2: Hard cap of 10 articles analyzed per run
        if analyzed_count >= 10:
            print("Reached MAX_ARTICLES_PER_RUN (10). Skipping remaining articles.")
            break
            
        try:
            insight = parse_and_analyze(article, processed_urls)
            if insight:
                insights.append(insight)
                analyzed_count += 1
        except Exception as e:
            print(f"Skipping article due to analysis failure: {e}")
            
    # Save updated processed URLs
    save_processed_urls(processed_urls)
            
    if not insights:
        print("No insights were extracted today.")
        save_daily_archive([])
        generate_dashboard([])
        send_alert({"title": "No signal found today."})
        return

    # Pipeline stages
    deduped = deduplicate_insights(insights)
    high_signal = filter_high_signal(deduped)
    ranked = rank_insights(high_signal)
    
    # Artifact generation
    save_daily_archive(ranked)
    generate_dashboard(ranked)
    
    if ranked:
        send_alert(ranked[0])
    else:
        send_alert({"title": "Gathering complete: No items passed signal filter."})
        
    print("Daily run complete.")

def run_weekly():
    print("Starting weekly synthesis...")
    try:
        generate_weekly_synthesis()
    except Exception as e:
        print(f"Weekly synthesis failed: {e}")
    
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
