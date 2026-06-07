"""
Utility Functions
-----------------
Configuration loading and date validation helpers.
"""

import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv


# Get the project root directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent

# Load .env file if it exists (for local development)
load_dotenv(PROJECT_ROOT / ".env")


def is_demo_mode() -> bool:
    """True when DEMO_MODE env var is set. Used by entry points to swap in DemoFetcher."""
    return os.getenv("DEMO_MODE", "").lower() == "true"


def load_config() -> dict:
    """
    Load configuration from environment variables.

    Supports:
    - .env file (local development - auto-loaded)
    - Environment variables (production deployment)
    - Streamlit secrets (Streamlit Cloud)

    In demo mode (DEMO_MODE=true), SLACK_TOKEN is not required.

    Returns:
        Dictionary with configuration values

    Raises:
        ValueError: If SLACK_TOKEN is not found and demo mode is not enabled
    """
    if is_demo_mode():
        return {"slack_token": None, "demo_mode": True}

    slack_token = os.getenv("SLACK_TOKEN")

    if not slack_token:
        raise ValueError(
            "❌ SLACK_TOKEN not found!\n\n"
            "For local development:\n"
            "  1. Copy env.example to .env\n"
            "  2. Add your token: SLACK_TOKEN=xoxb-your-token\n\n"
            "For deployment:\n"
            "  Set SLACK_TOKEN as environment variable in your platform\n\n"
            "Or, to run against the baked demo dataset: set DEMO_MODE=true"
        )

    return {"slack_token": slack_token, "demo_mode": False}


def validate_date_range(start_date: str, end_date: str) -> tuple[str, str]:
    """
    Validate and correct the date range.
    - start_date can't be later than end_date.
    - end_date can't be in the future (defaults to today).
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        Tuple of sanitized (start_date, end_date) as YYYY-MM-DD strings
        
    Raises:
        ValueError: If date format is invalid
    """
    today = datetime.today().date()

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Invalid start_date format. Expected YYYY-MM-DD.")

    try:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Invalid end_date format. Expected YYYY-MM-DD.")

    # If end_date > today → cap at today
    if end_dt > today:
        print("⚠️ End date is in the future. Defaulting to today.")
        end_dt = today

    # If start_date > end_date → swap or correct
    if start_dt > end_dt:
        print("⚠️ Start date is after end date. Swapping values.")
        start_dt, end_dt = end_dt, start_dt

    return (start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))

