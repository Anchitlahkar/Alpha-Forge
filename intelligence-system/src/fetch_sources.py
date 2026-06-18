import feedparser
import requests
from bs4 import BeautifulSoup
from src.config import load_feeds

def fetch_rss_feeds() -> list[dict]:
    feeds = load_feeds()
    articles = []
    
    for category, sources in feeds.items():
        for source in sources:
            print(f"📡 Fetching {source['name']}...", end=" ", flush=True)
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(source['url'], headers=headers, timeout=10)
                resp.raise_for_status()
                parsed = feedparser.parse(resp.content)
                
                count = 0
                for entry in parsed.entries[:3]:
                    articles.append({
                        "category": category,
                        "source_name": source["name"],
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "summary": entry.get("summary", "")
                    })
                    count += 1
                print(f"✅ (Found {count})")
            except Exception as e:
                print(f"❌ Failed: {e}")
    return articles

def fetch_article_text(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        
        # Remove scripts and styles
        for script in soup(["script", "style"]):
            script.decompose()
            
        text = soup.get_text(separator="\n")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return "\n".join(chunk for chunk in chunks if chunk)
    except Exception as e:
        print(f"Error fetching article text from {url}: {e}")
        return ""
