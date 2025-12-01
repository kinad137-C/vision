# Sejm Analyzer

Simple analytics dashboard for Polish Sejm (parliament) data.

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### 1. Sync data from Sejm API

```bash
# Sync current term only (recommended for start)
python sync_data.py current

# Sync specific terms
python sync_data.py sync --term 10 --term 9

# Sync all terms (takes a long time!)
python sync_data.py sync
```

### 2. Run dashboard

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Project Structure

```
sejm-analyzer/
├── src/
│   ├── collectors/      # Data collection from API
│   ├── db/              # Database models
│   └── analytics/       # Analytics functions
├── app.py               # Streamlit dashboard
├── sync_data.py         # CLI for data sync
└── sejm.duckdb          # DuckDB database (created after sync)
```

## Data Sources

- [Sejm API](https://api.sejm.gov.pl/) - Official Polish Parliament API

## Features

- Party cohesion analysis (Rice index)
- MP attendance tracking
- Voting distribution by party
- Club/party overview






