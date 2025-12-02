"""Club (klub/koło) model."""

CLUB_DDL = """
CREATE TABLE IF NOT EXISTS club (
    id VARCHAR PRIMARY KEY,
    term_id INTEGER,
    abbr VARCHAR,
    name VARCHAR,
    members_count INTEGER
)
"""
