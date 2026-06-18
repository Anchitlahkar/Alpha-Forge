from src.fetch_sources import fetch_article_text
from src.gemini_client import extract_insights

def parse_and_analyze(article: dict) -> dict | None:
    print(f"🔍 Analyzing: {article['title'][:60]}...", end=" ", flush=True)
    text = fetch_article_text(article["link"])
    if not text:
        text = article.get("summary", "")
    
    if len(text) < 100:
        print("⏭️  (Too short, skipping)")
        return None
        
    insight = extract_insights(text, article["link"])
    if insight:
        if not insight.get("sources"):
            insight["sources"] = [article["link"]]
        insight["original_category"] = article["category"]
        print(f"✨ (Signal: {insight.get('signal_score', 'N/A')})")
        return insight
    print("❌ (Analysis failed)")
    return None
