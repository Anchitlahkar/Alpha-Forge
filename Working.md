# 🏗️ Alpha-Forge Architecture & Pipeline Processing Logic

This document provides a comprehensive technical walkthrough of how the **Alpha-Forge** Intelligence System operates across all phases of ingestion, analysis, filtering, deduplication, ranking, layout generation, and notification dispatch.

---

## 1. High-Level Architecture Pipeline

Alpha-Forge operates as a linear processing pipeline triggered by time-based crons (via GitHub Actions). The pipeline stages are executed as follows:

```text
[Feeds List]
     |
     v
[RSS Aggregator] ---> [Length Filter & Seen Check]
                             |
                             v
                    [Summary Extraction] (Fallback: Full Page Crawl)
                             |
                             v
                    [Gemini API Client] <---> [Client Key Rotator]
                             |
                             v
                    [JSON Repair Engine]
                             |
                             v
                    [Pydantic Validation]
                             | (On Failure/Exhaustion)
                             +-------------------------> [Fail-Safe Fallback Model]
                             |
                             v
                    [Deduplication Stage]
                             |
                             v
                    [Score & Category Ranker]
                             |
                             v
                    [Dashboard HTML Render] ---> [Telegram Notification Dispatch]
```

---

## 2. Pipeline Components & Implementation Details

### A. Ingestion and Pre-Filtering (`fetch_sources.py` & `article_parser.py`)
1. **Aggregated Sources**: The pipeline reads feeds from `config/feeds.json` classified under Finance, AI, Quantum, Engineering, Semiconductors, and Startups.
2. **Duplication Filter**: The pipeline maintains two layers of URL filtering:
   - **Current Run Deduplication**: Tracks unique links in the current execution loop using an in-memory set (`seen_urls`).
   - **Historical Registry**: Loads processed URLs from `data/processed_urls.json` to prevent reprocessing articles analyzed in previous runs.
3. **Summary Preference (Token Saving)**:
   - Evaluates the RSS feed's summary first.
   - If present, it bypasses the article crawler entirely, saving 70% to 90% in token ingestion costs.
   - If the summary is absent, it calls a BeautifulSoup4 parser (`fetch_article_text`) using spoofed user-agent headers to scrape the main page content, discarding scripts, styles, and markup.
4. **Length Constraint**: If the extracted text content is shorter than **200 characters**, the article is skipped to ignore short stub updates.

---

### B. Gemini Client Manager & Key Rotation (`gemini_client.py`)
1. **Multi-Key Setup**: Allows setting multiple API keys via the `GEMINI_API_KEYS` env variable (comma-separated).
2. **Automatic Failover**:
   - The pipeline initiates calls using Key #1.
   - If an API call fails due to `RESOURCE_EXHAUSTED`, `QUOTA_EXCEEDED`, `429`, or rate limit messages, the manager switches to Key #2, Key #3, and so on.
   - Rotation activity is logged in the following format:
     ```text
     [Gemini]
     Using Key #1
     
     [Gemini]
     Key #1 exhausted
     
     [Gemini]
     Switching to Key #2
     ```
3. **Hard Cap**: Processes a maximum of **10 articles** per daily run (`MAX_ARTICLES_PER_RUN = 10`) to control token consumption.

---

### C. JSON Repair Engine & Validation (`gemini_client.py`)
Before passing the generated response text to Pydantic, the raw text is cleaned using the `repair_json` function:
1. Strips markdown block qualifiers (` ```json ` and ` ``` `).
2. Isolates the outermost braces (finds the first `{` and last `}`) to remove peripheral conversational commentary.
3. Fixes trailing commas inside lists or dictionary structures via regex replacement: `re.sub(r',\s*([\]}])', r'\1', text)`.
4. Standardizes unescaped newline characters within string literals.
5. Balances unmatched brackets/braces to prevent JSON syntax parser faults.
6. The cleaned string is validated using Pydantic's `ArticleAnalysis` schema, representing 11 required fields:
   ```json
   {
     "title": "string",
     "category": "string",
     "signal_score": 0.0,
     "personal_relevance": 0.0,
     "why_it_matters": "string",
     "tldr": "string",
     "key_points": [],
     "action_items": [],
     "source_name": "string",
     "source_url": "string",
     "date": "string"
   }
   ```

---

### D. Semantic Deduplication (`deduplicate.py`)
1. Simplifies insights by grouping overlapping titles and summaries via a Gemini structural prompt.
2. Identifies stories covering the same underlying event.
3. Blends them into single records, consolidating references into a aggregated list of sources.

---

### E. Scoring and Ranking (`relevance_ranker.py`)
Each insight receives a `final_score` calculated as:
$$\text{Final Score} = (\text{Signal Score} \times 0.7) + (\text{Adjusted Personal Relevance} \times 0.3)$$
Where:
- **Signal Score**: The LLM's assessment of Technical Depth (1-10).
- **Adjusted Personal Relevance**: The average of the LLM's relevance score and the category-specific weight defined in `config/scoring.json`.
- Discards any insight with a `signal_score < 5` to filter out low-signal stories.

---

### F. Failure Recovery & Fail-Safe Mode (`article_parser.py`)
If Gemini becomes unavailable (all keys exhausted or net failure), the pipeline executes a **fail-safe degradation routine**:
- Avoids crashing the pipeline.
- Instantiates fallback mock dictionaries:
  - `why_it_matters`: `"Analysis unavailable."`
  - `tldr`: `"Analysis unavailable."`
  - `key_points`: `[]`
  - `action_items`: `[]`
  - `signal_score` / `personal_relevance`: `5.0` (to bypass the signal score filter threshold).
  - Preserves target article title, source name, original link (`source_url`), and date.
- The pipeline proceeds to generate a dashboard with the remaining content.

---

### G. UI & Dashboard Layout (`templates/dashboard.html`)
The dashboard implements a modern visual design:
- **Dark Theme Palette**: Uses space-blue/gray color tones (`#0B0F19`, `#151B2C`, `#1E2640`).
- **Typography**: Imports the modern `Outfit` font for titles and structured contents.
- **Card Elements**:
  - Displays Category Badges and gradient Signal Score badges.
  - Interactive cards that elevate on hover with border transitions.
  - Distinct sections for **Why It Matters**, **Summary (TLDR)**, **Key Points**, and **Action Items**.
  - Direct "Read Original Article" links leading to the source.
- **Slicing**: Automatically sorts the final cards by `final_score` descending and restricts display to the **Top 5 Insights** of the day.

---

### H. Notifications (`telegram_alert.py`)
Dispatches a Real-Time message for the top-ranked insight of the day in this exact format:
```text
Top Insight:
<title>

Read:
<article_url>

Dashboard:
<dashboard_url>
```
*Note: Validates tokens and chat IDs before dispatching, avoiding crashes if credentials are unset.*
