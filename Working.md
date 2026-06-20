# 🏗️ Alpha-Forge Architecture & Pipeline Processing Logic

This document provides an exhaustive technical specification of the **Alpha-Forge** Intelligence System. It walks through all components, logic lifecycles, and processing phases.

---

## 1. High-Level Ingestion & Analysis Architecture

The platform operates as a modular, resilient intelligence pipeline. The data flow follows a pipeline-adapter model designed to automatically mitigate remote connection errors, rate limit barriers, and analysis anomalies.

```text
[Pipeline Ingestion Init]
           │
           ▼
┌────────────────────────────────────────────────────────┐
│               Source Health Ingestor                   │
│   (Polls config/feeds.json categorizing AI, Finance,   │
│    Quantum, Engineering, Semiconductors, Startups)    │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                Fetcher Factory Router                  │
│       (Resolves source to specific adapter class)      │
└────┬─────────────────┬───────────────────┬─────────────┘
     │                 │                   │
     ▼                 ▼                   ▼
┌──────────┐    ┌─────────────┐    ┌───────────────┐
│ Substack │    │ Netflix     │    │ Hugging Face  │
│ Fetcher  │    │ Fetcher     │    │ Papers        │
└────┬─────┘    └──────┬──────┘    └───────┬───────┘
     │                 │                   │
     ▼                 ▼                   ▼
┌────────────────────────────────────────────────────────┐
│                   Fetcher Lifecycle                    │
│   RSS -> RSS Retry (Alternative/Direct) -> Scrape      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                 Source Health Report                   │
│   (Evaluates fetched article sizes; prints OK/FAIL)   │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               Article Processing Loop                  │
├────────────────────────────────────────────────────────┤
│ 1. seen_urls check (removes duplicates in-run)         │
│ 2. processed_urls check (skips historical archive)     │
│ 3. summary evaluation (<200 char triggers full scrape) │
│ 4. parse_and_analyze logic (Gemini validation calls)    │
│ 5. Failure substitution (skipped/fail-safe replaces)   │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                  Gemini Client Manager                 │
├────────────────────────────────────────────────────────┤
│ 1. Startup Diagnostics (lists masked keys)             │
│ 2. Startup Verification (tests VALID/INVALID keys)     │
│ 3. 429 Quota interception & dynamic Client rotation    │
│ 4. JSON Repair Engine (cleans syntax, balances brackets)│
│ 5. Failure termination (RuntimeError propagation)      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               Deduplication & Ranking                  │
│   (Clustered group parsing; custom scoring weights)    │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│            Dashboard HTML & Telegram Alert             │
└────────────────────────────────────────────────────────┘
```

---

## 2. Ingestion Adapters & Pipeline Resilience

 ingesting raw feeds utilizes specific class fetchers mapped via a Factory Router:

### A. Fetcher Adapter Classes (`src/fetch_sources.py`)
1. **`RSSFetcher` (Base)**:
   * Reuses connections using `requests.Session()`.
   * Establishes default headers including real browser `User-Agent` (`Chrome/120.0.0.0`) and RSS compatibility headers.
   * Leverages a 30-second timeout with redirection enabled.
2. **`SubstackFetcher`**:
   * Specifically targets Substack publications (e.g. *Import AI*, *Quantum Zeitgeist*).
   * First attempts standard RSS fetching. If it encounters a 403 Forbidden on server ranges, it retries directly with `feedparser.parse()`.
   * If both fail, it falls back to Substack's native JSON Archive API: `https://<subdomain>.substack.com/api/v1/archive?sort=new&limit=5`.
3. **`NetflixTechBlogFetcher`**:
   * Medium DNS or server settings cause direct requests to `netflixtechblog.com/feed` to timeout.
   * If the base fetch fails, the fetcher retries using the direct Medium-hosted RSS feed: `https://medium.com/feed/netflix-techblog`.
   * If that also fails, it parses the HTML of the Medium homepage (`https://medium.com/netflix-techblog`) using BeautifulSoup to extract article links ending in Medium's unique hex slugs.
4. **`HuggingFacePapersFetcher`**:
   * Hugging Face papers HN feed searches frequently return 0 items.
   * If the feed fails or returns less than 5 entries, it falls back to scraping `https://huggingface.co/papers` directly, parsing article structures to locate paper paths and returning the top 5 papers.

### B. Fetcher Fallback Ingestion Pipeline
Every fetcher runs an automated fallback execution order:
$$\text{Ingestion Pipeline} = \text{RSS Fetch} \longrightarrow \text{RSS Retry} \longrightarrow \text{Homepage Scrape} \longrightarrow \text{Fail}$$

---

## 3. In-Run Substitution and Processing Loop

When `main.py` processes raw articles, it guarantees a clean output pool through strict loop boundaries:

1. **Quota Boundary**: The pipeline enforces a hard limit of `10` successfully analyzed articles.
2. **Failing Substitutions**:
   * If `parse_and_analyze` raises an exception (such as translation or parse failure) or returns `None` (such as articles under 200 characters), the pipeline logs the issue and ignores that article index.
   * If Gemini is unavailable or errors out during extraction, it degrades to fail-safe parameters: `why_it_matters: "Analysis unavailable."`. The pipeline explicitly intercepts these items, logs them, and bypasses adding them to the database.
   * Because `analyzed_count` is only incremented for successful analysis outputs, the pipeline continues processing subsequent articles in the raw pool. A fresh, valid article immediately takes the place of the failed one.
3. **RSS Summary Pre-validation**:
   * Evaluates the summary field of the feed entry.
   * If the summary text is missing or shorter than **200 characters**, the parser automatically crawls the source link using `fetch_article_text` to extract the full body text.
   * If the total text retrieved (summary or crawled body) is still less than **200 characters**, the item is skipped, marked as processed to avoid future reprocessing, and substituted with the next article in the queue.

---

## 4. Gemini API Client Lifecycle & Rotator

The Gemini client manager (`GeminiClientManager`) manages api keys with high resilience:

### A. Environment Configuration Parsing
* Environment variables `GEMINI_API_KEY` and `GEMINI_API_KEYS` are processed concurrently.
* Comma-separated strings are parsed, stripped of whitespaces, filtered of empty entries, and deduplicated while preserving precedence order.

### B. Startup Verification
1. On pipeline launch, the manager prints a startup summary of all loaded keys, masked to show only the first 4 characters (`AQ.A...`).
2. The manager validates each key sequentially by making a test API call to generate `"hello"`.
3. Keys are flagged based on response results:
   * **VALID**: Successful response, or rate limits (`RESOURCE_EXHAUSTED` / `429`). The key remains in the active pool.
   * **INVALID**: Credentials failures (e.g. `API_KEY_INVALID`). The key is immediately stripped from the active pool.

### C. Runtime Rotation Lifecycle
* The pipeline initiates calls using Key #1.
* When encountering a `RESOURCE_EXHAUSTED`, `QUOTA_EXCEEDED`, `429`, or rate limit exception, it interrupts the retry loop immediately.
* It increments the key index, switches to the next verified key, and instantiates a new `genai.Client` connection instance.
* Detailed rotation progression logs are printed to standard output:
  ```text
  [Gemini] Key 1 exhausted
  
  [Gemini] Rotating to key 2/5
  [Gemini] Using key 2/5
  [Gemini] New client created
  ```
* If the active key pool is exhausted, the manager throws a `RuntimeError("All Gemini API keys exhausted")`. This propagates up the pipeline to immediately crash the Daily/Weekly workflows.

---

## 5. UI Architecture & Notifications

* **Relevance Model**: Scoring weights are computed using the formula:
  $$\text{Final Score} = (\text{Signal Score} \times 0.7) + (\text{Adjusted Personal Relevance} \times 0.3)$$
* **HTML Templating**: The Jinja2 generator sorts the items by `final_score` descending, selects the Top 5 items, and outputs a dark-slate/glassmorphism UI featuring custom color indicators matching the technical signal strength.
* **Telegram Bot alerts**: Dispatches details of the day's top insight to a Telegram channel/group, formatting direct links to both the source article and the GitHub Pages deployment site.
