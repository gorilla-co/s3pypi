install:
	poetry install

test:
	tox

lint:
	tox -e lint

format:
	poetry run isort --apply
	poetry run black .

clean:
	rm -rf .coverage .eggs/ .pytest_cache/ .tox/ \
		build/ coverage/ dist/ pip-wheel-metadata/
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.egg' -exec rm -f {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +
