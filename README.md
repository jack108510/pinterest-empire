# 📌 Pinterest Empire Dashboard

Full-stack analytics dashboard for tracking Pinterest performance across all accounts.

## Features

- **Empire-wide KPIs** — Total impressions, engagements, outbound clicks, saves, and audience across all accounts
- **Per-account breakdown** — 30-day metrics with % change for each Pinterest account
- **Daily posting tracker** — Real-time pin counts vs. 100/day target with progress bars
- **Auto-refresh** — Dashboard data refreshes every 5 minutes; analytics fetched daily via cron

## Architecture

```
fetch_all_analytics.py    # Playwright scraper → JSON data
dashboard/
  server.js               # Node.js API server (port 3007)
  public/
    index.html            # Dashboard UI
    styles.css            # Dark theme styles
    app.js                # Frontend logic
  data/                   # Analytics JSON (auto-generated)
```

## Setup

### Prerequisites

- Python 3.14 with Playwright (`pip install playwright && playwright install chromium`)
- Node.js 18+
- Authenticated Pinterest browser sessions (one per account)

### Running

1. **Fetch analytics data:**
   ```bash
   python3.14 fetch_all_analytics.py
   ```

2. **Start the dashboard server:**
   ```bash
   cd dashboard && node server.js
   ```

3. **Open the dashboard:**
   ```
   http://localhost:3007
   ```

### Daily Auto-Refresh

Add to crontab:
```bash
# Fetch analytics at 6:00 AM daily
0 6 * * * cd /path/to/pinterest && /opt/homebrew/bin/python3.14 fetch_all_analytics.py >> logs/analytics-fetch.log 2>&1
```

## Configuration

Edit `accounts.json` to add/remove Pinterest accounts:

```json
{
  "id": "account-name",
  "name": "Display Name",
  "session_path": "~/.pinterest-session-name",
  "enabled": true,
  "boards": ["board1"],
  "products": ["product1"]
}
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/summary` | All account metrics combined |
| `GET /api/account/:id` | Single account details |
| `GET /api/posting-stats` | Today's pin counts per account |
| `GET /api/accounts` | Account configuration list |
