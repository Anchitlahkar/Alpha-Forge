# 🧠 Alpha-Forge Intelligence Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Google Gemini API](https://img.shields.io/badge/Gemini-2.5%20Pro%2FFlash-brightgreen.svg)](https://aistudio.google.com/)
[![CI/CD Pipeline](https://img.shields.io/badge/GitHub%20Actions-Daily%2FWeekly%20Cron-orange.svg)](https://github.com/features/actions)

**Alpha-Forge** is an automated, highly resilient, personal intelligence platform designed to cut through the information noise. The system automatically ingests recent articles and research papers from hand-curated, high-signal feeds across strategic technology and financial domains. It processes these entries using an intelligent API key-rotating manager, performs semantic deduplication, scores them against custom category weights, and generates a front-page-style dashboard along with instant Telegram alerts for the day's top insight.

---

## 📖 Table of Contents
1. [🚀 Core Features](#-core-features)
2. [⚙️ System Architecture](#️-system-architecture)
3. [🛠️ Tech Stack](#️-tech-stack)
4. [📁 Repository Structure](#-repository-structure)
5. [📋 Configuration & Environment Variables](#-configuration--environment-variables)
6. [🔧 Local Setup & Run Guide](#-local-setup--run-guide)
7. [⚙️ GitHub Actions & Pages Automation Guide](#️-github-actions--pages-automation-guide)
8. [🧪 Testing & Quality Assurance](#-testing--quality-assurance)
9. [⚖️ License](#️-license)

---

## 🚀 Core Features

- **📡 Resilient Source Ingestors:**
  - Standard RSS parsing using `feedparser` with active retry fallbacks.
  - **Substack Ingestor:** Custom fallback mapping to Substack's native JSON Archive API when Cloudflare blocks RSS requests.
  - **Medium/Netflix Ingestor:** Automatic fallback from custom blog domains to Medium feed paths or homepage scraper parsing hex slugs.
  - **Hugging Face Papers Ingestor:** Scrapes direct DOM listings when arXiv search indices are delayed.
- **💸 Token & Cost Optimization:**
  - Analyzes RSS summaries directly to reduce token usage by **70% to 90%** compared to parsing full web pages.
  - Triggers the full page body crawler (`BeautifulSoup` parser) only if feed summaries are missing or shorter than **200 characters**.
  - Limits daily pipeline runs to a maximum of `10` successfully analyzed articles.
  - Skips duplicate URLs within the current run and cross-checks historical records using `data/processed_urls.json`.
- **🔑 Key Rotation & Client Resilience:**
  - Extracts and deduplicates API keys from environment variables.
  - Validates keys lazily, on first real use, so no quota is spent before any work begins.
  - Catches rate limit errors (`429`, `RESOURCE_EXHAUSTED`) at runtime and rotates keys automatically, honouring the `retryDelay` the API returns.
  - Distinguishes per-minute throttling from per-day exhaustion: throttled keys cool down individually and are reused, so the run survives a burst of rate limits instead of ending at the last key. Keys out of daily quota, or rejected as invalid, are retired for the run.
  - Waits for the soonest key to recover when every key is throttled, capped at a cumulative 5 minutes, then stops the run with a `RuntimeError` if nothing can recover.
- **🔧 JSON Repair & Validation:**
  - Cleans and fixes malformed JSON formatting returned by LLMs (e.g. unescaped newlines, trailing commas, or missing brackets).
  - Validates structured outputs against Pydantic schemas: `ArticleAnalysis`, `DeduplicationItem`, and `DeduplicationResponse`.
- **🧠 Semantic Deduplication:**
  - Groups articles reporting on the same event and consolidates their summaries and source URLs.
- **📊 Custom Relevance Scoring:**
  - Computes weighted scores from three explicit terms: `(Signal * 0.7) + (Personal Relevance * 0.15) + (Category Weight * 0.15)`, all tunable in `config/scoring.json`.
  - Resolves the free-text category Gemini returns onto the configured category keys (exact, then containment, then token overlap) and logs anything it cannot place, so category weights are not silently discarded.
- **🎨 Front-Page Dashboard:**
  - Renders a newspaper-style layout in Archivo using Jinja2 templates: the lead story takes the headline and its score, items 2-3 share a divided band, and the rest collapse to ruled rows, so the ranking is legible without reading.
  - Shows the day's top 5 in full and lists everything else that cleared the filter exactly once, never repeating an article between sections.
  - Falls back to the most recent archive with content, clearly marked stale, if a run returns nothing, rather than publishing an empty page.
- **📢 Real-Time Telegram Alerts:**
  - Dispatches details of the day's top insight to a Telegram channel, complete with direct read links and Pages URLs.

---

## ⚙️ System Architecture

```text
[Feeds List JSON] ─────► [Fetch Sources Ingestion] ─────► [Article Processing Loop]
                                                                  │
                                                                  ▼
[Daily HTML Dashboard] ◄─── [Scoring & Filtering] ◄─── [Key Rotation Client Manager]
          │
          ├───────────────────────────────┐
          ▼ (Commit & Deploy)             ▼ (Alert Dispatch)
   [GitHub Pages]                [Telegram Messenger]
```

### Technical Workflow Stages
1. **Source Ingestion:** The pipeline queries the sources defined in `config/feeds.json`.
2. **Text Parsing & Filtering:** Crawls full page contents only if the summary is shorter than 200 characters. Articles under 200 characters are skipped.
3. **Structured Analysis:** Analyzes content using Gemini 2.5 Flash. If a key is rate-limited, the system automatically rotates keys and retries.
4. **Semantic Deduplication:** Groups articles covering the same event and merges their metadata.
5. **Relevance Scoring:** Computes final scores using category weights and excludes items below the signal threshold.
6. **Dashboard Generation:** Generates the dashboard files using Jinja2 templates and saves daily run outputs to `data/daily/`.
7. **Telegram Dispatch:** Posts the highest-ranking daily insight to a Telegram channel.
8. **Automated Commit:** Commits data updates to the repository and deploys the dashboard output directory to the `gh-pages` branch.

---

## 🛠️ Tech Stack

- **Primary Language:** Python 3.12
- **Core LLM APIs:** Google Gemini 2.5 Flash & Gemini 2.5 Pro (via `google-genai` SDK)
- **HTML Template Engine:** Jinja2
- **Markup Parser:** Markdown-it / Markdown python library
- **JSON Validation:** Pydantic v2
- **Scraping Libraries:** `BeautifulSoup4`, `feedparser`, and `requests`
- **Automation Host:** GitHub Actions Workflows
- **Hosting Target:** GitHub Pages
- **Alert Target:** Telegram Bot API

---

## 📁 Repository Structure

```text
Alpha-Forge/
├── .github/
│   └── workflows/
│       ├── daily.yml         # Daily run schedule configuration (7:00 AM IST)
│       └── weekly.yml        # Weekly synthesis run schedule (Sunday 9:00 AM UTC)
├── config/
│   ├── feeds.json            # Target RSS sources categorized by domain
│   └── scoring.json          # Target relevance weights and category ratings
├── dashboard/
│   └── index.html            # Target generated dashboard page (GitHub Pages root)
├── data/
│   ├── daily/                # JSON logs of daily intelligence runs
│   ├── weekly/               # Markdown files of generated weekly synthesis reports
│   └── processed_urls.json   # Flat JSON database tracking processed articles
├── src/
│   ├── config.py             # Config parser, environment variables loader, and path manager
│   ├── fetch_sources.py      # Resilient feed adapters and homepage scraper fallbacks
│   ├── article_parser.py     # Crawl triggers, pre-validation filters, and fail-safe mappings
│   ├── gemini_client.py      # LLM client builder, key rotator, and JSON repair engine
│   ├── deduplicate.py        # Semantic group clustering using Gemini Flash
│   ├── relevance_ranker.py   # Category weights loader and weighted score calculator
│   ├── signal_filter.py      # Signal threshold filter (excludes items with score < 5)
│   ├── archive_manager.py    # Gathers daily outputs and writes to JSON logs
│   ├── weekly_synthesis.py   # Aggregates daily logs and prompts Gemini Pro for deep dives
│   ├── dashboard_generator.py# Populates Jinja2 templates and writes generated HTML to paths
│   ├── telegram_alert.py     # Dispatches markdown alert messages to the Telegram Bot API
│   ├── utils.py              # File I/O helpers, datetime functions, and URL registry database
│   └── main.py               # Main execution router for daily and weekly schedules
├── templates/
│   ├── dashboard.html        # Front-page HTML layout template (all styles inlined)
│   └── styles.css            # Base stylesheet rules
├── tests/
│   ├── test_dedup.py         # Unit tests checking deduplication boundaries
│   ├── test_key_rotation.py  # Unit tests for key cooldown, wraparound, and quota classification
│   ├── test_parser.py        # Unit tests for processed-URL keying and fail-safe behaviour
│   ├── test_ranker.py        # Unit tests validating weighted ranking calculations
│   └── test_telegram_logic.py# Unit tests mocking outgoing telegram notification requests
├── requirements.txt          # Python library dependencies
├── setup.sh                  # Virtualenv setup and environment copying script
└── Working.md                # Exhaustive system architecture reference manual
```

---

## 📋 Configuration & Environment Variables

Create a `.env` file in the project root to configure the environment:

| Environment Variable | Description | Example / Required Format |
|---|---|---|
| `GEMINI_API_KEYS` | Comma-separated list of Gemini API Keys for rotation. | `AIzaSyA1...,AIzaSyB2...` |
| `GEMINI_API_KEY` | Fallback single Gemini key. | `AIzaSyC3...` |
| `TELEGRAM_BOT_TOKEN` | Bot API token generated from BotFather. | `123456789:ABCdefGhIJK...` |
| `TELEGRAM_CHAT_ID` | Telegram chat/channel ID where notifications are sent. | `-100123456789` |
| `PAGES_URL` | Base URL pointing to your GitHub Pages dashboard. | `https://username.github.io/Alpha-Forge/dashboard/` |

---

## 🔧 Local Setup & Run Guide

### 📋 Prerequisites
- Python 3.12 installed on your machine.
- At least one Google AI Studio API key.

### 🛠️ Execution Steps

1. **Clone the Repository:**
   ```bash
   git clone <your-repo-url>
   cd Alpha-Forge
   ```

2. **Initialize Environment & Dependencies:**
   ```bash
   # Run the bash setup script (configures venv, installs requirements, and copies template .env)
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Configure Environment Keys:**
   Open `.env` in the root folder and add your configuration credentials.

4. **Execute the Python App:**
   - Run the daily pipeline:
     ```bash
     python src/main.py
     ```
   - Run the weekly synthesis:
     ```bash
     python src/main.py --weekly
     ```

5. **Preview the Dashboard Interface:**
   Start a local Python server to preview the generated dashboard interface:
   ```bash
   python -m http.server 8000 --directory dashboard
   ```
   Open `http://localhost:8000` in your web browser.

---

## ⚙️ GitHub Actions & Pages Automation Guide

To automate and host the intelligence platform on GitHub, follow the steps below:

### Step 1: Push Code to a New GitHub Repository
Create a new GitHub repository and push your local codebase to it:
```bash
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git branch -M main
git push -u origin main
```

### Step 2: Configure Repository Secrets
Safely configure your credentials as repository secrets:
1. Go to repository home -> **Settings** -> **Secrets and variables** -> **Actions**.
2. Click **New repository secret** and add the following keys:
   * `GEMINI_API_KEY` (or `GEMINI_API_KEYS`): Paste your comma-separated list of Gemini keys.
   * `TELEGRAM_BOT_TOKEN`: Paste your Telegram bot token.
   * `TELEGRAM_CHAT_ID`: Paste your target group/channel chat ID.

### Step 3: Configure Workflow Write Permissions
The pipeline commits updated historical files and generated dashboard HTML back to your repository. This requires read/write workflow permissions:
1. Go to repository **Settings** -> **Actions** -> **General**.
2. Scroll to the bottom and select **"Read and write permissions"** under *Workflow permissions*.
3. Check the box **"Allow GitHub Actions to create and approve pull requests"**.
4. Click **Save**.

### Step 4: Configure GitHub Pages Deployment
The automated daily run uses `peaceiris/actions-gh-pages@v3` to build and deploy the dashboard files to a branch named `gh-pages`:
1. Go to repository **Settings** -> **Pages**.
2. Under **Build and deployment**:
   * **Source**: Select **Deploy from a branch**.
   * **Branch**: Set the target branch to **`gh-pages`** (this branch is created automatically after the first pipeline run) and directory path to **`/ (root)`**.
3. Click **Save**.

### Step 5: Run the Action Manually
1. Go to the **Actions** tab of the repository.
2. Select **Daily Intelligence Run** from the workflows list in the left sidebar.
3. Click the **Run workflow** dropdown on the right and select the `main` branch.
4. Click **Run workflow** to verify execution and trigger the dashboard build.

---

## 🧪 Testing & Quality Assurance

The codebase includes unit tests to validate core components like ranking logic, deduplication limits, and Telegram API requests.

Run the test suite using unittest:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

### Test Coverage Details:
- [test_dedup.py](tests/test_dedup.py): Verifies semantic grouping boundaries and empty/single-item handling.
- [test_ranker.py](tests/test_ranker.py): Verifies category-weighted score ordering.
- [test_key_rotation.py](tests/test_key_rotation.py): Verifies per-key cooldown and wraparound, `retryDelay` parsing, per-day vs per-minute quota classification, and that startup spends no API requests. Runs against a fake clock and a stubbed SDK, so it makes no network calls.
- [test_parser.py](tests/test_parser.py): Verifies that a failed analysis does not blacklist a URL, and that the same URL can still deliver a different article.
- [test_telegram_logic.py](tests/test_telegram_logic.py): Mocks request dispatch behaviors and verifies formatting layouts.

---

## ⚖️ License

Alpha-Forge is open-source software licensed under the [MIT License](LICENSE).
