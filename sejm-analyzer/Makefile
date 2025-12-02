.PHONY: install dev lint format check test sync sync-all run clean

PACKAGES = app etl helpers sejm_client settings web tests

# Install production dependencies
install:
	pip install -e .

# Install dev dependencies
dev:
	pip install -e ".[dev]"
	pre-commit install

# Lint with ruff
lint:
	ruff check $(PACKAGES)

# Format with ruff
format:
	ruff format $(PACKAGES)
	ruff check --fix $(PACKAGES)

# Check (lint + format check, no changes)
check:
	ruff check $(PACKAGES)
	ruff format --check $(PACKAGES)

# Run tests
test:
	pytest tests/ -v

# Sync current term (10) - quick start
sync:
	@echo "Syncing current term (10)..."
	@echo "Use 'make sync-all' for all terms or 'python sync_data.py <term_numbers>'"
	python sync_data.py 10

# Sync all historical terms (7-10 have voting data)
sync-all:
	@echo "Syncing ALL terms (this takes a while)..."
	python sync_data.py all

# Sync specific terms - usage: make sync-terms TERMS="10 9 8"
sync-terms:
	@echo "Syncing terms: $(TERMS)"
	python sync_data.py $(TERMS)

# Validate data integrity
validate:
	python sync_data.py --validate

# Run streamlit app
run:
	python run.py

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Show help
help:
	@echo "Available commands:"
	@echo "  make sync        - Sync term 10 (current)"
	@echo "  make sync-all    - Sync all terms (slow)"
	@echo "  make sync-terms TERMS='10 9' - Sync specific terms"
	@echo "  make validate    - Check data integrity"
	@echo "  make run         - Start Streamlit dashboard"
	@echo "  make lint        - Check code style"
	@echo "  make format      - Format code"
	@echo "  make test        - Run tests"
