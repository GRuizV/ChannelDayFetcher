"""
Logging Configuration
---------------------
Centralized logging setup for the Slack Channel Fetcher application.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = "ChannelFetcher", log_level: str = "INFO") -> logging.Logger:
    """
    Set up and configure the application logger.
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler (detailed logs)
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Suppress overly verbose libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('slack_sdk').setLevel(logging.WARNING)
    
    logger.info("=" * 60)
    logger.info(f"Logging initialized - Level: {log_level}")
    logger.info("=" * 60)
    
    return logger


# Create default logger instance
logger = setup_logger()

