.PHONY: quality test

quality:
	@python scripts/run_quality_checks.py

test:
	@python -m pytest
