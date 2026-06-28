# US & Hong Kong Value Screener

Screens US and HK stocks using the same value logic:

| Filter | Threshold |
|--------|-----------|
| Forward P/E | < 8 |
| P/B | < 0.8 |
| Dividend yield | > 5% |
| Sort | Lowest forward P/E first |

The **Friday Shortlist** (3 quality tiers) refreshes on **Fridays at 7:00 AM US Eastern** (first visit after that time, or manual refresh).

---

## Deploy on Streamlit (recommended)

### Run locally first

```bash
cd value-screener
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Or double-click **`run_streamlit.bat`** → opens **http://localhost:8501**

Use the sidebar: **US Value Screener** | **HK Value Screener**

### Deploy to Streamlit Community Cloud (free)

1. **Push this folder to GitHub** (create a repo, upload `value-screener/` contents).
   - Include `data/screen_results.json` and `data/screen_results_hk.json` (seed data).
   - Do **not** ignore the `data/` folder in `.gitignore`.

2. Go to **[share.streamlit.io](https://share.streamlit.io)** → Sign in with GitHub.

3. Click **New app** and set:
   | Field | Value |
   |-------|-------|
   | Repository | `your-user/value-screener` |
   | Branch | `main` |
   | Main file path | `streamlit_app.py` |

4. Click **Deploy**. First boot takes ~2–3 minutes.

5. Your public URL will look like:  
   `https://your-app-name.streamlit.app`

### Streamlit notes

- **Refresh button** on each page re-scrapes live data (US ~2 min, HK ~3–5 min).
- **Friday auto-refresh** runs on the first page visit after Friday 7:00 AM US Eastern.
- Streamlit Cloud has **no persistent disk** across redeploys — seed JSON in the repo keeps the app working on cold start; use **Refresh data** for live updates.
- Finviz may rate-limit cloud IPs — if US refresh fails, retry or run `python seed_data.py` locally and push updated JSON to GitHub.

---

## Flask version (local alternative)

## Quick start (Windows — easiest)

**Double-click `start.bat`** in the `value-screener` folder.  
It installs dependencies, seeds data if needed, starts the server, and **opens your browser automatically**.

Keep the black terminal window open while using the site.

## Quick start (manual)

```bash
cd value-screener
pip install -r requirements-flask.txt
python seed_data.py          # first time only
python run.py
```

The browser opens automatically at **http://127.0.0.1:5000**

**Hong Kong page:** **http://127.0.0.1:5000/hk** (or use the header tabs)

If the page does not load, port 5000 may be busy — the server will try **5001** instead. Check the terminal for the exact URL.

**Port stuck?** Close old servers:
```powershell
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
```
Then run `start.bat` again.

## Manual refresh

- Click **↻ Refresh** in the browser (scrapes Finviz, ~2 minutes)
- Or: `curl -X POST http://localhost:5000/api/refresh`

## API

| Endpoint | Description |
|----------|-------------|
| `GET /api/data` | Full screener JSON (results + shortlist + near misses) |
| `GET /api/status` | Last updated, next refresh, refreshing flag |
| `POST /api/refresh` | Trigger background Finviz scrape |
| `GET /hk` | Hong Kong screener page |
| `GET /api/hk/data` | HK screener JSON |
| `POST /api/hk/refresh` | Refresh HK data (StockAnalysis) |

## Hong Kong page

Same filters as US (Fwd P/E &lt; 8, P/B &lt; 0.8, Div &gt; 5%). Data sourced from [StockAnalysis HKEX list](https://stockanalysis.com/list/hong-kong-stock-exchange/) — Finviz does not cover HK listings.

Seed HK data: `python seed_hk_data.py` (~3 min first run)

## Project layout

```
value-screener/
  app/
    config.py          # Filter thresholds, tier lists, schedule
    main.py            # Flask routes
    scheduler.py       # APScheduler Friday job
    storage.py         # JSON cache read/write
    screener/
      engine.py        # Finviz scraper + filters
      tiers.py         # Tier 1/2/3 classification
  data/
    screen_results.json
  static/              # CSS + JS
  templates/           # index.html
  run.py
  seed_data.py
```

## Production deployment

For a public site, run behind **gunicorn** or **waitress** and keep the process alive so the Friday scheduler runs:

```bash
pip install waitress
waitress-serve --host=0.0.0.0 --port=5000 "app.main:create_app"
```

On Linux, you can also add a system cron as backup:

```cron
0 7 * * 5 cd /path/to/value-screener && python -c "from app.storage import refresh_screen; refresh_screen(force=True)"
```

## Disclaimer

Research tool only — not investment advice. Data from Finviz; verify before trading.