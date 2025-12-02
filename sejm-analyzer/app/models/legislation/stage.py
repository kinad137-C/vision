"""Process stage model."""

PROCESS_STAGE_DDL = """
CREATE TABLE IF NOT EXISTS process_stage (
    id VARCHAR PRIMARY KEY,
    process_id VARCHAR,
    stage_name VARCHAR,
    stage_type VARCHAR,
    date DATE,
    sitting_num INTEGER,
    decision VARCHAR,
    committee_code VARCHAR,
    voting_id VARCHAR
)
"""

PROCESS_STAGE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_stage_process ON process_stage(process_id)",
    "CREATE INDEX IF NOT EXISTS idx_stage_voting ON process_stage(voting_id)",
]
