"""
Slack Channel Day Fetcher — Streamlit UI
---------------------------------------
Web interface for the Slack Channel Fetcher tool.
Allows selecting a date range or fetching today's messages,
viewing formatted output, and exporting (with direct download).

Running command:
    streamlit run ui.py
"""

import streamlit as st
from datetime import date, datetime as dt
from pathlib import Path
from slack_sdk import WebClient

# Import from refactored src module
from src import SlackFetcher, UserCache, ChannelCache, MessageFormatter, DataExporter, load_config, logger


# ==============================
# APP INITIALIZATION
# ==============================

# Get the project root directory (where this file is located)
PROJECT_ROOT = Path(__file__).parent

# Initialize Streamlit page
st.set_page_config(page_title="Slack Channel Fetcher", layout="wide")
st.title("🗂️​​ Slack Channel Fetcher 🐕‍🦺")

# Log application start
logger.info("Streamlit UI started")

# # Testing line
# st.write("✅ Streamlit is running!")

# Load config (uses default location: PROJECT_ROOT/config.json)
config = load_config()

# APP SETUP - Paths relative to project root
USER_CACHE_FILE = str(PROJECT_ROOT / "user_cache.json")
CHANNEL_CACHE_FILE = str(PROJECT_ROOT / "channel_cache.json")
EXPORT_DIR = PROJECT_ROOT / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

# Initialize Slack client for channel fetching
slack_client = WebClient(token=config["slack_token"])




# ==============================
# INPUTS
# ==============================

st.sidebar.header("🔧 Configuration")

# Channel Cache and Selection
channel_cache = ChannelCache(cache_file=CHANNEL_CACHE_FILE)

# Refresh channels button
col_refresh1, col_refresh2 = st.sidebar.columns([3, 1])
with col_refresh2:
    if st.button("🔄", help="Refresh channel list"):
        with st.spinner("Refreshing channels..."):
            channel_cache.refresh_channels(slack_client)
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
start_date = col1.date_input("Start date", value=date.today())
end_date = col2.date_input("End date", value=date.today())

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
    help="Choose how messages are displayed"
)
show_timestamps = st.sidebar.checkbox("Show Timestamps", value=True, help="Display message timestamps")


st.sidebar.markdown("---")

# --- Export Section ---
export_csv = st.sidebar.checkbox("Export to CSV", value=True)
export_json = st.sidebar.checkbox("Export to JSON", value=False)




# ==============================
# MAIN CONTENT AREA
# ==============================

# Reset button and initial instructions
col_reset, col_spacer = st.columns([1, 5])
with col_reset:
    if st.button("🔄 Reset", help="Clear results and start fresh", use_container_width=True):
        logger.info("User clicked reset button - clearing session state")
        # Clear all message-related session state
        keys_to_clear = ['messages_fetched', 'messages', 'user_map', 'start_str', 'end_str', 'sort_emoji', 'sort_order']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
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

    # Mark that messages have been fetched
    st.session_state.messages_fetched = True
    st.subheader("📤 Fetching Messages...")
    logger.info(f"User initiated message fetch for channel {channel_id}")
    
    with st.spinner("Contacting Slack API..."):
        
        # Initialize components
        fetcher = SlackFetcher(token=config["slack_token"])
        cache = UserCache(cache_file=USER_CACHE_FILE)
        formatter = MessageFormatter()
        
        # Fetch messages (already filtered for relevance)
        if fetch_today_btn:
            messages = fetcher.fetch_today(channel_id)
            start_str = end_str = date.today().strftime("%Y-%m-%d")
        else:
            start_str, end_str = str(start_date), str(end_date)
            messages = fetcher.fetch_messages_in_range(channel_id, start_str, end_str)
        
        # Update user cache
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
    
    st.success(f"✅ Retrieved {len(messages)} relevant messages between {start_str} and {end_str}.")
    
    # Check if messages exist
    if len(messages) == 0:
        st.warning("📭 No messages found for this date range.")
        st.info("💡 Try a different date range or check if there are messages in the selected channel.")
    else:
        st.info(f"{sort_emoji} Displaying messages: **{sort_order}**")
    
    st.divider()

# ==============================
# DISPLAY AND EXPORT (from session state)
# ==============================
# Display messages if they exist in session state (persists across reruns)
if 'messages' in st.session_state and st.session_state.messages_fetched:
    messages = st.session_state.messages
    user_map = st.session_state.user_map
    start_str = st.session_state.start_str
    end_str = st.session_state.end_str
    sort_emoji = st.session_state.get('sort_emoji', '⏫')
    sort_order_stored = st.session_state.get('sort_order', 'Oldest First (Chronological)')
    
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
