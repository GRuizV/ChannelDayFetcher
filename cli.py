"""
CLI Testing Module
------------------
Run core logic locally in the terminal for testing before UI integration.

Usage:
    python cli.py
"""

from datetime import datetime
from pathlib import Path
from slack_sdk import WebClient
from src import (
    SlackFetcher, DemoFetcher,
    UserCache, ChannelCache, MessageFormatter, DataExporter,
    load_config, is_demo_mode,
)


# Get the project root directory (where this file is located)
PROJECT_ROOT = Path(__file__).parent
DEMO_MODE = is_demo_mode()


def display_messages(messages: list[dict], user_map: dict[str, str]) -> None:
    """
    Pretty-print messages to console with formatting.
    
    Args:
        messages: List of message dictionaries (already filtered for relevance)
        user_map: User ID to name mapping
    """
    formatter = MessageFormatter()
    
    for m in messages:
        user_id = m.get("user", "unknown")
        user_name = user_map.get(user_id, user_id)
        text = formatter.resolve_user_mentions(
            formatter.format_slack_markup(m.get("text", "")), 
            user_map
        )
        
        print(f"\n👤 {user_name}:")
        print(f"   {text}")
        
        # Display file attachments (ignoring link previews)
        for att in m.get("file_attachments", []):
            name = att.get("name", "Unnamed file")
            url = att.get("url", "N/A")
            mimetype = att.get("mimetype", "unknown")
            print(f"   📎 {name} ({mimetype}) → {url}")
        
        # Display replies
        for r in m.get("replies", []):
            reply_user = user_map.get(r["user"], r["user"])
            reply_text = formatter.resolve_user_mentions(
                formatter.format_slack_markup(r["text"]), 
                user_map
            )
            print(f"   ↳ {reply_user}: {reply_text}")
            
            for att in r.get("file_attachments", []):
                name = att.get("name", "Unnamed file")
                url = att.get("url", "N/A")
                mimetype = att.get("mimetype", "unknown")
                print(f"      📎 {name} ({mimetype}) → {url}")
    
    print("\n" + "="*80)


def main():
    """Main CLI entry point."""

    print("\n" + "="*80)
    print("🚀 Slack Channel Fetcher - CLI Mode" + ("  🎬 DEMO" if DEMO_MODE else ""))
    print("="*80 + "\n")

    # Configuration
    config = load_config()

    # Initialize Slack client (real mode only)
    slack_client = None if DEMO_MODE else WebClient(token=config["slack_token"])

    # Cache paths differ by mode
    if DEMO_MODE:
        channel_cache_file = str(PROJECT_ROOT / "demo" / "sample_channel_cache.json")
        user_cache_file = str(PROJECT_ROOT / "demo" / "sample_user_map.json")
    else:
        channel_cache_file = str(PROJECT_ROOT / "channel_cache.json")
        user_cache_file = str(PROJECT_ROOT / "user_cache.json")

    # Initialize channel cache
    channel_cache = ChannelCache(cache_file=channel_cache_file)

    # Channel selection
    print("\n📺 Channel Selection:")
    channels = channel_cache.get_channel_list()

    if not channels and not DEMO_MODE:
        print("⚠️  No channels found in cache.")
        refresh = input("Refresh channel list? (y/n, default=y): ").strip().lower()
        if refresh != "n":
            channel_cache.refresh_channels(slack_client)
            channels = channel_cache.get_channel_list()

    if not channels:
        print("❌ No channels available. Make sure the bot is added to at least one channel.")
        return

    # Display channels
    for idx, (name, cid) in enumerate(channels, 1):
        print(f"{idx}. {name}")

    # Get user selection
    prompt_suffix = "" if DEMO_MODE else ", or 'r' to refresh"
    while True:
        choice = input(f"\nSelect channel (1-{len(channels)}{prompt_suffix}): ").strip().lower()
        if choice == 'r' and not DEMO_MODE:
            channel_cache.refresh_channels(slack_client)
            channels = channel_cache.get_channel_list()
            for idx, (name, cid) in enumerate(channels, 1):
                print(f"{idx}. {name}")
        elif choice.isdigit() and 1 <= int(choice) <= len(channels):
            selected_channel = channels[int(choice) - 1]
            channel_name, channel_id = selected_channel
            print(f"✅ Selected: {channel_name}")
            break
        else:
            print(f"⚠️  Please enter a number between 1 and {len(channels)}{prompt_suffix}")

    # Initialize components with paths relative to project root
    print("\n⚙️  Initializing components...")
    fetcher = DemoFetcher() if DEMO_MODE else SlackFetcher(token=config["slack_token"])
    cache = UserCache(cache_file=user_cache_file)
    exporter = DataExporter(export_dir=str(PROJECT_ROOT / "exports"))
    
    # Get date range from user
    print("\n📅 Date Selection:")
    print("1. Fetch today's messages")
    print("2. Fetch date range")
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    # Get sort order preference
    print("\n📊 Message Order:")
    print("1. Oldest First (Chronological)")
    print("2. Newest First (Reverse)")
    sort_choice = input("\nEnter choice (1 or 2, default=1): ").strip() or "1"
    
    if choice == "1":
        # Fetch today
        print("\n🔍 Fetching today's messages...")
        messages = fetcher.fetch_today(channel_id)
        start_date = end_date = datetime.today().strftime("%Y-%m-%d")
    else:
        # Fetch range
        start_date = input("Start date (YYYY-MM-DD): ").strip()
        end_date = input("End date (YYYY-MM-DD): ").strip()
        
        print(f"\n🔍 Fetching messages from {start_date} to {end_date}...")
        messages = fetcher.fetch_messages_in_range(channel_id, start_date, end_date)
    
    # Update user cache (skipped in demo mode — sample_user_map is pre-populated)
    if not DEMO_MODE:
        print("👥 Updating user cache...")
        cache.update_from_messages(fetcher.client, messages)
    user_map = cache.get_map()
    
    # Sort messages based on user preference
    if sort_choice == "1":
        messages = sorted(messages, key=lambda m: float(m.get("ts", 0)))
        order_label = "Oldest First (Chronological)"
    else:
        messages = sorted(messages, key=lambda m: float(m.get("ts", 0)), reverse=True)
        order_label = "Newest First (Reverse)"
    
    print(f"\n✅ Found {len(messages)} relevant messages")
    print(f"📊 Order: {order_label}")
    print("="*80)
    
    # Display messages
    display_messages(messages, user_map)
    
    # Export options
    print("\n💾 Export Options:")
    export_choice = input("Export? (j=JSON, c=CSV, b=Both, n=None): ").strip().lower()
    
    if export_choice in ['j', 'b']:
        exporter.export_json(messages, start_date, end_date)
    
    if export_choice in ['c', 'b']:
        exporter.export_csv(messages, user_map, start_date, end_date)
    
    print("\n✨ Done!")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

