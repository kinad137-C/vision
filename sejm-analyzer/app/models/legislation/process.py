"""Process (legislative process) model."""

PROCESS_DDL = """
CREATE TABLE IF NOT EXISTS process (
    id VARCHAR PRIMARY KEY,
    term_id INTEGER,
    number VARCHAR,
    title VARCHAR,
    document_type VARCHAR,
    document_type_enum VARCHAR,
    passed BOOLEAN,
    process_start_date DATE,
    closure_date DATE,
    change_date TIMESTAMP,
    description VARCHAR,
    title_final VARCHAR
)
"""

PROCESS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_process_term ON process(term_id)",
    "CREATE INDEX IF NOT EXISTS idx_process_passed ON process(passed)",
]
