"""
Data Exporters
--------------
Export messages to various formats (JSON, CSV).
"""

import json
import csv
from pathlib import Path
from datetime import datetime

from .formatters import MessageFormatter
from .logger import logger


class DataExporter:
    """
    Handles exporting messages to different file formats.
    
    Usage Patterns:
    ---------------
    • File-based exports (CLI & Programmatic):
      - export_json() → Saves to file system
      - export_csv()  → Saves to file system
    
    • In-memory exports (UI):
      - generate_json_string() → Returns JSON string for download buttons
      - generate_csv_string()  → Returns CSV string for download buttons
    
    Note: UI uses in-memory methods because Streamlit download buttons
    need data as strings, not file paths.
    """
    
    def __init__(self, export_dir: str = "exports"):
        """
        Initialize exporter.
        
        Args:
            export_dir: Directory to save export files
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True)
        self.formatter = MessageFormatter()
    
    def generate_filename(
        self, 
        start_date: str, 
        end_date: str, 
        format_ext: str
    ) -> Path:
        """
        Generate standardized filename for exports.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            format_ext: File extension (json, csv)
            
        Returns:
            Path object with full filename
        """
        return self.export_dir / f"slack_export_{start_date}_to_{end_date}.{format_ext}"
    
    def export_json(
        self, 
        messages: list[dict], 
        start_date: str, 
        end_date: str
    ) -> Path:
        """
        Save full message data (with threads & attachments) as JSON.
        
        Used by: CLI, Programmatic API
        
        Args:
            messages: List of message dictionaries
            start_date: Start date for filename
            end_date: End date for filename
            
        Returns:
            Path to saved file
        """
        filename = self.generate_filename(start_date, end_date, "json")
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        
        logger.info(f"JSON export saved: {filename} ({len(messages)} messages)")
        print(f"💾 JSON export saved to {filename}")
        return filename
    
    def export_csv(
        self, 
        messages: list[dict], 
        user_map: dict[str, str], 
        start_date: str, 
        end_date: str
    ) -> Path:
        """
        Flatten messages & replies into a CSV file.
        Each reply is its own row with a reference to the parent timestamp.
        Properly resolves user names, formats text, and preserves UTF-8 characters.
        
        Used by: CLI, Programmatic API
        
        Args:
            messages: List of message dictionaries
            user_map: Dictionary mapping user IDs to names
            start_date: Start date for filename
            end_date: End date for filename
            
        Returns:
            Path to saved file
        """
        filename = self.generate_filename(start_date, end_date, "csv")
        rows = []
        
        for msg in messages:
            # Convert timestamp to human-readable format
            ts = msg.get("ts")
            if ts:
                timestamp = datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp = ""
            
            # Top-level message
            base = {
                "timestamp": timestamp,
                "user": user_map.get(msg.get("user"), msg.get("user", "Unknown")),
                "text": self.formatter.resolve_user_mentions(
                    self.formatter.format_slack_markup(msg.get("text", "")), 
                    user_map
                ),
                "has_file_attachments": "file_attachments" in msg,
                "reply_to": None
            }
            rows.append(base)
            
            # Replies
            for r in msg.get("replies", []):
                rows.append({
                    "timestamp": "",  # Replies don't have separate timestamps
                    "user": user_map.get(r.get("user"), r.get("user", "Unknown")),
                    "text": self.formatter.resolve_user_mentions(
                        self.formatter.format_slack_markup(r.get("text", "")), 
                        user_map
                    ),
                    "has_file_attachments": "file_attachments" in r,
                    "reply_to": timestamp  # Reference parent message timestamp
                })
        
        # Use UTF-8-SIG for Excel compatibility
        if rows:
            with open(filename, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter=";")
                writer.writeheader()
                writer.writerows(rows)
        
        logger.info(f"CSV export saved: {filename} ({len(rows)} total rows)")
        print(f"💾 CSV export saved to {filename}")
        return filename
    
    def generate_json_string(self, messages: list[dict]) -> str:
        """
        Generate JSON string for in-memory use (e.g., download buttons).
        
        Used by: UI (Streamlit download buttons)
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            JSON string
        """
        return json.dumps(messages, ensure_ascii=False, indent=2)
    
    def generate_csv_string(
        self, 
        messages: list[dict], 
        user_map: dict[str, str]
    ) -> str:
        """
        Generate CSV string for in-memory use (e.g., download buttons).
        
        Used by: UI (Streamlit download buttons)
        
        Args:
            messages: List of message dictionaries
            user_map: Dictionary mapping user IDs to names
            
        Returns:
            CSV string with UTF-8-SIG encoding
        """
        rows = []
        
        for msg in messages:
            # Convert timestamp to human-readable format
            ts = msg.get("ts")
            if ts:
                timestamp = datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp = ""
            
            # Top-level message
            base = {
                "timestamp": timestamp,
                "user": user_map.get(msg.get("user"), msg.get("user", "Unknown")),
                "text": self.formatter.resolve_user_mentions(
                    self.formatter.format_slack_markup(msg.get("text", "")), 
                    user_map
                ),
                "has_file_attachments": "file_attachments" in msg,
                "reply_to": None
            }
            rows.append(base)
            
            # Replies
            for r in msg.get("replies", []):
                rows.append({
                    "timestamp": "",
                    "user": user_map.get(r.get("user"), r.get("user", "Unknown")),
                    "text": self.formatter.resolve_user_mentions(
                        self.formatter.format_slack_markup(r.get("text", "")), 
                        user_map
                    ),
                    "has_file_attachments": "file_attachments" in r,
                    "reply_to": timestamp
                })
        
        # Generate CSV string
        if rows:
            import io
            csv_buffer = io.StringIO()
            writer = csv.DictWriter(csv_buffer, fieldnames=rows[0].keys(), delimiter=";")
            writer.writeheader()
            writer.writerows(rows)
            return csv_buffer.getvalue()
        
        return ""

