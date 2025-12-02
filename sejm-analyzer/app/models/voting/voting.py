"""Voting (głosowanie) model."""

VOTING_DDL = """
CREATE TABLE IF NOT EXISTS voting (
    id VARCHAR PRIMARY KEY,
    sitting_id VARCHAR,
    term_id INTEGER,
    sitting_num INTEGER,
    voting_num INTEGER,
    date TIMESTAMP,
    title VARCHAR,
    topic VARCHAR,
    yes INTEGER,
    no INTEGER,
    abstain INTEGER,
    not_voting INTEGER
)
"""

VOTING_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_voting_term ON voting(term_id)",
]
