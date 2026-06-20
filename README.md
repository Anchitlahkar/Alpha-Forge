# 🧠 Alpha-Forge Intelligence Platform

An automated, highly resilient, high-signal intelligence platform designed to cut through the noise. It gathers the latest developments across strategic technology domains, processes them using a smart Google Gemini API key-rotating manager, filters and ranks them according to relevance, and delivers a curated dashboard and Telegram alerts.

---

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

## 📋 Setup & Installation (Local Development)

### 1. Prerequisites
- One or more Google AI Studio API Keys ([AI Studio Console](https://aistudio.google.com/))
- A Telegram Bot Token and Chat ID ([@BotFather](https://t.me/botfather))

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

---

## ⚙️ GitHub Actions & Pages Setup Guide

Follow these steps to deploy and run Alpha-Forge automatically in GitHub:

### Step 1: Create a GitHub Repository
1. Go to [GitHub](https://github.com) and click **New Repository**.
2. Give your repository a name (e.g. `Alpha-Forge`), choose public/private, and click **Create repository**.
3. Push your codebase to the repository:
   ```bash
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git branch -M main
   git push -u origin main
   ```

### Step 2: Configure Repository Secrets
To allow GitHub Actions to safely access your API keys and Telegram credentials, set them up as Secrets:
1. Navigate to your GitHub repository home page.
2. Click on **Settings** (the gear icon on the top tab).
3. In the left sidebar, click on **Secrets and variables** -> **Actions**.
4. Click the **New repository secret** button.
5. Create the following secrets:
   * **`GEMINI_API_KEY`** (or **`GEMINI_API_KEYS`**): Set your comma-separated list of Gemini API keys (e.g. `AIzaSy...,AIzaSy...`).
   * **`TELEGRAM_BOT_TOKEN`**: Set your Telegram Bot Token.
   * **`TELEGRAM_CHAT_ID`**: Set your Telegram Chat or Group ID.
6. Click **Add secret** for each configuration.

### Step 3: Configure Workflow Run Permissions
The daily cron pipeline commits updated JSON data files and dashboard files back to the repository. This requires Read/Write permissions for Actions:
1. Remain in **Settings**.
2. In the left sidebar under *Security*, click on **Actions** -> **General**.
3. Scroll down to the bottom of the page to locate **Workflow permissions**.
4. Change the selection from *Read workflow permissions* to **Read and write permissions**.
5. Check the box **"Allow GitHub Actions to create and approve pull requests"**.
6. Click the **Save** button.

### Step 4: Configure GitHub Pages Deployment
The pipeline builds the frontend dashboard in the `dashboard/` directory and publishes it to a dedicated deployment branch named `gh-pages`:
1. Remain in **Settings**.
2. In the left sidebar, click on **Pages**.
3. Under **Build and deployment**:
   * **Source**: Select **Deploy from a branch**.
   * **Branch**: Set the branch target to **`gh-pages`** (it will be created automatically after the first pipeline run) and the folder to **`/ (root)`**.
4. Click **Save**.

### Step 5: Enable & Trigger the Workflow
1. Go to the **Actions** tab of your repository.
2. If you forked or imported the repository, click the green button **"I understand my workflows, go ahead and enable them"**.
3. Select **Daily Intelligence Run** from the list of workflows on the left sidebar.
4. Click the **Run workflow** dropdown on the right hand side, select the branch (`main`), and click **Run workflow**.
5. Once complete, you will see a `gh-pages` branch created, your telegram group will receive the alert, and your GitHub pages dashboard site (e.g. `https://<your-username>.github.io/<your-repo-name>/dashboard/`) will go live!

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
