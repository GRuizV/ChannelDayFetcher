"""
Channel Cache Management
------------------------
Handles caching and retrieval of Slack channels the bot has access to.
"""

import os
import json
import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from .logger import logger


class ChannelCache:
    """Manages channel ID to name mapping with persistent caching."""
    
    def __init__(self, cache_file: str = "channel_cache.json"):
        """
        Initialize channel cache.
        
        Args:
            cache_file: Path to cache file
        """
        self.cache_file = cache_file
        self.channel_map = {}
        self.load_cache()
    
    def load_cache(self) -> None:
        """Load existing cache from file."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file) as f:
                    self.channel_map = json.load(f)
            except json.JSONDecodeError:
                print("⚠️ Channel cache file corrupted. Will rebuild on refresh.")
                self.channel_map = {}
    
    def save_cache(self) -> None:
        """Save current cache to file."""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.channel_map, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to update channel cache: {e}")
    
    def refresh_channels(self, client: WebClient) -> dict[str, str]:
        """
        Fetch all channels (public and private) that the bot is a member of.
        Updates the cache and returns the channel map.
        
        Args:
            client: Slack WebClient instance
            
        Returns:
            Dictionary mapping channel IDs to names
        """
        print("🔄 Refreshing channel list...")
        logger.info("Refreshing channel list from Slack API")
        self.channel_map = {}
        
        try:
            # Fetch all conversation types where bot is a member
            # types: public_channel, private_channel
            response = client.conversations_list(
                types="public_channel,private_channel",
                exclude_archived=True,
                limit=200
            )
            
            for channel in response["channels"]:
                # Only include channels where the bot is a member
                if channel.get("is_member", False):
                    channel_id = channel["id"]
                    channel_name = channel["name"]
                    self.channel_map[channel_id] = f"#{channel_name}"
            
            # Handle pagination if there are more channels
            while response.get("response_metadata", {}).get("next_cursor"):
                cursor = response["response_metadata"]["next_cursor"]
                response = client.conversations_list(
                    types="public_channel,private_channel",
                    exclude_archived=True,
                    limit=200,
                    cursor=cursor
                )
                
                for channel in response["channels"]:
                    if channel.get("is_member", False):
                        channel_id = channel["id"]
                        channel_name = channel["name"]
                        self.channel_map[channel_id] = f"#{channel_name}"
                
                time.sleep(1)  # Rate limiting
            
            # Save updated cache
            self.save_cache()
            logger.info(f"Found and cached {len(self.channel_map)} channels")
            print(f"✅ Found {len(self.channel_map)} channels where bot is a member")
            
        except SlackApiError as e:
            if e.response["error"] == "ratelimited":
                print("⏳ Rate limited. Please try again in a moment.")
            else:
                print(f"⚠️ Error fetching channels: {e.response['error']}")
        
        return self.channel_map
    
    def get_channel_name(self, channel_id: str) -> str:
        """
        Get channel name from cache.
        
        Args:
            channel_id: Slack channel ID
            
        Returns:
            Channel name or channel_id if not found
        """
        return self.channel_map.get(channel_id, channel_id)
    
    def get_map(self) -> dict[str, str]:
        """
        Get the complete channel map.
        
        Returns:
            Dictionary mapping channel IDs to names
        """
        return self.channel_map
    
    def get_channel_list(self) -> list[tuple[str, str]]:
        """
        Get list of channels as (name, id) tuples, sorted by name.
        
        Returns:
            List of (channel_name, channel_id) tuples
        """
        return sorted(
            [(name, cid) for cid, name in self.channel_map.items()],
            key=lambda x: x[0].lower()
        )
    
    def get_first_channel_id(self) -> str | None:
        """
        Get the ID of the first channel (alphabetically).
        
        Returns:
            First channel ID or None if no channels
        """
        channels = self.get_channel_list()
        return channels[0][1] if channels else None

