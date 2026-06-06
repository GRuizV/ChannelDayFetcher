# ChannelDayFetcher — Wire-up & Smoke-test Plan

> **Repo policy:** this plan is intentionally committed to the public repo. Showing the planning process is part of the portfolio narrative — recruiters get to see *how* the project came together, not just the polished end-state.

Goal: get the cleaned, public version of ChannelDayFetcher fully wired against a Slack workspace, then smoke-test all three interfaces (CLI, Streamlit UI, programmatic API) end-to-end, and deploy a live demo on Streamlit Cloud that can be linked from the CV.

---

## Open questions — resolved

- [x] **Which Slack workspace?** — Existing dedicated portfolio workspace; channel already created (empty).
- [x] **Public live demo or local-only?** — Public live demo on Streamlit Cloud. Phase 5 is in scope (not optional).

---

## Phase 1 — Slack workspace + app

### Step 1.1 — Pick / create the Slack workspace ✅
- [x] Dedicated portfolio Slack workspace already exists with a test channel ready (empty).

### Step 1.2 — Create the Slack app
- [ ] Go to <https://api.slack.com/apps> → **Create New App** → **From scratch**.
- [ ] App name: `ChannelDayFetcher` (or whatever — only shown internally).
- [ ] Pick the workspace from Step 1.1.
- **Verify:** you land on the app's settings page.

### Step 1.3 — Add Bot Token Scopes
Navigate: **OAuth & Permissions → Scopes → Bot Token Scopes** → Add each:
- [ ] `channels:read`
- [ ] `channels:history`
- [ ] `groups:read`
- [ ] `groups:history`
- [ ] `users:read`
- **Verify:** all five scopes appear in the Bot Token Scopes table.

### Step 1.4 — Install to workspace + grab token
- [ ] Click **Install to Workspace** → authorize.
- [ ] Copy the **Bot User OAuth Token** (starts with `xoxb-`). Stash it somewhere temporary (1Password / a sticky note).
- **Verify:** the token starts with `xoxb-` and has at least 50 characters.

### Step 1.5 — Create a test channel and seed data
- [ ] In Slack, create a channel: `#cdf-test` (or similar).
- [ ] Invite the bot: in the channel, run `/invite @ChannelDayFetcher`.
- [ ] Post at least 3–5 messages of varying types so you have something to fetch:
  - A plain message
  - A message with *bold* and `code` markup
  - A message in a thread (any reply works)
  - A message with a file attachment (drop in a small image)
  - A message with a user mention (mention yourself)
- **Verify:** the bot appears in the channel's member list.

---

## Phase 2 — Local environment

### Step 2.1 — Open the repo and create a virtual environment
- [ ] `cd "c:/Users/USUARIO/GR/Software Development/Projects/07 ChannelDayFetcher"`
- [ ] `python -m venv venv`
- [ ] Activate: `venv\Scripts\activate` (PowerShell) or `source venv/bin/activate` (bash)
- **Verify:** prompt shows `(venv)`; `python --version` reports 3.10+.

### Step 2.2 — Install dependencies
- [ ] `pip install -r requirements.txt`
- **Verify:** no errors; `pip list` shows `slack_sdk`, `streamlit`, `python-dotenv`.

### Step 2.3 — Drop in the Slack token
- [ ] `python setup_env.py` and paste the `xoxb-` token, **OR** manually copy `env.example` to `.env` and edit it.
- **Verify:** `.env` exists, contains `SLACK_TOKEN=xoxb-...`, AND `.env` is gitignored (`git status` should NOT list it).

---

## Phase 3 — Smoke-test each interface

> Run these in CLI → Programmatic → UI order. CLI is the simplest sanity check; UI is the showpiece but has the most moving parts.

### Step 3.1 — CLI
- [ ] `python cli.py`
- [ ] When prompted, refresh channels.
- [ ] Pick `#cdf-test` from the list.
- [ ] Choose "Fetch today's messages".
- [ ] Pick chronological order.
- [ ] When asked, export to BOTH (j+c or `b`).
- **Verify:**
  - Console shows your seeded messages with resolved user names (not `Uxxxxx` IDs).
  - Thread replies appear nested with `↳` prefix.
  - File attachment shows with 📎.
  - `exports/slack_export_YYYY-MM-DD_to_YYYY-MM-DD.json` and `.csv` files exist.
  - Open the CSV in Excel — accented characters render correctly.

### Step 3.2 — Programmatic API
- [ ] Open `programmatic.py`. Note the `main()` function uses `2025-10-22 → 2025-10-23` hardcoded dates — those won't match your test data.
- [ ] Either edit those dates to today, or run the module from a fresh script:
  ```python
  from programmatic import fetch_and_export
  result = fetch_and_export(
      channel_id="<your #cdf-test channel ID>",  # get from ChannelCache or Slack URL
      start_date="2026-05-26",
      end_date="2026-05-26",
      export_json=True,
      export_csv=False,
  )
  print(len(result["messages"]), "messages")
  ```
- [ ] To get the channel ID quickly: after running CLI once, `channel_cache.json` will contain the mapping.
- **Verify:** message count matches what you saw in CLI; a new JSON export lands in `exports/`.

### Step 3.3 — Streamlit UI
- [ ] `streamlit run ui.py`
- [ ] Open <http://localhost:8501>.
- [ ] Click the 🔄 refresh button in the sidebar.
- [ ] Select `#cdf-test` from the dropdown.
- [ ] Click the blue **Fetch Today** button.
- **Verify:**
  - Messages render with bold/italic/code formatting.
  - Timestamps are visible (toggle off → on to confirm).
  - Attachments render as clickable 📎 links.
  - Thread replies show indented.
  - Click **Download CSV** — file downloads, opens cleanly in Excel.
  - Click **Download JSON** — file downloads, opens cleanly in any text editor.
- [ ] Test the date-range path: pick yesterday → today. Re-verify.
- [ ] Test the **Reset** button — clears the view.

---

## Phase 4 — Build the public demo dataset + demo mode

The deployed Streamlit Cloud app must not depend on a live Slack workspace (free-tier 90-day rollover would silently break it). Instead, bake a static JSON snapshot into the repo and have the app load that when running in "demo mode". Recruiters get a working UI forever; technical reviewers can still self-host against their own Slack via the README.

### Step 4.1 — Capture a realistic sample conversation
- [ ] In your test Slack channel, post a small but visually rich conversation (~10–15 top-level messages + a few threads + 1–2 file attachments + 1–2 user mentions + a mix of plain / **bold** / `code` / [links]).
- [ ] Run `python cli.py` against the channel, fetch the day, and export JSON.
- [ ] Locate the JSON in `exports/` — this is your seed dataset.
- **Verify:** open the JSON; threads, attachments, mentions all present.

### Step 4.2 — Sanitize and bake the dataset into the repo
- [ ] Create `demo/` directory.
- [ ] Copy the JSON to `demo/sample_conversation.json`.
- [ ] **Sanitize user IDs and names** — replace your real workspace user IDs (`U...`) and display names with generic placeholders (`Alex Chen`, `Sam Patel`, `Jordan Lee`, etc.). Same for any channel ID references.
- [ ] Build a matching `demo/sample_user_map.json` mapping the placeholder user IDs to placeholder names.
- [ ] Build a matching `demo/sample_channel_cache.json` with 2–3 fake channels (e.g., `#general`, `#engineering`, `#design`) — the dropdown should look populated.
- **Verify:** `grep -i "<your real name>" demo/` returns nothing; `grep "U0[A-Z0-9]\{8,\}" demo/` only matches your placeholder IDs.

### Step 4.3 — Add a `DemoFetcher` and demo-mode switch
- [ ] Add `src/demo_fetcher.py` with a `DemoFetcher` class that mirrors `SlackFetcher`'s public methods (`fetch_today`, `fetch_messages_in_range`) but reads from `demo/sample_conversation.json` and date-filters in memory.
- [ ] In `src/utils.py` (or wherever `load_config` lives), add detection: `DEMO_MODE = os.getenv("DEMO_MODE", "").lower() == "true"`.
- [ ] In `ui.py`, `cli.py`, `programmatic.py`: when `DEMO_MODE` is true, instantiate `DemoFetcher` instead of `SlackFetcher`, and load `demo/sample_*.json` for the caches.
- [ ] In `load_config`: if `DEMO_MODE` is true, do NOT raise on missing `SLACK_TOKEN`.
- **Verify:** `DEMO_MODE=true streamlit run ui.py` (no `SLACK_TOKEN` in `.env`) renders the baked conversation correctly; exports still work.

### Step 4.4 — Update README with the two paths
- [ ] Add a **"Try the demo"** section pointing to the future Streamlit URL (placeholder for now).
- [ ] Add a **"Run against your own Slack workspace"** section — confirm the existing Setup section already covers this; tighten if needed.
- [ ] Explicitly mention the `DEMO_MODE` env var so anyone reading the code knows how the deployed demo works.

### Step 4.5 — Local sanity check before deploying
- [ ] With `SLACK_TOKEN` set and no `DEMO_MODE`: app hits real Slack — works as before.
- [ ] With `DEMO_MODE=true` and `SLACK_TOKEN` removed/unset: app serves baked data — no Slack API call attempted.
- **Verify:** flip the switch both ways; both modes render correctly.

---

## Phase 5 — Cleanup before any public demo

### Step 5.1 — Confirm nothing sensitive landed in the repo
- [ ] `git status` — only expected changes should be present.
- [ ] If `exports/`, `user_cache.json`, `channel_cache.json`, or `logs/` show up: confirm they're gitignored (`git check-ignore <file>` should print the path).
- **Verify:** `.env` is NOT listed in `git status`; `demo/` IS staged and contains only sanitized data.

### Step 5.2 — Commit and push the demo-mode work
- [ ] Stage and commit the new `demo/`, `src/demo_fetcher.py`, and entry-point edits.
- [ ] Push to `main`.

---

## Phase 6 — Streamlit Cloud deployment (live demo)

### Step 6.1 — Deploy
- [ ] Go to <https://share.streamlit.io/> → sign in with the personal GitHub (`GRuizV`).
- [ ] **New app** → repo: `GRuizV/ChannelDayFetcher` → branch: `main` → main file: `ui.py`.
- [ ] Click **Deploy**.

### Step 6.2 — Configure the env var (demo mode, NOT a real token)
- [ ] App settings → **Secrets** → add:
  ```toml
  DEMO_MODE = "true"
  ```
- [ ] Do NOT set `SLACK_TOKEN` here — the deployed demo serves baked data only.
- [ ] Save; the app auto-restarts.

### Step 6.3 — Verify live deployment
- [ ] Open the public URL Streamlit gives you (logged-out browser is a stronger check).
- [ ] Confirm the dropdown is populated from the baked channel cache.
- [ ] Fetch a date, see the sample conversation render, download both exports.
- **Verify:** behaviour matches the local `DEMO_MODE=true` smoke test from Step 4.5.

### Step 6.4 — Update the README with the live URL
- [ ] Replace the placeholder from Step 4.4 with the real Streamlit URL.
- [ ] Commit + push.

---

## Risks & gotchas

- **Slack free-tier 90-day rollover** — solved by Phase 4. The deployed demo never reads from live Slack, so workspace-side message expiry can't break it.
- **Demo dataset leaks real data.** The seed JSON comes from your real workspace; aggressive sanitization in Step 4.2 is the only safeguard. Always grep before committing.
- **`secrets.toml` accidentally committed.** `.streamlit/secrets.toml` is gitignored; the `.example` is fine to ship. Double-check before any commit if you ever create the real `secrets.toml` locally.
- **Channel ID hardcoding.** `programmatic.py`'s `main()` example uses an example channel ID. If you customise it for your test workspace, don't push your real channel ID to the public repo.
- **Streamlit Cloud free tier sleeps.** The app idles after inactivity and wakes on the next visit (~10s cold start). Mention that near the CV link if relevant.

---

## Definition of done

- [ ] All three interfaces fetch messages from the test channel and export correctly.
- [ ] No sensitive data (real tokens, internal channel IDs, real user names) appears anywhere in `git status` or in any committed file.
- [ ] Live Streamlit Cloud demo URL is in the README and reachable from a logged-out browser, serving the baked demo dataset.
- [ ] You can describe the project verbally in 30 seconds using the README structure as a guide.
