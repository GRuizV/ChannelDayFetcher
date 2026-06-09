"""
Slack Channel Day Fetcher — Streamlit UI
---------------------------------------
Web interface for the Slack Channel Fetcher tool.
Allows selecting a date range or fetching today's messages,
viewing formatted output, and exporting (with direct download).

Running command:
    streamlit run ui.py
"""

import json
import random
import time
import streamlit as st
from datetime import date, datetime as dt
from pathlib import Path
from slack_sdk import WebClient

# Import from refactored src module
from src import (
    SlackFetcher, DemoFetcher,
    UserCache, ChannelCache, MessageFormatter, DataExporter,
    load_config, is_demo_mode, logger,
)


# ==============================
# APP INITIALIZATION
# ==============================

# Get the project root directory (where this file is located)
PROJECT_ROOT = Path(__file__).parent
DEMO_MODE = is_demo_mode()

# Simulated-latency range for demo mode — makes the local-disk reads feel
# like a real Slack API roundtrip and gives Streamlit Cloud cold-start
# something to hide behind. Range calibrated against actual day-to-day
# experience using the original tool internally.
DEMO_DELAY_RANGE = (5.0, 9.0)

def _widget_defaults() -> dict:
    """Default values for the resettable sidebar widgets.

    Recomputed on each call so `date.today()` stays fresh if the app survives
    midnight.
    """
    return {
        "start_date_widget": date.today(),
        "end_date_widget": date.today(),
        "sort_order_widget": "Oldest First (Chronological)",
        "show_timestamps_widget": True,
        "filter_mode_widget": "None",
        "export_csv_widget": False,
        "export_json_widget": False,
    }


def reset_widget_state():
    """Schedule a widget-default reset to take effect on the next rerun.

    We do NOT delete keys here — Streamlit treats key deletion as "carry
    whatever the widget rendered" in some cases, which is why the previous
    deletion-based approach didn't visibly reset the UI. Instead we set a
    flag that the script consumes at the top of the next run, BEFORE any
    widget mounts, writing defaults straight into session_state.
    """
    st.session_state["__reset_widgets_pending__"] = True
    # `applied_filter_*` and `filter_user_widget` aren't covered by the
    # defaults dict (the filter user dropdown only renders when mode != None,
    # so it has no sensible default) — clear them explicitly so the applied
    # filter is dropped and the user picker is empty when mode is "None".
    for key in ("applied_filter_mode", "applied_filter_user_id", "filter_user_widget"):
        st.session_state.pop(key, None)


# Apply a pending widget reset BEFORE any widget renders. This is the only
# reliable spot to overwrite widget session state — once a widget has been
# instantiated, Streamlit forbids touching its key for the rest of the run.
if st.session_state.pop("__reset_widgets_pending__", False):
    for key, value in _widget_defaults().items():
        st.session_state[key] = value

# Initialize Streamlit page
st.set_page_config(page_title="Slack Channel Fetcher", layout="wide")
st.title("🗂️​​ Slack Channel Fetcher 🐕‍🦺")

if DEMO_MODE:
    st.caption("🎬 Demo mode — serving a baked sample conversation. Set `DEMO_MODE=false` and provide a `SLACK_TOKEN` to fetch from a real workspace.")

# Log session start once — Streamlit reruns the script on every widget
# interaction, so unconditional logging here was creating dozens of identical
# "Streamlit UI started" lines per visit.
if "_ui_session_started_logged" not in st.session_state:
    logger.info(f"Streamlit UI session started (demo_mode={DEMO_MODE})")
    st.session_state["_ui_session_started_logged"] = True

# Load config
config = load_config()

# APP SETUP - Paths relative to project root
if DEMO_MODE:
    USER_CACHE_FILE = str(PROJECT_ROOT / "demo" / "sample_user_map.json")
    # In demo mode the *runtime* channel cache starts empty — the user must
    # click 🔄 to "load" channels from the static source file. This mirrors
    # how real Slack mode behaves (empty cache until first refresh).
    DEMO_CHANNEL_SOURCE = PROJECT_ROOT / "demo" / "sample_channel_cache.json"
    CHANNEL_CACHE_FILE = str(PROJECT_ROOT / "demo" / "_runtime_channel_cache.json")
else:
    USER_CACHE_FILE = str(PROJECT_ROOT / "user_cache.json")
    CHANNEL_CACHE_FILE = str(PROJECT_ROOT / "channel_cache.json")
EXPORT_DIR = PROJECT_ROOT / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

# Initialize Slack client for channel fetching (real mode only)
slack_client = None if DEMO_MODE else WebClient(token=config["slack_token"])




# ==============================
# INPUTS
# ==============================

st.sidebar.header("🔧 Configuration")

# Channel Cache and Selection
channel_cache = ChannelCache(cache_file=CHANNEL_CACHE_FILE)

# In demo mode the runtime cache file doesn't exist on disk, so we use session
# state to remember that channels have been "loaded" via the refresh button.
if DEMO_MODE and "demo_channel_map" in st.session_state:
    channel_cache.channel_map = st.session_state["demo_channel_map"]

# Refresh channels button. In demo mode it simulates the API roundtrip with a
# 3.5-5.5s delay and then loads the static channel list from disk.
col_refresh1, col_refresh2 = st.sidebar.columns([3, 1])
with col_refresh2:
    if st.button("🔄", help="Refresh channel list"):
        with st.spinner("Refreshing channels..."):
            if DEMO_MODE:
                time.sleep(random.uniform(*DEMO_DELAY_RANGE))
                with open(DEMO_CHANNEL_SOURCE, encoding="utf-8") as f:
                    loaded = json.load(f)
                st.session_state["demo_channel_map"] = loaded
                channel_cache.channel_map = loaded
            else:
                channel_cache.refresh_channels(slack_client)
        reset_widget_state()
        st.rerun()

# Get channel list
channels = channel_cache.get_channel_list()

if channels:
    # Create dropdown with channel names
    channel_options = {name: cid for name, cid in channels}
    
    with col_refresh1:
        selected_channel_name = st.selectbox(
            "Select Channel",
            options=list[str](channel_options.keys()),
            help="Choose a channel to fetch messages from"
        )
    
    channel_id = channel_options[selected_channel_name]
else:
    st.sidebar.warning("⚠️ No channels found. Click 🔄 to refresh.")
    st.sidebar.info("💡 Make sure the bot is added to at least one channel in Slack.")
    channel_id = None

st.sidebar.markdown("---")

# --- Quick Fetch Section ---
st.sidebar.subheader("⚡ Fetch Today's Messages")
fetch_today_btn = st.sidebar.button(
    "Fetch Today", 
    type="primary", 
    use_container_width=True,
    help="Quickly fetch all messages from today"
)

st.sidebar.markdown("---")

# --- Date Range Section ---
st.sidebar.subheader("📅 Custom Date Range")
col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input("Start date", value=date.today(), key="start_date_widget")
end_date = col2.date_input("End date", value=date.today(), key="end_date_widget")

fetch_range_btn = st.sidebar.button(
    "Fetch Range", 
    use_container_width=True,
    help="Fetch messages from selected date range"
)

st.sidebar.markdown("---")

# --- Message ordering Section ---
st.sidebar.subheader("📊 Display Options")
sort_order = st.sidebar.radio(
    "Message Order",
    options=["Oldest First (Chronological)", "Newest First (Reverse)"],
    index=0,  # Default to chronological (oldest first)
    help="Choose how messages are displayed",
    key="sort_order_widget",
)
show_timestamps = st.sidebar.checkbox(
    "Show Timestamps", value=True, help="Display message timestamps",
    key="show_timestamps_widget",
)


st.sidebar.markdown("---")

# --- Filter Section ---
st.sidebar.subheader("🔎 Filter")

# Build two distinct user-id sets from the currently displayed messages:
#   - _author_user_ids  → only users who STARTED a top-level message
#   - _includes_user_ids → anyone who appears anywhere (parent or reply)
# The dropdown then shows the appropriate set based on the chosen filter mode.
_fetched_messages = st.session_state.get("messages") or []
_session_user_map = st.session_state.get("user_map") or {}
_author_user_ids = set()
_includes_user_ids = set()
for _m in _fetched_messages:
    if _m.get("user"):
        _author_user_ids.add(_m["user"])
        _includes_user_ids.add(_m["user"])
    for _r in _m.get("replies", []):
        if _r.get("user"):
            _includes_user_ids.add(_r["user"])

filter_mode = st.sidebar.radio(
    "Filter mode",
    options=["None", "Author", "Includes"],
    index=0,
    help=(
        "Author: only top-level messages started by the selected user.\n\n"
        "Includes: any thread where the selected user appears (parent or any reply)."
    ),
    key="filter_mode_widget",
)

if filter_mode == "Author":
    _filter_user_ids = _author_user_ids
elif filter_mode == "Includes":
    _filter_user_ids = _includes_user_ids
else:
    _filter_user_ids = set()

_filter_user_map = {uid: _session_user_map.get(uid, uid) for uid in _filter_user_ids}
_filter_user_names = sorted(_filter_user_map.values())

# DRAFT state: what the widgets currently say. Doesn't take effect until Apply.
selected_filter_user_id = None
if filter_mode != "None":
    if _filter_user_names:
        selected_user_name = st.sidebar.selectbox(
            "User", options=_filter_user_names, key="filter_user_widget",
        )
        selected_filter_user_id = next(
            (uid for uid, name in _filter_user_map.items() if name == selected_user_name),
            None,
        )
    else:
        st.sidebar.info("Fetch some messages first — the filter list is built from whoever appears in the fetched batch.")

# Apply button — commits the current draft into the APPLIED state used at
# display + export time. Hidden until there are messages to filter against.
if _fetched_messages:
    if st.sidebar.button("Apply Filter", use_container_width=True):
        st.session_state["applied_filter_mode"] = filter_mode
        st.session_state["applied_filter_user_id"] = selected_filter_user_id
        st.rerun()

st.sidebar.markdown("---")

# --- Export Section ---
export_csv = st.sidebar.checkbox("Export to CSV", value=False, key="export_csv_widget")
export_json = st.sidebar.checkbox("Export to JSON", value=False, key="export_json_widget")


def apply_filter(msgs: list[dict], mode: str, user_id: str | None) -> list[dict]:
    """Filter messages by Author (top-level only) or Includes (any thread participant)."""
    if mode == "None" or not user_id:
        return msgs
    if mode == "Author":
        return [m for m in msgs if m.get("user") == user_id]
    if mode == "Includes":
        def participates(m: dict) -> bool:
            if m.get("user") == user_id:
                return True
            return any(r.get("user") == user_id for r in m.get("replies", []))
        return [m for m in msgs if participates(m)]
    return msgs




# ==============================
# MAIN CONTENT AREA
# ==============================

# Reset button and initial instructions
col_reset, col_spacer = st.columns([1, 5])
with col_reset:
    if st.button("🔄 Reset", help="Clear results and start fresh", use_container_width=True):
        logger.info("User clicked reset button - clearing session state")
        # Clear all message-related session state (also clears the demo channel
        # map so the dropdown goes back to empty until 🔄 is clicked again).
        keys_to_clear = [
            'messages_fetched', 'messages', 'user_map', 'start_str', 'end_str',
            'sort_emoji', 'sort_order', 'demo_channel_map', 'last_fetch_summary',
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        reset_widget_state()
        st.rerun()

# Instructions - always visible, but expand/collapse based on state
is_expanded = 'messages_fetched' not in st.session_state

if is_expanded:
    st.info("👈 **Get Started:** Select a channel and date, then click a fetch button to retrieve messages!")

# Instructions card (always available, expand on first visit or after reset)
with st.expander("📖 How to Use", expanded=is_expanded):
    st.markdown("""
    **Quick Start:**
    1. 🔄 Click the refresh button in the sidebar to load your channels
    2. 📋 Select a channel from the dropdown
    3. ⚡ Click **"Fetch Today"** for today's messages, or pick a custom date range
    4. 🔀 Choose your preferred message order (oldest/newest first)
    5. 📊 Check the export options (CSV/JSON) in the sidebar
    6. 💾 Download your exports after fetching!
    
    **Note:** Export options only appear when messages are available.
    """)

st.markdown("---")





# ==============================
# ACTIONS
# ==============================

if (fetch_today_btn or fetch_range_btn) and channel_id:

    # Detect date issues BEFORE validate_date_range silently corrects them.
    # Warnings get surfaced in the UI post-rerun via session state.
    date_warnings = []
    if fetch_range_btn:
        if end_date > date.today():
            date_warnings.append(
                "⚠️ End date was in the future — capped at today."
            )
            logger.warning(f"End date {end_date} was in the future; capped at today.")
        if start_date > end_date:
            date_warnings.append(
                f"⚠️ Start date ({start_date}) was after end date ({end_date}) — dates were swapped automatically."
            )
            logger.warning(f"Start date {start_date} > end date {end_date}; swapping.")

    # Mark that messages have been fetched
    st.session_state.messages_fetched = True
    st.subheader("📤 Fetching Messages...")
    logger.info(f"User initiated message fetch for channel {channel_id}")

    spinner_msg = "Contacting Slack API..." if not DEMO_MODE else "Contacting Slack API..."
    with st.spinner(spinner_msg):

        # In demo mode, simulate the API roundtrip so the UX matches real mode.
        if DEMO_MODE:
            time.sleep(random.uniform(*DEMO_DELAY_RANGE))

        # Initialize components
        fetcher = DemoFetcher() if DEMO_MODE else SlackFetcher(token=config["slack_token"])
        cache = UserCache(cache_file=USER_CACHE_FILE)
        formatter = MessageFormatter()

        # Fetch messages (already filtered for relevance)
        if fetch_today_btn:
            messages = fetcher.fetch_today(channel_id)
            start_str = end_str = date.today().strftime("%Y-%m-%d")
        else:
            start_str, end_str = str(start_date), str(end_date)
            messages = fetcher.fetch_messages_in_range(channel_id, start_str, end_str)

        # Update user cache (skipped in demo mode — sample_user_map is pre-populated)
        if not DEMO_MODE:
            cache.update_from_messages(fetcher.client, messages)
        user_map = cache.get_map()
    
    # Sort messages based on user preference
    if sort_order == "Oldest First (Chronological)":
        messages = sorted(messages, key=lambda m: float(m.get("ts", 0)))
        sort_emoji = "⏫"
    else:  # Newest First (Reverse)
        messages = sorted(messages, key=lambda m: float(m.get("ts", 0)), reverse=True)
        sort_emoji = "⏬"
    
    # Store in session state for persistence across reruns
    st.session_state.messages = messages
    st.session_state.user_map = user_map
    st.session_state.start_str = start_str
    st.session_state.end_str = end_str
    st.session_state.sort_emoji = sort_emoji
    st.session_state.sort_order = sort_order
    # Summary banner is rendered post-rerun from this session-state entry,
    # because the widgets are about to be reset and the action block won't
    # have a chance to show them otherwise.
    st.session_state["last_fetch_summary"] = {
        "count": len(messages),
        "start": start_str,
        "end": end_str,
        "sort_label": sort_order,
        "sort_emoji": sort_emoji,
    }
    # Any date-validation warnings detected above are surfaced once on the
    # next render, then cleared (st.session_state.pop in the display block).
    st.session_state["pending_warnings"] = date_warnings

    # Reset post-process widgets so the next interaction starts from defaults
    # (no carry-over of stale filter/sort/export state from the previous run).
    reset_widget_state()
    st.rerun()

# ==============================
# DISPLAY AND EXPORT (from session state)
# ==============================
# Display messages if they exist in session state (persists across reruns)
if 'messages' in st.session_state and st.session_state.messages_fetched:
    raw_messages = st.session_state.messages
    user_map = st.session_state.user_map
    start_str = st.session_state.start_str
    end_str = st.session_state.end_str
    summary = st.session_state.get("last_fetch_summary", {})
    sort_emoji = summary.get("sort_emoji", st.session_state.get('sort_emoji', '⏫'))
    sort_label = summary.get("sort_label", st.session_state.get('sort_order', 'Oldest First (Chronological)'))

    # Render any one-shot warnings raised during the fetch (date swap, future
    # date cap). `pop` ensures they only show once and don't re-appear on the
    # next rerun (e.g. when the user clicks Apply Filter later).
    for _warning in st.session_state.pop("pending_warnings", []):
        st.warning(_warning)

    # Post-rerun summary banners (the fetch action resets widgets + reruns,
    # so the banners can't live in the action block — they live here).
    st.success(f"✅ Retrieved {len(raw_messages)} relevant messages between {start_str} and {end_str}.")
    if len(raw_messages) == 0:
        st.warning("📭 No messages found for this date range.")
        st.info("💡 Try a different date range or check if there are messages in the selected channel.")
    else:
        st.info(f"{sort_emoji} Displaying messages: **{sort_label}**")
    st.divider()

    # Apply Author/Includes filter using the APPLIED state (from session state),
    # not the current draft widget values. Filter only takes effect after the
    # "Apply Filter" sidebar button is clicked.
    applied_mode = st.session_state.get("applied_filter_mode", "None")
    applied_user_id = st.session_state.get("applied_filter_user_id")
    messages = apply_filter(raw_messages, applied_mode, applied_user_id)

    if applied_mode != "None" and applied_user_id:
        filter_user_name = user_map.get(applied_user_id, applied_user_id)
        st.info(
            f"🔎 Filter active — **{applied_mode}** = `{filter_user_name}` · "
            f"{len(messages)} of {len(raw_messages)} messages shown"
        )

    # Initialize formatter and exporter for display/export
    formatter = MessageFormatter()
    exporter = DataExporter(export_dir=str(EXPORT_DIR))
    
    # ==============================
    # DISPLAY
    # ==============================
    for m in messages:
        user_id = m.get("user", "unknown")
        user_name = user_map.get(user_id, user_id)
        text = formatter.resolve_user_mentions(
            formatter.format_slack_markup(m.get("text", "")), 
            user_map
        )
        
        # Format message with optional timestamp
        if show_timestamps:
            ts = float(m.get("ts", 0))
            timestamp = dt.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            st.markdown(f"**{user_name}** `{timestamp}`: {text}", unsafe_allow_html=True)
        else:
            st.markdown(f"**{user_name}**: {text}", unsafe_allow_html=True)
        
        # File attachments (ignoring link previews)
        for att in m.get("file_attachments", []):
            name = att.get("name", "Unnamed file")
            url = att.get("url", "#")
            mimetype = att.get("mimetype", "unknown")
            st.markdown(f"📎 [{name}]({url}) ({mimetype})")
        
        # Replies
        for r in m.get("replies", []):
            reply_user = user_map.get(r["user"], r["user"])
            reply_text = formatter.resolve_user_mentions(
                formatter.format_slack_markup(r["text"]), 
                user_map
            )
            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;↳ **{reply_user}**: {reply_text}", unsafe_allow_html=True)
            
            # Reply attachments (same as top-level messages)
            for att in r.get("file_attachments", []):
                name = att.get("name", "Unnamed file")
                url = att.get("url", "#")
                mimetype = att.get("mimetype", "unknown")
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;📎 [{name}]({url}) ({mimetype})")
        
        st.write("---")
    
    # ==============================
    # EXPORTS WITH DOWNLOAD
    # ==============================
    if messages and (export_json or export_csv):
        st.subheader("💾 Export Options")
        
        if export_json:
            # Use DataExporter to generate JSON
            json_str = exporter.generate_json_string(messages)
            st.download_button(
                label="⬇️ Download JSON",
                data=json_str.encode("utf-8"),
                file_name=f"slack_export_{start_str}_to_{end_str}.json",
                mime="application/json",
                key="download_json"  # Unique key to prevent conflicts
            )
        
        if export_csv:
            # Use DataExporter to generate CSV
            csv_str = exporter.generate_csv_string(messages, user_map)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_str.encode("utf-8-sig"),
                file_name=f"slack_export_{start_str}_to_{end_str}.csv",
                mime="text/csv",
                key="download_csv"  # Unique key to prevent conflicts
            )

    # Prompt the user to enable an export if neither is currently selected.
    # Both export checkboxes default to False after every fetch, so this
    # banner appears each time messages are first rendered until the user
    # opts in. Uses st.info (blue) to match the existing "Displaying messages"
    # banner style.
    if messages and not export_csv and not export_json:
        st.info("💡 Tick **Export to CSV** or **Export to JSON** in the sidebar to enable a download.")
