# 🏗️ System Architecture & Working Logic

This document provides a deep dive into how the Personal Intelligence System operates, from ingestion to delivery.

## 1. High-Level Architecture
The system follows a linear pipeline architecture, triggered by cron jobs (GitHub Actions).

```text
[Sources] -> [Fetch & Parse] -> [Gemini Extraction] -> [Deduplication] -> [Ranking] -> [Synthesis] -> [Delivery]
```

## 2. Core Pipeline Components

### A. Content Ingestion (`fetch_sources.py` & `article_parser.py`)
- **RSS Aggregation:** Polls high-signal RSS feeds defined in `config/feeds.json`.
- **Full-Text Extraction:** Uses `BeautifulSoup4` with custom headers to bypass simple bot detection and extract the core article body, stripping away navigation, ads, and scripts.
- **Classification:** Initial categorization is based on the source feed domain.

### B. Intelligent Processing (`gemini_client.py`)
The system employs a dual-model strategy:
- **Gemini 2.5 Flash:** Used for high-volume daily tasks (Fact extraction, TLDR, classification validation). It provides low-latency, structured JSON output via Pydantic schemas.
- **Gemini 2.5 Pro:** Reserved for the **Weekly Deep Dive**. It analyzes the cumulative data from the week to identify "cross-cutting" trends that aren't visible in individual daily reports.

### C. Semantic Deduplication (`deduplicate.py`)
Unlike simple hash-based deduping, this system uses **LLM Semantic Clustering**.
1. It sends the titles and summaries of all daily articles to Gemini.
2. Gemini identifies which articles discuss the same underlying event (e.g., "Nvidia Earnings" reported by 5 different blogs).
3. The system merges these into a single "Insight" but retains all source URLs for reference.

### D. The Relevance Model (`relevance_ranker.py`)
Insights are ranked using a composite score:
- **Signal Score (LLM Generated):** How much *new* information or technical depth is in the piece (1-10).
- **Personal Relevance:** Based on category weights defined in `config/scoring.json`.
- **Formula:** `(Signal * 0.7) + (Personal_Relevance * 0.3)`

## 3. Monitored Content Sources

The system is configured to monitor the following high-signal sources:

### 📈 Finance & Economics
- **Net Interest:** Deep dives into financial sector themes.
- **The Diff:** Info-dense analysis of inflections in tech and finance.
- **Apricitas Economics:** Data-driven macroeconomic insights.

### 🤖 Artificial Intelligence
- **Import AI (Jack Clark):** Policy and technical research summaries.
- **Ahead of AI (Sebastian Raschka):** Latest breakthroughs in ML and LLMs.
- **Hugging Face Papers:** Daily trending research papers.

### ⚛️ Quantum Computing
- **arXiv quant-ph:** Raw academic research pre-prints.
- **Quantum Software Engineering:** Newsletter focused on the quantum stack.

### 💻 Software Engineering
- **Pragmatic Engineer:** Market trends and engineering leadership.
- **Netflix Tech Blog:** High-scale infrastructure and culture.
- **Cloudflare Blog:** Networking, security, and edge computing.
- **Stripe Engineering:** Payment systems and platform reliability.

### 🔌 Semiconductors
- **SemiAnalysis:** In-depth supply chain and hardware architecture analysis.

### 🚀 Startups & Strategy
- **Stratechery (Ben Thompson):** Business strategy and tech ecosystems.

## 4. Automation & Deployment

### Daily Workflow (`daily.yml`)
- Runs at **08:00 UTC**.
- Fetches sources, generates the `dashboard/index.html`, and commits the JSON archive to the repo.
- Deploys the result to **GitHub Pages**.
- Sends a **Telegram Alert** with the #1 ranked insight.

### Weekly Workflow (`weekly.yml`)
- Runs every **Sunday at 09:00 UTC**.
- Aggregates the last 7 days of JSON files.
- Uses Gemini 2.5 Pro to write a high-level strategic overview.
- Re-generates the dashboard to include the "Weekly Deep Dive" section.

## 5. Data Integrity & Error Handling
- **JSON Validation:** The system uses Pydantic to enforce Gemini's output format.
- **Retry Logic:** If Gemini returns invalid JSON or fails, the system attempts up to 3 retries with exponential backoff.
- **Signal Filtering:** Any insight with a Signal Score < 5 is automatically discarded to keep the dashboard fluff-free.
