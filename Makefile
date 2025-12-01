.PHONY: install dev lint format check test sync run clean

# Default directory
APP_DIR = sejm-analyzer

# Install production dependencies
install:
	cd $(APP_DIR) && pip install -e .

# Install dev dependencies
dev:
	cd $(APP_DIR) && pip install -e ".[dev]"
	cd $(APP_DIR) && pre-commit install

# Lint with ruff
lint:
	cd $(APP_DIR) && ruff check src/ tests/

# Format with ruff
format:
	cd $(APP_DIR) && ruff format src/ tests/
	cd $(APP_DIR) && ruff check --fix src/ tests/

# Check (lint + format check, no changes)
check:
	cd $(APP_DIR) && ruff check src/ tests/
	cd $(APP_DIR) && ruff format --check src/ tests/

# Run tests
test:
	cd $(APP_DIR) && pytest tests/ -v

# Sync data from API
sync:
	cd $(APP_DIR) && python sync_data.py 10

# Sync all terms
sync-all:
	cd $(APP_DIR) && python sync_data.py all

# Run streamlit app
run:
	cd $(APP_DIR) && python run.py

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Pre-commit on all files
pre-commit:
	cd $(APP_DIR) && pre-commit run --all-files
