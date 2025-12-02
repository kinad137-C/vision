"""Sitting (posiedzenie) model."""

SITTING_DDL = """
CREATE TABLE IF NOT EXISTS sitting (
    id VARCHAR PRIMARY KEY,
    term_id INTEGER,
    number INTEGER,
    dates VARCHAR
)
"""
