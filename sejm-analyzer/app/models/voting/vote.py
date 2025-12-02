"""Vote (individual MP vote) model."""

VOTE_DDL = """
CREATE TABLE IF NOT EXISTS vote (
    id VARCHAR PRIMARY KEY,
    voting_id VARCHAR,
    mp_id VARCHAR,
    club VARCHAR,
    vote VARCHAR
)
"""

VOTE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_vote_voting ON vote(voting_id)",
    "CREATE INDEX IF NOT EXISTS idx_vote_mp ON vote(mp_id)",
    "CREATE INDEX IF NOT EXISTS idx_vote_club ON vote(club)",
]
