unittest:
	PYTHONPATH=`pwd` python3 -m pytest tests -cov=pyplasmod -v

lint:
	PYTHONPATH=`pwd` python3 -m black pyplasmod tests examples scripts/sdk_checks --check --diff
	PYTHONPATH=`pwd` python3 -m ruff check pyplasmod tests examples scripts/sdk_checks

format:
	pip install -e ".[dev]"
	PYTHONPATH=`pwd` python3 -m black pyplasmod tests examples scripts/sdk_checks
	PYTHONPATH=`pwd` python3 -m ruff check pyplasmod tests examples scripts/sdk_checks --fix

coverage:
	PYTHONPATH=`pwd` pytest --cov=pyplasmod tests --cov-report=xml

version:
	python -m setuptools_scm

install:
	pip install -e .
