PYTHON ?= python3
PIP ?= pip3
DOCKER ?= docker
COMPOSE ?= docker compose
IMAGE ?= edgeloom-dev
SITE_OUTPUT ?= _site

.PHONY: install lint format format-check test validate check \
        docker-build docker-shell docker-test site-build site-lint site-links site-check

# Editable install of the package itself, not just its dependencies. Installing
# only requirements-dev.txt leaves `edgeloom` and `ha2st_edge` unimportable and
# omits jsonschema, so the test suite cannot run.
install:
	$(PIP) install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

format-check:
	$(PYTHON) -m ruff format --check .

test:
	$(PYTHON) -m pytest tests/ translator/tests/ -vv

validate:
	$(PYTHON) -m edgeloom.cli validate auto_patch/capability-map.yaml
	$(PYTHON) -m edgeloom.cli validate auto_patch/zigbee-lock/profiles translator/ha_proxy_edge_driver/profiles

# Everything CI runs, in one target.
check: lint format-check test validate

docker-build:
	$(DOCKER) build -t $(IMAGE) .

docker-shell: docker-build
	$(COMPOSE) run --rm dev bash

docker-test: docker-build
	$(DOCKER) run --rm -v $(PWD):/workspace -w /workspace $(IMAGE) make check

site-build:
	$(PYTHON) scripts/site_build.py --output $(SITE_OUTPUT)

site-lint:
	$(PYTHON) scripts/site_check.py --lint
	node --check site/script.js

site-links:
	$(PYTHON) scripts/site_check.py --links --external

site-check: site-lint
	$(PYTHON) scripts/site_check.py --links
	$(MAKE) site-build SITE_OUTPUT=$(SITE_OUTPUT)
