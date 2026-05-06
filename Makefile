unittest:
	PYTHONPATH=`pwd` python3 -m pytest tests --ignore=tests/benchmark --cov=pyplasmod -v

lint:
	PYTHONPATH=`pwd` python3 -m black pyplasmod tests --check --diff
	PYTHONPATH=`pwd` python3 -m ruff check pyplasmod tests

format:
	pip install -e ".[dev]"
	PYTHONPATH=`pwd` python3 -m black pyplasmod tests
	PYTHONPATH=`pwd` python3 -m ruff check pyplasmod tests --fix

coverage:
	PYTHONPATH=`pwd` pytest --cov=pyplasmod --ignore=tests/benchmark tests --cov-report=xml

example:
	PYTHONPATH=`pwd` python examples/example.py

example_index:
	PYTHONPATH=`pwd` python examples/example_index.py

package:
	python3 -m build --sdist --wheel --outdir dist/ .

get_proto:
	git submodule update --init

gen_proto:
	pip install -e ".[dev]"
	cd pyplasmod/grpc_gen && ./python_gen.sh

check_proto_product: gen_proto
	./check_proto_product.sh

version:
	python -m setuptools_scm

install:
	pip install -e .
