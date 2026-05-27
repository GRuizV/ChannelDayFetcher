"""
Programmatic API for Slack Channel Fetcher
-------------------------------------------
Use this module to import and use the fetcher as a library for automation,
scheduled jobs, or integration with other Python projects.

Example:
    from programmatic import fetch_and_export
    
    result = fetch_and_export(
        channel_id="C123456",
        start_date="2025-10-20",
        end_date="2025-10-24",
        export_json=True,
        export_csv=True
    )
    
    print(f"Retrieved {len(result['messages'])} messages")
    print(f"Exports saved to: {result['export_paths']}")
"""


from datetime import datetime
from pathlib import Path
from slack_sdk import WebClient
from src import SlackFetcher, UserCache, ChannelCache, DataExporter, load_config


# Get the project root directory (where this file is located)
PROJECT_ROOT = Path(__file__).parent


def fetch_and_export(
    channel_id: str,
    start_date: str,
    end_date: str,
    export_json: bool = True,
    export_csv: bool = False
) -> dict:
    """
    High-level function to fetch messages and export them.
    
    Args:
        channel_id: Slack channel ID
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        export_json: Whether to export as JSON
        export_csv: Whether to export as CSV
        
    Returns:
        Dictionary with messages, user_map, and export paths
    """
    # Load configuration (uses default location: PROJECT_ROOT/config.json)
    config = load_config()
    
    # Initialize components with paths relative to project root
    fetcher = SlackFetcher(token=config["slack_token"])
    cache = UserCache(cache_file=str(PROJECT_ROOT / "user_cache.json"))
    exporter = DataExporter(export_dir=str(PROJECT_ROOT / "exports"))
    
    # Fetch messages (already filtered for relevance)
    print(f"🔍 Fetching messages from {start_date} to {end_date}...")
    messages = fetcher.fetch_messages_in_range(channel_id, start_date, end_date)
    
    # Update user cache
    print("👥 Updating user cache...")
    cache.update_from_messages(fetcher.client, messages)
    user_map = cache.get_map()
    
    print(f"✅ Found {len(messages)} relevant messages")
    
    # Export
    result = {
        "messages": messages,
        "user_map": user_map,
        "export_paths": {}
    }
    
    if export_json:
        json_path = exporter.export_json(messages, start_date, end_date)
        result["export_paths"]["json"] = str(json_path)
    
    if export_csv:
        csv_path = exporter.export_csv(messages, user_map, start_date, end_date)
        result["export_paths"]["csv"] = str(csv_path)
    
    return result


def main():
    """
    Example usage - customize as needed.
    For interactive CLI, use: python cli.py
    """
    # Configuration
    config = load_config()
    slack_client = WebClient(token=config["slack_token"])
    
    # Get first available channel from cache
    channel_cache = ChannelCache(cache_file=str(PROJECT_ROOT / "channel_cache.json"))
    channel_id = channel_cache.get_first_channel_id()
    
    if not channel_id:
        print("⚠️ No channels found. Please run cli.py to refresh channels.")
        return
    
    start_date = "2025-10-22"
    end_date = "2025-10-23"
    
    # Fetch and export
    result = fetch_and_export(
        channel_id=channel_id,
        start_date=start_date,
        end_date=end_date,
        export_json=True,
        export_csv=True
    )
    
    print(f"\n📊 Summary:")
    print(f"   Messages: {len(result['messages'])}")
    print(f"   Users: {len(result['user_map'])}")
    print(f"   Exports: {', '.join(result['export_paths'].keys())}")


if __name__ == "__main__":
    main()
