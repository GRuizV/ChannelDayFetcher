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

### Step 1.2 — Create the Slack app ✅
- [x] Created `ChannelDayFetcher` app in the portfolio workspace.

### Step 1.3 — Add Bot Token Scopes ✅
- [x] All five Bot Token Scopes added: `channels:read`, `channels:history`, `groups:read`, `groups:history`, `users:read`.

### Step 1.4 — Install to workspace + grab token ✅
- [x] Installed to workspace; `xoxb-...` bot token stashed locally for Phase 2.

### Step 1.5 — Create a test channel and seed data ✅
- [x] Created two channels (`#cdf-channel`, `#cdf-channel-2`) — two channels exercises the dropdown channel-switching in the demo.
- [x] Bot invited to both channels.
- [x] Seeded with a mix of plain text, formatted text, threads, attachments, and mentions.

---

## Phase 2 — Local environment

### Step 2.1 — Virtual environment ✅
- [x] `venv` created and activated. Python 3.12.0.

### Step 2.2 — Install dependencies ✅
- [x] `pip install -r requirements.txt` completed successfully.

### Step 2.3 — Drop in the Slack token ✅
- [x] `.env` contains the real `xoxb-` token. `git status` confirms it is NOT tracked.

---

## Phase 3 — Smoke-test each interface

> Run these in CLI → Programmatic → UI order. CLI is the simplest sanity check; UI is the showpiece but has the most moving parts.

### Step 3.1 — CLI ✅
- [x] CLI fetched both channels, exported JSON + CSV, resolved user names + mentions, expanded a thread, captured file attachments, converted Slack markup to Markdown.

### Step 3.2 — Programmatic API ✅
- [x] `fetch_and_export()` invoked via one-liner — 2 messages with 1 thread fetched, JSON export saved to `exports/`.

### Step 3.3 — Streamlit UI ✅
- [x] All UI paths exercised: channel dropdown + refresh, Fetch Today, Fetch Range, sort toggle, timestamp toggle, CSV + JSON downloads, channel switch (`#cdf-channel-2`), Reset.
- [x] Bonus: Streamlit's markdown renderer also handles `~strike~` syntax beyond what `formatters.py` does.

### Post-Phase-3 cleanup ✅
- [x] Removed `enableCORS = false` from `.streamlit/config.toml`. The conflict-with-XSRF warning is gone on boot.

---

## Phase 4 — Build the public demo dataset + demo mode

The deployed Streamlit Cloud app must not depend on a live Slack workspace (free-tier 90-day rollover would silently break it). Instead, bake a static JSON snapshot into the repo and have the app load that when running in "demo mode". Recruiters get a working UI forever; technical reviewers can still self-host against their own Slack via the README.

### Key decisions made during Phase 4

- **Determinism, not randomness.** Same fetch on same wall-clock day always returns the same result. No per-visitor variation.
- **Pool per channel, not one giant file.** Three channel-flavored pool files (`general`, `engineering`, `announcements`) so the demo can show channel switching with content that fits each context (banter / code / broadcasts).
- **Relative timestamps, rebased at load time.** Each message stores `days_ago` + `time_of_day` instead of absolute `ts`. The `DemoFetcher` rebases against `datetime.now()` on every call → today is always today; the demo never ages.
- **Distribution weighted toward recent.** ~25 messages per channel spread across the last 90 days, more frequent closer to today, so Fetch Today, last-week, and last-quarter all return sensible counts.
- **File attachments shipped as SVGs in the repo, served via GitHub raw URLs.** A clickable 📎 link in the deployed Streamlit demo opens an actual image from `github.com/GRuizV/ChannelDayFetcher/raw/main/demo/assets/...`. No external hosting, no Slack auth, no broken links.
- **Rejected: bots posting real-time messages with date manipulation.** Slack's `chat.postMessage` doesn't allow backdating timestamps — would have re-introduced the 90-day-rollover problem.
- **Rejected: `customer_quotes` seed file.** Too saturated with real customer/property/internal names to be worth sanitizing. `industry_news_channel` and `memes_channel` were used as structural inspiration only; the final pool content is freshly composed.

### Step 4.1 — Capture & inspect seed conversations ✅
- [x] User exported three real channel conversations as raw inspiration (kept in `demo/base conversations/`, gitignored).
- [x] Files inspected for contamination level — customer_quotes dropped; other two used only as structural reference.
- **Decision:** the final demo pools are freshly composed rather than directly sanitized from real exports.

### Step 4.2 — Build sanitized demo dataset ✅
- [x] `demo/sample_user_map.json` — 6 fake users (Alex Chen, Sam Patel, Jordan Lee, Riley Park, Casey Morgan, Devi Krishnan).
- [x] `demo/sample_channel_cache.json` — 3 fake channels: `#general`, `#engineering`, `#announcements`.
- [x] `demo/pool/general.json` — 25 top-level messages + threads (light banter, mixed formatting).
- [x] `demo/pool/engineering.json` — 25 top-level messages + threads (code blocks, debugging stories, architecture).
- [x] `demo/pool/announcements.json` — 18 top-level messages + threads (broadcasts, hiring, milestones).
- [x] `demo/assets/` — 6 SVG files: `Q3_roadmap`, `dashboard_redesign_wip`, `deploy_diagram`, `ingestion_pipeline`, `incident_postmortem`, `brand_guidelines_v2`, `1k_users_celebration`. Referenced from the pools via GitHub raw URLs.
- **Verify:** `grep -i "lilo\|<your real name>" demo/` outside `base conversations/` should return nothing.

### Step 4.3 — DemoFetcher and demo-mode switch ✅
- [x] `src/demo_fetcher.py` — `DemoFetcher` class mirroring `SlackFetcher`'s public interface (`fetch_today`, `fetch_messages_in_range`). Loads pool files at init; rebases `days_ago` + `time_of_day` against `datetime.now()` on each call; filters by requested date range.
- [x] `src/utils.py` — added `is_demo_mode()` helper; `load_config()` returns `{slack_token: None, demo_mode: True}` when `DEMO_MODE=true` so the token check is bypassed.
- [x] `src/__init__.py` — exports `DemoFetcher` and `is_demo_mode`.
- [x] `ui.py`, `cli.py`, `programmatic.py` — all three entry points now:
  - Compute `DEMO_MODE = is_demo_mode()` at the top
  - Branch between `DemoFetcher()` and `SlackFetcher(token=...)`
  - Point caches at `demo/sample_*.json` vs the local `*_cache.json`
  - Skip `cache.update_from_messages(...)` (no Slack API call) in demo mode
  - Hide / no-op the `🔄` channel refresh button in demo mode
- [x] `ui.py` shows a "🎬 Demo mode" caption when the env var is set, so visitors know what they're looking at.

### Step 4.4 — README updated ✅
- [x] Added **"Try the demo"** section near the top of the README, with a placeholder for the future Streamlit URL and a local-demo command (`DEMO_MODE=true streamlit run ui.py`).
- [x] Self-host path (existing Setup section) confirmed sufficient — no edits needed there.

### Step 4.5 — First smoke test ✅ (with feedback)
Initial smoke test passed functionally but surfaced two UX gaps and prompted one new feature:
- Channels showed up instantly in demo mode → looked pre-baked (real mode forces a refresh).
- Messages rendered instantly in demo mode → no perceptible "fetch" feel.
- Feature idea: filter displayed messages by user, for "what did Devi say last week" questions.

### Step 4.6 — UX polish + Author/Includes filter ✅

**Demo-mode UX parity with real mode:**
- [x] Refresh button now visible in demo mode too. Channel dropdown starts empty until 🔄 is clicked.
- [x] On refresh in demo mode: a simulated 3.5–5.5s delay (random per click) before the static channel list is loaded from `demo/sample_channel_cache.json`. Same range applies when fetching messages.
- [x] `DEMO_DELAY_RANGE = (3.5, 5.5)` constant at the top of `ui.py` so this is tweakable in one place.

**New Author / Includes filter (both modes):**
- [x] New sidebar section: "Filter mode" radio with `None` / `Author` / `Includes`, plus a "User" dropdown.
- [x] **Author** = only top-level messages by the selected user.
- [x] **Includes** = any thread where the selected user appears (parent or any reply). Whole thread is preserved including attachments.
- [x] Filter applies at display + export time, against the unfiltered messages stored in session state, so changing the filter does NOT require a re-fetch.
- [x] When a filter is active, an `🔎 Filter active — Author = Alex Chen · 4 of 12 messages shown` banner shows above the message list.
- [x] User dropdown is populated from session state's user_map if a fetch has happened; otherwise from the on-disk user cache. In demo mode this means all 6 sample users are pickable immediately.

### Step 4.5 (re-test) — Local smoke test of both modes
- [ ] **Normal mode regression check:** plain `streamlit run ui.py` — channel dropdown still works, filter widget appears in sidebar (populated only after first fetch), filter applied correctly.
- [ ] **Demo mode:**
  - `$env:DEMO_MODE="true"; streamlit run ui.py`
  - 🎬 caption shows; 🔄 button shows; dropdown starts EMPTY.
  - Click 🔄 → ~4s spinner → three demo channels appear.
  - Fetch Today → ~4s spinner → ~3+3+2 messages across the three channels.
  - Last-7-day range returns ~12 messages.
  - Filter: pick "Includes" + "Devi Krishnan" → message list narrows to threads where Devi appears. Counter banner shows "X of Y".
  - Switch filter to "Author" + same user → narrows further.
  - CSV/JSON exports reflect the filtered view.
  - 📎 attachment links: visible in message; opening only works once `main` is pushed to GitHub.
- [ ] Clear the env var afterwards: `Remove-Item Env:DEMO_MODE`.

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
- **GitHub raw URLs are public.** The 📎 attachment URLs in the demo pools point to `raw.githubusercontent.com/GRuizV/ChannelDayFetcher/main/demo/assets/*.svg`. They only resolve after the next push to `main`. Until then, links 404. The text of each message still renders correctly.
- **`demo/base conversations/` is gitignored.** Already added to `.gitignore` — the raw, contaminated seed exports never leave your machine.
- **`secrets.toml` accidentally committed.** `.streamlit/secrets.toml` is gitignored; the `.example` is fine to ship. Double-check before any commit if you ever create the real `secrets.toml` locally.
- **Channel ID hardcoding (resolved).** `programmatic.py`'s `main()` no longer hardcodes a channel ID; it pulls the first available from whichever cache the current mode uses.
- **Streamlit Cloud free tier sleeps.** The app idles after inactivity and wakes on the next visit (~10s cold start). Mention that near the CV link if relevant.

---

## Definition of done

- [ ] All three interfaces fetch messages from the test channel and export correctly.
- [ ] No sensitive data (real tokens, internal channel IDs, real user names) appears anywhere in `git status` or in any committed file.
- [ ] Live Streamlit Cloud demo URL is in the README and reachable from a logged-out browser, serving the baked demo dataset.
- [ ] You can describe the project verbally in 30 seconds using the README structure as a guide.
