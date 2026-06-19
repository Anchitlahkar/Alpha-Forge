from src.fetch_sources import fetch_article_text
from src.gemini_client import extract_insights
from src.utils import get_today_str

def parse_and_analyze(article: dict, processed_urls: set) -> dict | None:
    # Feature 2: Use RSS summaries whenever available. Do NOT send full article text unless summary is missing.
    text = article.get("summary", "")
    if not text:
        text = fetch_article_text(article["link"])
    
    # Feature 2: Skip articles shorter than 200 characters
    if len(text) < 200:
        print(f"⏭️  (Too short: {len(text)} chars, skipping: {article['title'][:40]})")
        # Mark as processed so we don't attempt to process it in future runs
        processed_urls.add(article["link"])
        return None
        
    print(f"🔍 Analyzing: {article['title'][:60]}...", end=" ", flush=True)
    
    insight = extract_insights(
        text, 
        article["link"], 
        article_source_name=article["source_name"], 
        article_title=article["title"], 
        article_published=article.get("published", "")
    )
    
    processed_urls.add(article["link"])
    
    if insight:
        if not insight.get("source_url"):
            insight["source_url"] = article["link"]
        if not insight.get("source_name"):
            insight["source_name"] = article["source_name"]
        insight["original_category"] = article["category"]
        print(f"✨ (Signal: {insight.get('signal_score', 'N/A')})")
        return insight
    else:
        # Feature 7: Fail Safe Mode
        print("⚠️ (Gemini unavailable, using fail-safe mode)")
        fail_safe_insight = {
            "title": article["title"],
            "category": article["category"],
            "signal_score": 5.0,  # default score to pass minimum filters
            "personal_relevance": 5.0,
            "why_it_matters": "Analysis unavailable.",
            "tldr": "Analysis unavailable.",
            "key_points": [],
            "action_items": [],
            "source_name": article["source_name"],
            "source_url": article["link"],
            "date": article.get("published", "") or get_today_str(),
            "original_category": article["category"]
        }
        return fail_safe_insight
