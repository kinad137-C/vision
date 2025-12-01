"""Application settings."""

import os
from pathlib import Path

DB_PATH = os.getenv("SEJM_DB_PATH", "sejm.duckdb")
LOG_DIR = Path("logs")

API_BASE_URL = "https://api.sejm.gov.pl/sejm"
API_TIMEOUT = 60

MAX_CONCURRENT = 20
BATCH_SIZE = 50
BATCH_DELAY = 1.0
