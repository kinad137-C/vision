"""Analytics cache table - shared across all domains."""

CACHE_DDL = """
CREATE TABLE IF NOT EXISTS analytics_cache (
    term_id INTEGER NOT NULL,
    key VARCHAR NOT NULL,
    data JSON NOT NULL,
    computed_at TIMESTAMP NOT NULL,
    PRIMARY KEY (term_id, key)
)
"""
