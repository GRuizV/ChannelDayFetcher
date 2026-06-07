"""
DemoFetcher
-----------
Drop-in replacement for SlackFetcher that serves pre-baked conversations
from demo/pool/*.json. Used when DEMO_MODE is enabled so the deployed
Streamlit Cloud app never depends on a live Slack workspace.

Each message template in a pool stores `days_ago` and `time_of_day` instead
of an absolute timestamp. At fetch time, those are rebased against today's
wall clock — so the demo always shows "fresh" messages and the same fetch
on the same day always returns the same result (deterministic).
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from .utils import validate_date_range
from .logger import logger


PROJECT_ROOT = Path(__file__).parent.parent
POOL_DIR = PROJECT_ROOT / "demo" / "pool"
CHANNEL_CACHE_FILE = PROJECT_ROOT / "demo" / "sample_channel_cache.json"


_CHANNEL_ID_TO_POOL = {
    "C_DEMO_GEN": "general",
    "C_DEMO_ENG": "engineering",
    "C_DEMO_ANN": "announcements",
}


class DemoFetcher:
    """Serves a deterministic, rebased view of pre-baked Slack-shaped messages."""

    def __init__(self):
        self.client = None
        self._pools = {}
        for channel_id, pool_name in _CHANNEL_ID_TO_POOL.items():
            pool_path = POOL_DIR / f"{pool_name}.json"
            with open(pool_path, encoding="utf-8") as f:
                self._pools[channel_id] = json.load(f)
        logger.info(f"DemoFetcher loaded {len(self._pools)} channel pools")

    def fetch_today(self, channel_id: str) -> list[dict]:
        today = datetime.today().strftime("%Y-%m-%d")
        return self.fetch_messages_in_range(channel_id, today, today)

    def fetch_messages_in_range(
        self,
        channel_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict]:
        start_date, end_date = validate_date_range(start_date, end_date)
        logger.info(f"[demo] Fetching {channel_id} from {start_date} to {end_date}")

        pool = self._pools.get(channel_id)
        if pool is None:
            logger.warning(f"[demo] No pool found for channel {channel_id}")
            return []

        now = datetime.now()
        start_ts = datetime.strptime(start_date, "%Y-%m-%d").timestamp()
        end_ts = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).timestamp()

        results = []
        for template in pool:
            msg = self._rebase(template, now)
            ts = float(msg["ts"])
            if start_ts <= ts < end_ts:
                results.append(msg)

        logger.info(f"[demo] Returning {len(results)} messages")
        return results

    @staticmethod
    def _rebase(template: dict, now: datetime) -> dict:
        days_ago = template.get("days_ago", 0)
        time_of_day = template.get("time_of_day", "12:00:00")
        hour, minute, second = (int(x) for x in time_of_day.split(":"))

        msg_dt = (now - timedelta(days=days_ago)).replace(
            hour=hour, minute=minute, second=second, microsecond=0
        )
        ts = str(msg_dt.timestamp())

        msg = {
            "user": template["user"],
            "text": template.get("text", ""),
            "ts": ts,
            "type": "message",
        }

        if template.get("file_attachments"):
            msg["file_attachments"] = template["file_attachments"]

        if template.get("replies"):
            msg["reply_count"] = len(template["replies"])
            msg["replies"] = template["replies"]

        return msg
