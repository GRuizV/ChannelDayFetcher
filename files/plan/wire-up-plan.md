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
- [x] Refresh button visible in demo mode too. Channel dropdown starts empty until 🔄 is clicked.
- [x] Refresh + fetch in demo mode each take a simulated **5–9s random delay** (calibrated against the user's actual day-to-day experience of the real tool internally). Single constant `DEMO_DELAY_RANGE` at the top of `ui.py` controls both.
- [x] Demo-mode refresh persistence: loaded channel list is stored in `st.session_state["demo_channel_map"]` so it survives reruns.

**Author / Includes filter (both modes):**
- [x] Sidebar: "Filter mode" radio with `None` / `Author` / `Includes`, then a "User" dropdown, then an **Apply Filter** button. Filter only takes effect after Apply — a stray dropdown change doesn't re-render the whole message list.
- [x] **Author** = only top-level posts started by the selected user.
- [x] **Includes** = any thread where the selected user appears (parent or any reply). Whole thread preserved.
- [x] User dropdown is built **only from users present in the currently fetched batch** (top-level posters for Author mode, anyone for Includes mode). Pre-fetch the dropdown is empty with a hint message. Channel-specific pool composition naturally narrows the list: `#engineering` shows 3 names, `#announcements` shows ~2 main posters.
- [x] Filter applies at display + export time, so toggling/changing it never triggers a re-fetch.
- [x] When a filter is active, an `🔎 Filter active — Author = Alex Chen · 4 of 12 messages shown` info banner shows above the message list.

**Widget reset on refresh / Reset / fetch:**
- [x] Every channel refresh, full Reset, and successful fetch returns all sidebar widgets to defaults: date range → today/today, sort → Oldest First, timestamps → on, filter → None, exports → both off.
- [x] Implementation: `__reset_widgets_pending__` flag set at the trigger site, consumed at the **top of the next run before any widget mounts** by pre-writing default values into `st.session_state`. Replaces an earlier deletion-based approach that didn't reliably re-render the widgets.
- [x] Export checkboxes default to **false** (changed from CSV defaulting to true). When neither is selected, a blue prompt banner under the message list invites the user to enable one.

**Date validation surfaced in the UI:**
- [x] `ui.py` detects `start > end` and `end > today` before calling the fetcher. Warnings get stored in `st.session_state["pending_warnings"]` and rendered once via `st.warning()` at the top of the post-fetch display (then popped so they don't re-appear on subsequent reruns like Apply Filter).
- [x] Warnings also written to the log at `WARNING` level.

**Quieter logs:**
- [x] `"Streamlit UI session started"` now logs only on the first run of a Streamlit session (guarded by a session-state flag). Previously fired on every script rerun → dozens of identical lines per visit.

### Step 4.5 (re-test) ✅
- [x] **Normal mode:** confirmed by user. Channel dropdown still works, filter populated only after fetch, applies on click.
- [x] **Demo mode:** confirmed by user. Dropdown starts empty; 🔄 loads with simulated delay; fetch has simulated delay; filter dropdown narrows per channel; Apply gates the filter; widgets reset visibly after every interaction; date-swap warning fires; export prompt banner shows when neither is selected.

---

## Phase 5 — Cleanup before any public demo

### Step 5.1 — Sanitization sweep ✅
- [x] Grepped the repo for `lilo`, `inn-flow`, internal workspace IDs, real channel IDs, real user IDs, real personal names. Only matches were:
  - `LICENSE`: "Copyright (c) 2026 Gerardo Ruiz" — intentional, the repo owner's own license.
- [x] `git status` clean — no `.env`, no real `channel_cache.json`/`user_cache.json`/`exports/`/`logs/` showing up (all gitignored).
- [x] `demo/base conversations/` (raw, contaminated seed exports) is gitignored — never leaves the local machine.

### Step 5.2 — env.example cleanup ✅
- [x] `DEMO_MODE = "true"` (which would have force-enabled demo mode for anyone copying `env.example → .env`) replaced with a commented hint:
  ```
  # Optional: set DEMO_MODE=true to run against the baked-in sample dataset
  # instead of a real Slack workspace. When set, SLACK_TOKEN is not required.
  # DEMO_MODE=true
  ```

### Step 5.3 — Commit and push
- [ ] Stage and commit the remaining changes (`env.example`, `ui.py`).
- [ ] Push to `main`.


---

## Phase 6 — Streamlit Cloud deployment (live demo)

### Step 6.1 — Deploy ✅
- [x] Signed in to <https://share.streamlit.io/> with the deploying GitHub account.
- [x] New app → repo: `GRuizV/ChannelDayFetcher` → branch: `main` → main file: `ui.py`.
- [x] Deployed; build picked up `requirements.txt` and `runtime.txt` (bumped from `python-3.11` → `python-3.12` to match the local dev environment).

### Step 6.2 — Configure the env var ✅
- [x] Secrets configured with **only** `DEMO_MODE = "true"`. `SLACK_TOKEN` deliberately omitted — the deployed app serves baked data and has no need for a real Slack credential (keeping zero credentials on the host was the whole point of Phase 4).

### Step 6.3 — Verify live deployment ✅
- [x] Logged-out browser walkthrough confirmed by the user: refresh + simulated delay, channel switching, Fetch Today / Fetch Range, attachments resolving from GitHub raw, filter Apply, exports, date-swap warning.
- **Live URL:** <https://channeldayfetcher-grv.streamlit.app/>

### Step 6.4 — Live URL added to README ✅
- [x] README's "Try the demo" section now links to `https://channeldayfetcher-grv.streamlit.app/` with a note about the cold-start delay on Streamlit Cloud's free tier.

---

## Risks & gotchas

- **Slack free-tier 90-day rollover** — solved by Phase 4. The deployed demo never reads from live Slack, so workspace-side message expiry can't break it.
- **GitHub raw URLs are public.** The 📎 attachment URLs in the demo pools point to `raw.githubusercontent.com/GRuizV/ChannelDayFetcher/main/demo/assets/*.svg`. They only resolve after the next push to `main`. Until then, links 404. The text of each message still renders correctly.
- **`demo/base conversations/` is gitignored.** Already added to `.gitignore` — the raw, contaminated seed exports never leave your machine.
- **`secrets.toml` accidentally committed.** `.streamlit/secrets.toml` is gitignored; the `.example` is fine to ship. Double-check before any commit if you ever create the real `secrets.toml` locally.
- **Channel ID hardcoding (resolved).** `programmatic.py`'s `main()` no longer hardcodes a channel ID; it pulls the first available from whichever cache the current mode uses.
- **Streamlit Cloud free tier sleeps.** The app idles after inactivity and wakes on the next visit (~10s cold start). Mention that near the CV link if relevant.

---

## Definition of done — ✅ all met

- [x] All three interfaces (CLI, Streamlit UI, programmatic API) fetch messages from the test workspace and export correctly.
- [x] Demo mode swaps in `DemoFetcher` cleanly; the same UI and API surface works against baked sample data with zero live Slack dependency.
- [x] No sensitive data (real tokens, internal workspace IDs, real channel IDs, real user names) appears in `git status` or in any committed file. Sanitization grep is clean.
- [x] Live Streamlit Cloud demo at <https://channeldayfetcher-grv.streamlit.app/> reachable from a logged-out browser, serving the baked dataset with zero credentials on the host.
- [x] README documents both paths (live demo + self-host) and includes architecture, design notes, and how demo mode works.
- [x] The plan itself is committed to the public repo as part of the portfolio narrative.

---

## Wrap-up — what shipped

| Layer | Artifact |
|---|---|
| **Code** | `src/{slack_client, demo_fetcher, channel_cache, user_cache, formatters, exporters, utils, logger}.py`; entry points `ui.py`, `cli.py`, `programmatic.py`; `setup_env.py` first-run helper. |
| **Demo dataset** | `demo/sample_{user_map,channel_cache}.json`, `demo/pool/{general,engineering,announcements}.json`, `demo/assets/*.svg` (6 SVGs served from GitHub raw). |
| **Config / deploy** | `requirements.txt`, `runtime.txt` (python-3.12), `render.yaml`, `.streamlit/{config,secrets.toml.example}.toml`, `env.example` with commented `DEMO_MODE` hint. |
| **Docs** | `README.md` (portfolio-grade, both deployment paths documented), `LICENSE` (MIT), `files/plan/wire-up-plan.md` (this plan). |
| **Public surfaces** | GitHub repo `GRuizV/ChannelDayFetcher`; live demo `https://channeldayfetcher-grv.streamlit.app/`. |
