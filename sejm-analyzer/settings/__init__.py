"""Application settings."""

import os
from pathlib import Path

# Database
DB_PATH = os.getenv("SEJM_DB_PATH", "sejm.duckdb")

# Logging
LOG_DIR = Path("logs")

# API
API_BASE_URL = "https://api.sejm.gov.pl/sejm"
API_TIMEOUT = 60

# Sync
MAX_CONCURRENT = 20
BATCH_SIZE = 50
BATCH_DELAY = 1.0
