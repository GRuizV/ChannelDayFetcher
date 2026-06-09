# Slack Channel Day Fetcher

A lightweight Python tool to fetch, view, and export Slack channel messages for a given date or date range — through a **Streamlit web UI**, an **interactive CLI**, or a **programmatic Python API**.

Originally built to satisfy a real need: pulling all of a single day's conversation out of a Slack channel into a clean, exportable artifact (CSV or JSON) — including threaded replies, file attachments, and human-readable user names — without manually scrolling through Slack.

## Try the demo

A public demo is deployed on Streamlit Cloud — it serves a baked sample conversation (no live Slack token attached), so you can see the full UI, exports, and threading behaviour without setting anything up. **(Live URL will be added after deployment.)**

To run the demo locally instead:

```bash
DEMO_MODE=true streamlit run ui.py     # macOS / Linux
$env:DEMO_MODE="true"; streamlit run ui.py     # Windows PowerShell
```

To run against your own Slack workspace, follow the [Setup](#setup) section below.

---

## What it does

- Lists Slack channels the bot has been invited to, by name (no copy-pasting channel IDs)
- Fetches all messages in a single day or a custom date range
- Recursively pulls thread replies and inlines them under their parent message
- Resolves Slack user IDs to display names (with caching to minimise API calls)
- Converts Slack's pseudo-markup into standard Markdown
- Filters out system noise (joins, leaves, pin/unpin notifications, etc.)
- **Post-fetch filter by user** — narrow the rendered batch to *who* started a message (**Author**) or *who participated* in a thread (**Includes**), with an explicit **Apply** so a stray selection doesn't re-render the whole view
- Validates dates (warns and swaps if start > end, caps end at today)
- Exports to **CSV** (UTF-8 BOM for Excel) or **JSON** (full structure with threads + attachments) — the filter applies to exports too

## Why it's interesting

- **Three interfaces, one core.** The same `src/` module powers a Streamlit UI, an interactive CLI, and an importable Python API — useful when the audience is mixed (non-technical users want a web UI, automation wants a function call).
- **Two-tier caching** (channels + users) keeps Slack API calls low and avoids `ratelimited` errors on repeat fetches.
- **Pagination + thread expansion** is handled transparently for the caller; you just ask for a date range and get back a complete picture.
- **Deploy-ready**: works locally, on Streamlit Cloud, Render, Heroku, Railway, or any VPS — all configuration is environment-variable-driven.

---

## Architecture

```
channeldayfetcher/
├── ui.py                          # Streamlit web interface
├── cli.py                         # Interactive CLI
├── programmatic.py                # Importable Python API
├── setup_env.py                   # First-run helper for .env
│
├── src/                           # Core library
│   ├── slack_client.py            # SlackFetcher  — paginated history + thread expansion
│   ├── demo_fetcher.py            # DemoFetcher   — drop-in replacement for the public demo
│   ├── channel_cache.py           # ChannelCache  — bot-membership channels, persisted to disk
│   ├── user_cache.py              # UserCache     — user_id → name, persisted to disk
│   ├── formatters.py              # MessageFormatter — Slack markup → Markdown + relevance filter
│   ├── exporters.py               # DataExporter  — JSON & CSV (file-based + in-memory)
│   ├── utils.py                   # Config loading, date validation, demo-mode helper
│   └── logger.py                  # Logging setup
│
├── demo/                          # Public-demo dataset (read by DemoFetcher when DEMO_MODE=true)
│   ├── sample_channel_cache.json  # Fake channels for the dropdown
│   ├── sample_user_map.json       # Fake users for ID → name resolution
│   ├── pool/                      # Per-channel message pools (days_ago + time_of_day templates)
│   │   ├── general.json
│   │   ├── engineering.json
│   │   └── announcements.json
│   └── assets/                    # SVG attachments referenced from the pools (served from GitHub raw)
│
├── .streamlit/                    # Streamlit theme + secrets template
├── env.example                    # Environment-variable template
├── requirements.txt
├── render.yaml                    # Optional: Render deployment config
└── runtime.txt                    # Optional: Python version pin
```

## Tech stack

- **Python 3.10+**
- [`slack_sdk`](https://pypi.org/project/slack-sdk/) — official Slack Web API client
- [`streamlit`](https://streamlit.io/) — web UI
- [`python-dotenv`](https://pypi.org/project/python-dotenv/) — local config loading

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/GRuizV/ChannelDayFetcher.git
cd ChannelDayFetcher

python -m venv venv
source venv/bin/activate          # On Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Create a Slack app and bot token

1. Go to <https://api.slack.com/apps> → **Create New App** → **From scratch**
2. Under **OAuth & Permissions → Bot Token Scopes**, add:
   - `channels:read` — list public channels
   - `channels:history` — read public-channel messages
   - `groups:read` — list private channels
   - `groups:history` — read private-channel messages
   - `users:read` — resolve user IDs to display names
3. Click **Install to Workspace** and copy the **Bot User OAuth Token** (starts with `xoxb-`)
4. In any Slack channel you want to read, run `/invite @YourBotName`

### 3. Configure the token

Either run the interactive helper:

```bash
python setup_env.py
```

…or manually:

```bash
cp env.example .env
# then edit .env and paste your xoxb-... token
```

`.env` is gitignored. For deployed environments, set `SLACK_TOKEN` as a regular environment variable on your platform of choice.

---

## Usage

### Streamlit UI

```bash
streamlit run ui.py
```

Open <http://localhost:8501>. Click 🔄 to load channels, pick one, choose **Fetch Today** or a custom date range, and download the result.

The sidebar exposes:

- **Date range / Fetch Today** — what to retrieve.
- **Display options** — chronological vs. reverse order, timestamps on/off.
- **Filter** — **Author** (only top-level posts by the chosen user) or **Includes** (any thread the chosen user appears in). The dropdown is populated from users present in *this* fetched batch, and the filter only applies after clicking **Apply Filter** — so a stray pick doesn't re-render the whole view. The filter affects both the rendered output and the exports.
- **Exports** — pick CSV / JSON to enable download buttons under the message list. Off by default; a blue prompt at the bottom of every batch reminds you to opt in.

After each fetch — and after any channel refresh or full reset — all sidebar choices snap back to defaults so the next interaction is intentional.

### CLI

```bash
python cli.py
```

Interactive prompts walk you through channel selection, date range, sort order, and export.

### Programmatic API

```python
from programmatic import fetch_and_export

result = fetch_and_export(
    channel_id="C123456789",
    start_date="2025-10-20",
    end_date="2025-10-24",
    export_json=True,
    export_csv=True,
)

print(f"Retrieved {len(result['messages'])} messages")
print(f"Exports: {result['export_paths']}")
```

Useful for scheduled jobs, data pipelines, or wiring Slack data into downstream tooling.

---

## Deployment

The repo is deploy-ready for any Python-friendly platform. Two deployment shapes are supported:

- **Real-Slack deployment**: set `SLACK_TOKEN` on the host. The app fetches from your own workspace.
- **Public-demo deployment**: set `DEMO_MODE=true` and leave `SLACK_TOKEN` unset. The app serves the baked sample conversation from `demo/`. No live Slack credentials live on the host.

| Platform | Config in this repo | Notes |
|----------|--------------------|-------|
| **Streamlit Cloud** | `.streamlit/secrets.toml.example` | Easiest free option for Streamlit apps. Set `SLACK_TOKEN` (real mode) **or** `DEMO_MODE=true` (public demo) in App Settings → Secrets. |
| **Render**          | `render.yaml`                    | Free tier available. Set `SLACK_TOKEN` or `DEMO_MODE` in dashboard. |
| **Heroku / Railway / VPS** | `requirements.txt`, `runtime.txt` | Standard Python deployment; run `streamlit run ui.py --server.port=$PORT --server.address=0.0.0.0`. |

### How demo mode works

When `DEMO_MODE=true`, `ui.py` swaps `SlackFetcher` for `DemoFetcher` and points the channel/user caches at `demo/sample_*.json` instead of the on-disk runtime caches. Each entry in `demo/pool/<channel>.json` is a Slack-shaped message *template* with `days_ago` and `time_of_day` fields; the fetcher rebases those against `datetime.now()` on every call, so today is always today and the demo never ages.

A simulated 5–9 second delay on the "refresh channels" and "fetch messages" actions makes the local-disk reads feel like a real Slack API roundtrip and gives Streamlit Cloud's cold-start something to hide behind.

The dataset is **deterministic** for a given date — refreshing the page or sharing the link on the same day yields the same conversation. The content rotates naturally across the rolling 90-day window without any cron jobs or live workspace dependencies.

---

## Design notes

- **Caches are local-only.** `user_cache.json` and `channel_cache.json` are gitignored; they're rebuilt automatically on first run via the 🔄 refresh button (UI) or the `r` prompt (CLI). An example schema is shipped as `channel_cache.example.json`.
- **Filtering happens during fetch**, not after — saves memory on large channels and keeps the API surface clean (callers get only "real" messages).
- **CSV uses `;` delimiter and UTF-8 BOM** so Excel opens it directly without mangling accented text.
- **Thread expansion is recursive but rate-limit-aware** — falls back to a 30s sleep + retry on `ratelimited`.
- **No persistence beyond caches.** This tool is for one-shot fetches; there's no database. If you want history, run it on a schedule and persist the exports.

## Future improvements

- Async thread fetching to parallelise heavy retrievals
- Keyword search in the UI (user filtering is already in place)
- Reaction capture in exports
- Direct-message and group-message support
- Scheduled exports to S3 / database

---

## License

MIT — free to use, modify, and redistribute.
