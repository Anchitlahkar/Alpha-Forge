# 🧠 Alpha-Forge Intelligence Platform

An automated, highly resilient, high-signal intelligence platform designed to cut through the noise. It gathers the latest developments across strategic technology domains, processes them using a smart Google Gemini API key-rotating manager, filters and ranks them according to relevance, and delivers a curated dashboard and Telegram alerts.

## 🚀 Features

- **Automated Ingestion:** Polls high-signal RSS feeds and blogs across Finance, AI, Quantum Computing, Semiconductors, Software Engineering, and Startups.
- **Token Optimization & Reduction:**
  - Prefers RSS summaries over crawling complete articles, reducing prompt sizes by 70%-90%.
  - Enforces a hard cap of `MAX_ARTICLES_PER_RUN = 10` to conserve Gemini API limits.
  - Skips duplicate URLs within the same run.
  - Excludes articles with content shorter than 200 characters.
  - Bypasses already processed articles using a persistent history database stored in `data/processed_urls.json`.
- **Intelligent API Key Rotation (Resilience):**
  - Allows entering multiple Gemini keys under the `GEMINI_API_KEYS` variable.
  - Automatically switches keys when encountering `RESOURCE_EXHAUSTED`, `QUOTA_EXCEEDED`, `429`, or rate limit errors.
  - Logs transition progress in detail.
  - Continues pipeline execution gracefully even if all keys fail.
- **Semantic Deduplication:** Merges overlapping stories into unified events using LLM-based clustering.
- **Relevance Ranking:** Scores and ranks insights based on a custom weighted model: `(Signal × 0.7) + (Personal Relevance × 0.3)`.
- **Enhanced Structured Output:** Utilizes Pydantic schemas to validate LLM outputs across 11 fields. Employs `repair_json` to automatically resolve trailing commas, unescaped newlines in JSON strings, and unbalanced brackets.
- **Fail-Safe Mode:** Ensures the pipeline never crashes and prevents empty dashboards. If Gemini is unavailable, it automatically degrades gracefully, showing standard cards marked as `Analysis unavailable.` with the original link.
- **Premium Dark UI Dashboard:** Features a modern Outfit-typography design, interactive HSL gradients, glassmorphism cards, sorted descending by final score, displaying the daily top 5 insights.
- **Real-Time Telegram Alerts:** Formats the day's top insight with direct read links and dashboard links.

---

## 🛠️ Tech Stack

- **Language:** Python 3.12
- **LLM:** Google Gemini 2.5 Flash & Pro (Google GenAI SDK)
- **Automation:** GitHub Actions
- **Storage:** Flat JSON files (Git-based history)
- **Frontend:** Jinja2 templates, HTML5, Vanilla CSS3 (Modern dark-slate/glassmorphism design)
- **Notifications:** Telegram Bot API

---

## 📋 Setup & Installation

### 1. Prerequisites
- One or more Google AI Studio API Keys ([AI Studio Console](https://aistudio.google.com/))
- A Telegram Bot Token and Chat ID ([@BotFather](https://t.me/botfather))
- A GitHub repository for hosting the output on GitHub Pages.

### 2. Local Installation
```bash
git clone <your-repo-url>
cd Alpha-Forge
./setup.sh
```

### 3. Environment Configuration
Create or edit the `.env` file in the root directory:
```env
# Enter a single key or comma-separated keys for automatic rotation:
GEMINI_API_KEYS=key_1,key_2,key_3,key_4
GEMINI_API_KEY=fallback_key

TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
PAGES_URL=https://yourusername.github.io/Alpha-Forge/dashboard/
```

### 4. GitHub Secrets
For automatic cron execution, add these as **GitHub Actions Secrets**:
- `GEMINI_API_KEYS`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

---

## 📁 Repository Structure
```text
Alpha-Forge/
├── .github/workflows/    # CI/CD pipelines (Daily/Weekly workflow crons)
├── src/                  # Python implementation files
│   ├── config.py         # Config loading (API keys, Telegram, feeds, scoring)
│   ├── gemini_client.py  # Rotation client, JSON repair, LLM schemas, weekly deep dives
│   ├── fetch_sources.py  # RSS parsing & BeautifulSoup crawling fallback
│   ├── article_parser.py # Content filters, summary preferences, fail-safe fallbacks
│   ├── deduplicate.py    # Semantic LLM grouping
│   ├── relevance_ranker.py# Custom personal-weighted ranking calculation
│   ├── dashboard_generator.py# Daily/weekly HTML rendering
│   ├── telegram_alert.py # Formatted notification dispatch
│   └── utils.py          # IO helpers, processed URL registry
├── templates/            # HTML/CSS Jinja templates
├── dashboard/            # Target deployment directory (GitHub Pages root)
├── data/                 # JSON archive folders and processed_urls.json
├── config/               # Scoring coefficients and RSS feed lists
└── tests/                # Pipeline test suite
```

---

## ⚖️ License
MIT License - See LICENSE for details.
