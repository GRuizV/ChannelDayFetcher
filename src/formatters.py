"""
Message Formatters
------------------
Text formatting, Markdown conversion, and message filtering.
"""

import re


class MessageFormatter:
    """Handles Slack message text formatting and filtering."""
    
    @staticmethod
    def format_slack_markup(text: str) -> str:
        """
        Convert basic Slack markup into Markdown-style formatting:
        - <http://url|text> → [text](http://url)
        - *bold* → **bold**
        - _italic_ → _italic_
        - `code` → `code`
        - Retains newlines and indentation for lists or paragraphs.
        
        Args:
            text: Raw Slack message text
            
        Returns:
            Markdown-formatted text
        """
        if not text:
            return ""

        # Links: <http://url|text> → [text](http://url)
        text = re.sub(r"<(http[s]?://[^|]+)\|([^>]+)>", r"[\2](\1)", text)
        # Bold: *word* → **word**
        text = re.sub(r"\*(.*?)\*", r"**\1**", text)
        # Italic: _word_ → _\1_
        text = re.sub(r"_(.*?)_", r"_\1_", text)
        # Inline code: `code` → `code`
        text = re.sub(r"`(.*?)`", r"`\1`", text)
        # Preserve lists and spacing
        text = re.sub(r"\n•", r"\n- ", text)
        # Cleanup multiple spaces
        text = re.sub(r" {2,}", " ", text)
        # Normalize line endings
        text = text.replace("\r\n", "\n").strip()

        return text

    @staticmethod
    def resolve_user_mentions(text: str, user_map: dict[str, str]) -> str:
        """
        Replace <@UXXXXXX> with display names.
        
        Args:
            text: Text containing user mentions
            user_map: Dictionary mapping user IDs to names
            
        Returns:
            Text with resolved user mentions
        """
        if not text:
            return ""

        pattern = r"<@([A-Z0-9]+)>"

        def repl(match):
            user_id = match.group(1)
            return f"@{user_map.get(user_id, user_id)}"
            
        return re.sub(pattern, repl, text)

    @staticmethod
    def is_relevant_message(msg: dict) -> bool:
        """
        Return True if the message is relevant (user or bot content),
        False if it's a Slack system or join/notification message.
        
        Args:
            msg: Slack message dictionary
            
        Returns:
            True if message is relevant, False otherwise
        """
        # Skip Slack system subtypes
        system_subtypes = {
            "channel_join", "channel_leave", "channel_topic", "channel_purpose",
            "channel_name", "channel_archive", "bot_add", "bot_message",
            "pinned_item", "unpinned_item", "file_share", "file_comment"
        }

        if msg.get("subtype") in system_subtypes:
            return False

        # Skip "joined the channel" notifications or auto-bot echo messages
        text = msg.get("text", "").lower()
        if "has joined the channel" in text or "invited" in text:
            return False

        # Skip completely empty messages
        if not msg.get("text") and not msg.get("files"):
            return False

        return True

