"""Term (kadencja) model."""

TERM_DDL = """
CREATE TABLE IF NOT EXISTS term (
    id INTEGER PRIMARY KEY,
    from_date DATE NOT NULL,
    to_date DATE,
    current BOOLEAN DEFAULT FALSE
)
"""
