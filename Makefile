.PHONY: clean clean-test clean-pyc clean-build Makefile

clean: clean-build clean-pyc clean-tests

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	rm -fr pip-wheel-metadata/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-tests:
	rm -fr .tox/
	rm -f .coverage
	rm -fr coverave/
	rm -fr .pytest_cache/

install:
	poetry install

test:
	poetry run pytest

lint:
	poetry run flake8
	poetry run black . --check --quiet
	poetry run isort --check-only --quiet

format:
	poetry run isort --apply
	poetry run black .
