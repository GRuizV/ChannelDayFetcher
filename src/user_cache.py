"""
User Cache Management
---------------------
Handles caching and retrieval of Slack user ID to name mappings.
"""

from typing import Any


import os
import json
import re
import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from .logger import logger


class UserCache:
    """Manages user ID to name mapping with persistent caching."""
    
    def __init__(self, cache_file: str = "user_cache.json"):
        """
        Initialize user cache.
        
        Args:
            cache_file: Path to cache file
        """
        self.cache_file = cache_file
        self.user_map = {}
        self.load_cache()
    
    def load_cache(self) -> None:
        """Load existing cache from file."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file) as f:
                    self.user_map = json.load(f)
            except json.JSONDecodeError:
                print("⚠️ Cache file corrupted. Rebuilding from scratch.")
                self.user_map = {}
    
    def save_cache(self) -> None:
        """Save current cache to file."""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.user_map, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to update user cache: {e}")
    
    def get_user_name(self, user_id: str) -> str:
        """
        Get user name from cache.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            User's display name or user_id if not found
        """
        return self.user_map.get(user_id, user_id)
    
    def update_from_messages(self, client: WebClient, messages: list[dict]) -> None:
        """
        Update cache with new user IDs found in messages.
        Fetches only missing users from Slack API.
        
        Args:
            client: Slack WebClient instance
            messages: List of message dictionaries
        """
        # Collect all user IDs appearing in messages + replies
        user_ids = set[Any]()
        for msg in messages:
            if "user" in msg:
                user_ids.add(msg["user"])
            
            # Extract user IDs from message text (mentions like <@U12345>)
            text = msg.get("text", "")
            user_ids.update(self._extract_user_ids_from_text(text))
            
            # Search inside replies
            for r in msg.get("replies", []):
                if "user" in r:
                    user_ids.add(r["user"])
                # Extract from reply text too
                reply_text = r.get("text", "")
                user_ids.update(self._extract_user_ids_from_text(reply_text))
        
        # Determine which users are missing from the cache
        missing_users = [uid for uid in user_ids if uid not in self.user_map]
        
        if missing_users:
            logger.info(f"Fetching {len(missing_users)} new users from Slack API")
            print(f"🔍 Found {len(missing_users)} new users to fetch from Slack...")
        
        # Fetch missing users incrementally
        for uid in missing_users:
            try:
                resp = client.users_info(user=uid)
                user = resp["user"]
                self.user_map[uid] = user.get("real_name", user.get("name", uid))
                time.sleep(1)  # Polite spacing between API calls
            except SlackApiError as e:
                if e.response["error"] == "ratelimited":
                    print("⏳ Rate limited. Waiting 30s before retry...")
                    time.sleep(30)
                    continue
                print(f"⚠️ Could not fetch info for {uid}: {e.response['error']}")
        
        # Save updated cache
        if missing_users:
            self.save_cache()
    
    def _extract_user_ids_from_text(self, text: str) -> set:
        """
        Extract user IDs from text mentions like <@U12345>.
        
        Args:
            text: Message text
            
        Returns:
            Set of user IDs found in the text
        """
        if not text:
            return set()
        
        pattern = r"<@([A-Z0-9]+)>"
        return set(re.findall(pattern, text))
    
    def get_map(self) -> dict[str, str]:
        """
        Get the complete user map.
        
        Returns:
            Dictionary mapping user IDs to names
        """
        return self.user_map

