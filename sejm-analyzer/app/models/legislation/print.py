"""Print (druk sejmowy) model."""

PRINT_DDL = """
CREATE TABLE IF NOT EXISTS print (
    id VARCHAR PRIMARY KEY,
    term_id INTEGER,
    number VARCHAR,
    title VARCHAR,
    document_date DATE,
    delivery_date DATE,
    change_date TIMESTAMP,
    process_print VARCHAR
)
"""

PRINT_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_print_term ON print(term_id)",
]
