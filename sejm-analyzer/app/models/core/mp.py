"""MP (poseł) model."""

MP_DDL = """
CREATE TABLE IF NOT EXISTS mp (
    id VARCHAR PRIMARY KEY,
    term_id INTEGER,
    mp_id INTEGER,
    first_name VARCHAR,
    last_name VARCHAR,
    club VARCHAR,
    district VARCHAR,
    active BOOLEAN
)
"""

MP_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_mp_term ON mp(term_id)",
]
