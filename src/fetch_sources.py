import feedparser
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
from src.config import load_feeds

class RSSFetcher:
    def __init__(self, name: str, url: str, category: str):
        self.name = name
        self.url = url
        self.category = category
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*"
        })

    def fetch(self) -> list[dict]:
        # 1. RSS Fetch
        try:
            resp = self.session.get(self.url, timeout=30, allow_redirects=True)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            if parsed.entries:
                return self._parse_entries(parsed.entries)
        except Exception as e:
            print(f"[RSS Fetcher] RSS failed for {self.name}: {e}. Trying RSS Retry...")
            
        # 2. RSS Retry
        try:
            parsed = feedparser.parse(self.url)
            if parsed.entries:
                return self._parse_entries(parsed.entries)
        except Exception as e:
            print(f"[RSS Fetcher] RSS Retry failed for {self.name}: {e}")
            
        # 3. Generic Homepage Scrape
        return self._scrape_generic_homepage()

    def _parse_entries(self, entries) -> list[dict]:
        articles = []
        for entry in entries[:3]:
            articles.append({
                "category": self.category,
                "source_name": self.name,
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", "")
            })
        return articles

    def _scrape_generic_homepage(self) -> list[dict]:
        homepage_url = self.url
        for suffix in ["/feed.xml", "/feed", "/rss.xml", "/rss", "/feed.rss", "/feed/"]:
            if homepage_url.endswith(suffix):
                homepage_url = homepage_url[:-len(suffix)]
                break
        
        print(f"[RSS Fetcher] Falling back to Generic Homepage Scrape for {self.name} on {homepage_url}...")
        try:
            resp = self.session.get(homepage_url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "html.parser")
            
            articles = []
            seen = set()
            for a in soup.find_all("a", href=True):
                href = a["href"]
                title = a.get_text().strip()
                title = " ".join(title.split())
                
                if len(title) > 20 and not any(x in href.lower() for x in ["javascript:", "mailto:", "tel:", "facebook.com", "twitter.com", "linkedin.com", "github.com", "/tag/", "/category/", "/author/"]):
                    full_url = urllib.parse.urljoin(homepage_url, href)
                    if full_url not in seen:
                        seen.add(full_url)
                        articles.append({
                            "category": self.category,
                            "source_name": self.name,
                            "title": title,
                            "link": full_url,
                            "published": "",
                            "summary": ""
                        })
            return articles[:3]
        except Exception as e:
            print(f"[RSS Fetcher] Generic homepage scrape failed for {self.name}: {e}")
        return []

class SubstackFetcher(RSSFetcher):
    def fetch(self) -> list[dict]:
        # 1. Try parent RSS fetch
        articles = super().fetch()
        if articles:
            return articles

        # 2. Homepage Scrape: Use Substack Archive API
        print(f"[Substack Fetcher] Falling back to Homepage Scrape (Archive API) for {self.name}...")
        try:
            match = re.search(r"https?://([^.]+)\.substack\.com", self.url)
            if match:
                subdomain = match.group(1)
                api_url = f"https://{subdomain}.substack.com/api/v1/archive?sort=new&limit=5"
                resp = self.session.get(api_url, timeout=30)
                resp.raise_for_status()
                posts = resp.json()
                
                parsed_articles = []
                for p in posts[:3]:
                    parsed_articles.append({
                        "category": self.category,
                        "source_name": self.name,
                        "title": p.get("title", ""),
                        "link": p.get("canonical_url", ""),
                        "published": p.get("post_date", ""),
                        "summary": p.get("description", p.get("subtitle", ""))
                    })
                return parsed_articles
        except Exception as e:
            print(f"[Substack Fetcher] Archive API scrape failed for {self.name}: {e}")
            
        return []

class NetflixTechBlogFetcher(RSSFetcher):
    def fetch(self) -> list[dict]:
        # 1. Try parent RSS fetch (netflixtechblog.com/feed)
        articles = super().fetch()
        if articles:
            return articles

        # 2. RSS Retry with Medium feed URL
        print(f"[Netflix Fetcher] Falling back to RSS Retry (Medium feed) for {self.name}...")
        medium_feed_url = "https://medium.com/feed/netflix-techblog"
        try:
            resp = self.session.get(medium_feed_url, timeout=30)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            if parsed.entries:
                return self._parse_entries(parsed.entries)
        except Exception as e:
            print(f"[Netflix Fetcher] Medium feed failed for {self.name}: {e}")

        # 3. Homepage Scrape
        print(f"[Netflix Fetcher] Falling back to Homepage Scrape for {self.name}...")
        try:
            homepage_url = "https://medium.com/netflix-techblog"
            resp = self.session.get(homepage_url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "html.parser")
            
            articles = []
            seen_links = set()
            for a in soup.find_all("a", href=True):
                href = a["href"]
                title = a.get_text().strip()
                title = " ".join(title.split())
                if len(title) > 15 and re.search(r"-[0-9a-f]+$", href):
                    full_url = urllib.parse.urljoin(homepage_url, href)
                    full_url = full_url.split("?")[0]
                    if full_url not in seen_links:
                        seen_links.add(full_url)
                        articles.append({
                            "category": self.category,
                            "source_name": self.name,
                            "title": title,
                            "link": full_url,
                            "published": "",
                            "summary": ""
                        })
            if articles:
                return articles[:3]
        except Exception as e:
            print(f"[Netflix Fetcher] Homepage scrape failed for {self.name}: {e}")

        return []

class HuggingFacePapersFetcher(RSSFetcher):
    def fetch(self) -> list[dict]:
        # 1. Try RSS (HN search feed)
        try:
            resp = self.session.get(self.url, timeout=30)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            # HF Papers requires at least 5 articles
            if len(parsed.entries) >= 5:
                return self._parse_hf_entries(parsed.entries)
        except Exception as e:
            print(f"[HF Papers Fetcher] RSS failed: {e}")

        # 2. Fallback: Homepage Scrape
        print(f"[HF Papers Fetcher] Falling back to Homepage Scrape...")
        try:
            homepage_url = "https://huggingface.co/papers"
            resp = self.session.get(homepage_url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "html.parser")
            
            papers = []
            seen = set()
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("/papers/") and not href.endswith("/papers"):
                    title = a.get_text().strip()
                    title = " ".join(title.split())
                    if title and len(title) > 10:
                        paper_url = urllib.parse.urljoin("https://huggingface.co", href)
                        if paper_url not in seen:
                            seen.add(paper_url)
                            papers.append({
                                "category": self.category,
                                "source_name": self.name,
                                "title": title,
                                "link": paper_url,
                                "published": "",
                                "summary": f"Research paper on Hugging Face: {title}"
                            })
            if len(papers) >= 5:
                return papers[:5]
            elif papers:
                return papers
        except Exception as e:
            print(f"[HF Papers Fetcher] Homepage scrape failed: {e}")

        return []

    def _parse_hf_entries(self, entries) -> list[dict]:
        articles = []
        for entry in entries[:5]:
            articles.append({
                "category": self.category,
                "source_name": self.name,
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", "")
            })
        return articles

def get_fetcher(name: str, url: str, category: str) -> RSSFetcher:
    if name == "Hugging Face Papers":
        return HuggingFacePapersFetcher(name, url, category)
    elif name == "Netflix Tech Blog":
        return NetflixTechBlogFetcher(name, url, category)
    elif "substack.com" in url or name in ["Import AI", "Quantum Zeitgeist"]:
        return SubstackFetcher(name, url, category)
    else:
        return RSSFetcher(name, url, category)

def fetch_rss_feeds() -> list[dict]:
    feeds = load_feeds()
    articles = []
    
    # Run fetchers and store articles
    health_results = {}
    for category, sources in feeds.items():
        for source in sources:
            name = source["name"]
            url = source["url"]
            print(f"📡 Fetching {name}...", end=" ", flush=True)
            fetcher = get_fetcher(name, url, category)
            try:
                source_articles = fetcher.fetch()
                if name == "Hugging Face Papers":
                    is_ok = len(source_articles) >= 5
                else:
                    is_ok = len(source_articles) > 0
            except Exception:
                source_articles = []
                is_ok = False
                
            health_results[name] = "OK" if is_ok else "FAIL"
            if is_ok:
                articles.extend(source_articles)
                print(f"✅ (Found {len(source_articles)})")
            else:
                print(f"❌ Failed")
                
    # Print the Source Health Report
    print("\nSource Health Report\n")
    for name in [
        "Import AI", 
        "Quantum Zeitgeist", 
        "Netflix Tech Blog", 
        "Hugging Face Papers",
        "Net Interest",
        "The Diff",
        "Apricitas Economics"
    ]:
        status = health_results.get(name, "FAIL")
        print(f"{name}: {status}\n")
        
    return articles

def fetch_article_text(url: str) -> str:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=30)
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
