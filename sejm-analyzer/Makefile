.PHONY: install dev lint format check test sync run clean

# Install production dependencies
install:
	pip install -e .

# Install dev dependencies
dev:
	pip install -e ".[dev]"
	pre-commit install

# Lint with ruff
lint:
	ruff check src/ tests/

# Format with ruff
format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

# Check (lint + format check, no changes)
check:
	ruff check src/ tests/
	ruff format --check src/ tests/

# Run tests
test:
	pytest tests/ -v

# Sync data from API
sync:
	python sync_data.py 10

# Sync all terms
sync-all:
	python sync_data.py all

# Run streamlit app
run:
	python run.py

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Pre-commit on all files
pre-commit:
	pre-commit run --all-files
