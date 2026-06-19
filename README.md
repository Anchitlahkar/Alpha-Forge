# 🧠 Alpha-Forge Intelligence

An automated, high-signal intelligence platform designed to cut through the noise. It gathers the latest developments in Finance, AI, Quantum Computing, Semiconductors, and Engineering, processes them using Gemini 2.5, and delivers a curated dashboard and Telegram alerts.

## 🚀 Features
- **Automated Discovery:** Fetches from RSS feeds and blogs across 7 strategic technology domains.
- **AI-Powered Analysis:** Uses **Gemini 2.5 Flash** for fact extraction, TLDR generation, and signal scoring.
- **Semantic Deduplication:** Merges overlapping stories into unified events using LLM-based clustering.
- **Relevance Ranking:** Scores insights based on a custom weighted model (Signal × 0.7 + Personal Relevance × 0.3).
- **Weekly Deep Dives:** Uses **Gemini 2.5 Pro** to synthesize a week's worth of data into a strategic report.
- **Zero-Cost Deployment:** Runs entirely on GitHub Actions with hosting on GitHub Pages.
- **Real-time Alerts:** Sends the top daily insight directly to your Telegram.

## 🛠️ Tech Stack
- **Language:** Python 3.12
- **LLM:** Google Gemini 2.5 Flash & Pro
- **Automation:** GitHub Actions
- **Storage:** Flat JSON files (Git-based history)
- **Frontend:** HTML5/CSS3 (Jinja2 Templates)
- **Notifications:** Telegram Bot API

## 📋 Setup & Installation

### 1. Prerequisites
- A Google AI Studio API Key ([Get it here](https://aistudio.google.com/))
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- A GitHub repository for hosting.

### 2. Local Installation
```bash
git clone <your-repo-url>
cd Alpha-Forge
./setup.sh
```

### 3. Environment Configuration
Edit the `.env` file:
```env
GEMINI_API_KEY=your_key
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_id
PAGES_URL=https://anchitlahkar.github.io/Alpha-Forge/dashboard/
```

### 4. GitHub Secrets
For automation, add these as **GitHub Actions Secrets**:
- `GEMINI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## 📁 Repository Structure
```text
Alpha-Forge/
├── .github/workflows/    # CI/CD (Daily/Weekly runs)
├── src/                  # Core Python logic
├── templates/            # HTML/CSS UI
├── dashboard/            # Generated site (GH Pages root)
├── data/                 # JSON archives
├── config/               # Feeds and scoring weights
└── tests/                # Unit tests
```

## ⚖️ License
MIT License - See LICENSE for details.
