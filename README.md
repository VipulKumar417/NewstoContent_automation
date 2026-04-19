# EpiCred AI Content Automation Tool

AI-powered content pipeline for [EpiCred](https://epicred.in):  
**Trending News → Gemini AI → 6 Social Formats → Google Drive + Calendar**

---

## Phase Build Status

| Phase | Status       | Description                          |
|-------|--------------|--------------------------------------|
| 1     | ✅ Complete  | Setup, News Ingestion, Dashboard     |
| 2     | ⏳ Pending   | Trend Analyzer (Gemini scoring)      |
| 3     | ⏳ Pending   | Content Generator (6 platforms)      |
| 4     | ⏳ Pending   | Google Drive + Calendar integration  |
| 5     | ⏳ Pending   | Dashboard UI (full wiring)           |
| 6     | ⏳ Pending   | APScheduler automation               |
| 7     | ⏳ Pending   | Testing & Polish                     |

---

## Quick Start

### 1. Prerequisites
- Python 3.11+
- API keys: Gemini, NewsData.io, GNews
- Google Cloud project with Drive + Calendar APIs enabled

### 2. Setup

```bash
# Clone & enter the project
cd epicred-content-bot

# Create virtual environment
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env and fill in your real API keys
```

### 3. Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → enable **Google Drive API** and **Google Calendar API**
3. Create OAuth 2.0 credentials → download as `credentials.json`
4. Place `credentials.json` in the project root

### 4. Run the Dashboard

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## API Keys Required

| Service         | Where to Get                     | Free Tier         |
|-----------------|----------------------------------|-------------------|
| Gemini API      | aistudio.google.com              | 15 RPM / 1M TPM   |
| NewsData.io     | newsdata.io                      | 200 req/day       |
| GNews           | gnews.io                         | 100 req/day       |
| Google Drive    | console.cloud.google.com         | Free              |
| Google Calendar | console.cloud.google.com         | Free              |

---

## Folder Structure

```
epicred-content-bot/
├── app.py               # Flask entry point
├── config.py            # All settings & constants
├── .env                 # Your secrets (never commit!)
├── requirements.txt
├── pipeline/
│   ├── news_fetcher.py  # NewsData.io + GNews + RSS
│   ├── trend_analyzer.py        # Phase 2
│   ├── content_generator.py     # Phase 3
│   ├── repurposer.py            # Phase 3
│   └── scheduler.py             # Phase 6
├── integrations/
│   ├── auth.py          # OAuth 2.0          Phase 4
│   ├── google_drive.py  # Drive + Docs API   Phase 4
│   └── google_calendar.py  # Calendar API    Phase 4
├── storage/
│   ├── news_cache.json  # Latest fetched news
│   ├── content_library/ # Generated JSON bundles
│   └── logs/
├── dashboard/
│   ├── templates/index.html
│   └── static/
│       ├── style.css
│       └── app.js
└── prompts/             # Gemini prompt templates (Phase 3)
```
