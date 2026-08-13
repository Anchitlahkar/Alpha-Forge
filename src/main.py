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
from src.utils import get_today_str, load_processed_urls, save_processed_urls, make_processed_key
from src.fetch_sources import fetch_rss_feeds, LAST_FEED_HEALTH
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
    seen_keys = set()
    
    insights = []
    analyzed_count = 0
    dropped_analysis = 0

    for article in raw_articles:
        url = article.get("link")
        if not url:
            continue
            
        # Keyed on URL + title, so the same URL can still bring a different
        # paper through; only an actual repeat of the same piece is skipped.
        key = make_processed_key(url, article.get("title", ""))

        # Feature 2: Skip the same article twice in one run
        if key in seen_keys:
            print(f"Skipping duplicate article in current run: {url}")
            continue
        seen_keys.add(key)

        # Feature 2: Skip articles already handled in past runs.
        # `url in processed_urls` catches entries written before keys carried
        # titles; those are permalinks, so they stay skipped and age out.
        if key in processed_urls or url in processed_urls:
            print(f"Skipping already processed article: {url}")
            continue
            
        # Feature 2: Hard cap of 10 articles analyzed per run
        if analyzed_count >= 10:
            print("Reached MAX_ARTICLES_PER_RUN (10). Skipping remaining articles.")
            break
            
        try:
            insight = parse_and_analyze(article, processed_urls)
            if insight:
                # If analysis failed and returned fail-safe values, do not count it and try next article
                if insight.get("why_it_matters") == "Analysis unavailable.":
                    print(f"⚠️ Article analysis failed (fail-safe). Continuing to next article to take its place.")
                    dropped_analysis += 1
                    continue
                insights.append(insight)
                analyzed_count += 1
            else:
                print(f"Skipping article. Continuing to next article to take its place.")
        except RuntimeError as re_err:
            if "All Gemini API keys exhausted" in str(re_err):
                raise re_err
            print(f"Skipping article due to analysis failure: {re_err}. Continuing to next article to take its place.")
        except Exception as e:
            print(f"Skipping article due to analysis failure: {e}. Continuing to next article to take its place.")
            
    # Save updated processed URLs
    save_processed_urls(processed_urls)

    failed_feeds = sorted(n for n, s in LAST_FEED_HEALTH.items() if s != "OK")
    run_stats = {
        "feeds_polled": len(LAST_FEED_HEALTH),
        "feeds_ok": sum(1 for s in LAST_FEED_HEALTH.values() if s == "OK"),
        "failed_feeds": failed_feeds,
        "analyzed": analyzed_count,
        "dropped_analysis": dropped_analysis,
        "cleared": 0,
    }

    if not insights:
        print("No insights were extracted today.")
        # Archive the empty day honestly; the dashboard falls back to the last
        # good run on its own rather than rendering an empty page.
        save_daily_archive([])
        generate_dashboard([], run_stats=run_stats)
        send_alert({"title": "No signal found today."})
        return

    # Pipeline stages
    deduped = deduplicate_insights(insights)
    high_signal = filter_high_signal(deduped)
    ranked = rank_insights(high_signal)
    run_stats["cleared"] = len(ranked)

    # Artifact generation
    save_daily_archive(ranked)
    generate_dashboard(ranked, run_stats=run_stats)

    if ranked:
        send_alert(ranked[0])
    else:
        send_alert({"title": "Gathering complete: No items passed signal filter."})
        
    print("Daily run complete.")

def run_weekly():
    print("Starting weekly synthesis...")
    try:
        generate_weekly_synthesis()
    except RuntimeError as re_err:
        if "All Gemini API keys exhausted" in str(re_err):
            raise re_err
        print(f"Weekly synthesis failed: {re_err}")
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
