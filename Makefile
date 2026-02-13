.PHONY: lint typecheck test check format

lint:
	ruff check sportsref_nfl/
	ruff format --check sportsref_nfl/

typecheck:
	mypy sportsref_nfl/

test:
	pytest --cov=sportsref_nfl tests/

check: lint typecheck test

format:
	ruff check --fix sportsref_nfl/
	ruff format sportsref_nfl/
