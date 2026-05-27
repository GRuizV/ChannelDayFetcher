"""
Slack API Client
----------------
Handles all interactions with the Slack API for message fetching.
"""

import time
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .utils import validate_date_range
from .formatters import MessageFormatter
from .logger import logger


class SlackFetcher:
    """Handles fetching messages and threads from Slack channels."""
    
    def __init__(self, token: str):
        """
        Initialize Slack client.
        
        Args:
            token: Slack Bot User OAuth Token (xoxb-...)
        """
        self.client = WebClient(token=token)
        self.formatter = MessageFormatter()
        logger.info("SlackFetcher initialized")
    
    def fetch_today(self, channel_id: str) -> list[dict]:
        """
        Shortcut to fetch all messages from today.
        
        Args:
            channel_id: Slack channel ID
            
        Returns:
            List of message dictionaries
        """
        today = datetime.today().strftime("%Y-%m-%d")
        return self.fetch_messages_in_range(channel_id, today, today)
    
    def fetch_messages_in_range(
        self, 
        channel_id: str, 
        start_date: str, 
        end_date: str
    ) -> list[dict]:
        """
        Fetch all relevant messages and replies from a Slack channel between dates.
        Automatically filters out system messages, join notifications, etc.
        Includes attachments, thread replies, and date validation.
        
        Args:
            channel_id: Slack channel ID
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            
        Returns:
            List of relevant message dictionaries with threads and attachments
        """
        
        # Date validation
        start_date, end_date = validate_date_range(start_date, end_date)
        logger.info(f"Fetching messages from {start_date} to {end_date} for channel {channel_id}")
        
        start_ts = datetime.strptime(start_date, "%Y-%m-%d").timestamp()
        end_ts = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).timestamp()
        
        messages = []
        next_cursor = None
        
        try:
            # Fetch main messages with pagination
            while True:
                response = self.client.conversations_history(
                    channel=channel_id,
                    oldest=start_ts,
                    latest=end_ts,
                    inclusive=True,
                    cursor=next_cursor,
                    limit=200,
                )
                # Filter out irrelevant messages during fetch
                relevant_msgs = [
                    msg for msg in response["messages"] 
                    if self.formatter.is_relevant_message(msg)
                ]
                messages.extend(relevant_msgs)
                logger.debug(f"Fetched {len(relevant_msgs)} relevant messages from API response")
                next_cursor = response.get("response_metadata", {}).get("next_cursor")
                if not next_cursor:
                    break
            
            # Process each message for attachments and threads
            for msg in messages:
                # Extract file attachments (ignore Slack's link preview "attachments")
                if "files" in msg:
                    msg["file_attachments"] = [
                        {
                            "name": f.get("name", "Unnamed file"),
                            "mimetype": f.get("mimetype", "unknown"),
                            "url": f.get("url_private", f.get("permalink", "#")),
                        }
                        for f in msg["files"]
                    ]
                
                # Fetch thread replies
                if msg.get("reply_count", 0) > 0:
                    msg["replies"] = self._fetch_thread_replies(channel_id, msg["ts"])
        
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            print(f"❌ Slack API error: {e.response['error']}")
        
        logger.info(f"Successfully fetched {len(messages)} messages with {sum(1 for m in messages if m.get('reply_count', 0) > 0)} threads")
        return messages
    
    def _fetch_thread_replies(self, channel_id: str, message_ts: str) -> list[dict]:
        """
        Fetch all replies in a thread.
        
        Args:
            channel_id: Slack channel ID
            message_ts: Parent message timestamp
            
        Returns:
            List of reply dictionaries
        """
        replies = []
        
        try:
            replies_resp = self.client.conversations_replies(
                channel=channel_id, 
                ts=message_ts, 
                limit=200
            )
            
            # Skip first message (parent) and process replies
            for r in replies_resp["messages"][1:]:
                reply_entry = {
                    "user": r.get("user"),
                    "text": r.get("text"),
                }
                
                # Extract file attachments from replies (ignore link previews)
                if "files" in r:
                    reply_entry["file_attachments"] = [
                        {
                            "name": f.get("name", "Unnamed file"),
                            "mimetype": f.get("mimetype", "unknown"),
                            "url": f.get("url_private", f.get("permalink", "#")),
                        }
                        for f in r["files"]
                    ]
                
                replies.append(reply_entry)
        
        except SlackApiError as e:
            if e.response["error"] == "ratelimited":
                print("⏳ Rate limited while fetching replies. Retrying in 30s...")
                time.sleep(30)
                return self._fetch_thread_replies(channel_id, message_ts)
            print(f"⚠️ Could not fetch replies for {message_ts}: {e.response['error']}")
        
        return replies

