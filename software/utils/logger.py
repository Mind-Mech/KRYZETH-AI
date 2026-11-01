"""
KRYZETH Logging System
"""

import logging

from software.utils.config import LOGS, LOG_LEVEL

# Create logs folder if it doesn't exist
LOGS.mkdir(parents=True, exist_ok=True)

# Log file
LOG_FILE = LOGS / "kryzeth.log"

# Configure logger
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("KRYZETH")