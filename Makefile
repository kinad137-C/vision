.PHONY: install dev lint format check test sync run clean

# Default directory
APP_DIR = sejm-analyzer
PACKAGES = app etl helpers sejm_client settings web tests

# Install production dependencies
install:
	cd $(APP_DIR) && pip install -e .

# Install dev dependencies
dev:
	cd $(APP_DIR) && pip install -e ".[dev]"
	cd $(APP_DIR) && pre-commit install

# Lint with ruff
lint:
	cd $(APP_DIR) && ruff check $(PACKAGES)

# Format with ruff
format:
	cd $(APP_DIR) && ruff format $(PACKAGES)
	cd $(APP_DIR) && ruff check --fix $(PACKAGES)

# Check (lint + format check, no changes)
check:
	cd $(APP_DIR) && ruff check $(PACKAGES)
	cd $(APP_DIR) && ruff format --check $(PACKAGES)

# Run tests
test:
	cd $(APP_DIR) && pytest tests/ -v

# Sync data from API
sync:
	cd $(APP_DIR) && python sync_data.py 10

# Sync all terms
sync-all:
	cd $(APP_DIR) && python sync_data.py all

# Force sync all terms (re-download everything)
sync-force:
	cd $(APP_DIR) && python sync_data.py all --force

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
