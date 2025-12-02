# Sejm Analyzer

Simple analytics dashboard for Polish Sejm (parliament) data.

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

## Usage

### 1. Sync data from Sejm API

```bash
# Sync current term only (recommended for start)
python sync_data.py

# Sync specific terms
python sync_data.py 10 9 8

# Sync all terms (takes a long time!)
python sync_data.py all

# Force re-download everything
python sync_data.py 10 --force

# Check data integrity
python sync_data.py --validate

# Recompute analytics only (no sync)
python sync_data.py --recompute
```

### 2. Run dashboard

```bash
streamlit run web/streamlit/app.py
```

Open http://localhost:8501 in your browser.

## Project Structure

```
sejm-analyzer/
├── app/                    # Application logic
│   ├── container.py        # Dependency injection container
│   ├── models/             # DDL definitions and data classes
│   │   ├── common/         # Shared models (cache, base)
│   │   ├── core/           # Core entities (term, club, mp, sitting)
│   │   ├── legislation/    # Legislative process models
│   │   └── voting/         # Voting models
│   ├── repositories/       # Data access layer
│   │   ├── base.py         # Base repository with caching
│   │   ├── db.py           # DuckDB connection management
│   │   ├── common/         # Cache repository
│   │   ├── core/           # MP repository
│   │   ├── legislation/    # Process repository
│   │   └── voting/         # Voting repository
│   └── services/           # Business logic
│       ├── dashboard/      # Dashboard aggregations
│       ├── legislation/    # Topic modeling, predictions
│       └── voting/         # Voting analytics (power indices, cohesion)
├── etl/                    # ETL pipelines
│   ├── core.py             # Sync MPs, clubs, sittings
│   ├── voting.py           # Sync votings and votes
│   ├── legislation.py      # Sync legislative processes
│   └── validation.py       # Data validation
├── helpers/                # Pure utility functions
│   └── formulas.py         # Math formulas (Shapley, Rice index, etc.)
├── sejm_client/            # Async HTTP client for Sejm API
│   ├── base.py             # Base client with retry logic
│   ├── core/               # Core API endpoints
│   ├── legislation/        # Legislation API endpoints
│   └── voting/             # Voting API endpoints
├── settings/               # Configuration
│   ├── __init__.py         # App settings (DB_PATH, API_URL, etc.)
│   └── logging.py          # Logging setup
├── web/                    # Web layer
│   ├── api/                # API views and schemas
│   │   ├── dashboard/      # Dashboard endpoints
│   │   ├── legislation/    # Legislation endpoints
│   │   └── voting/         # Voting endpoints
│   └── streamlit/          # Streamlit dashboard
│       └── app.py          # Main dashboard app
├── tests/                  # Tests
├── sync_data.py            # CLI for data sync
└── sejm.duckdb             # DuckDB database (created after sync)
```

## Data Sources

- [Sejm API](https://api.sejm.gov.pl/) - Official Polish Parliament API

## Features

- Party cohesion analysis (Rice index)
- Power indices (Shapley-Shubik, Banzhaf)
- Minimum winning coalitions
- Party agreement matrix
- Legislative topic modeling
- Pass/reject prediction model
