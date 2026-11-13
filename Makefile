.PHONY: help install data build audit robustness simulate report all demo validate test notebooks upload lint format docs serve clean-demo

PY ?= python
export NO_MKDOCS_2_WARNING = 1

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install:  ## Install the package with dev and notebook tools
	$(PY) -m pip install -e ".[dev,notebooks]"

data:  ## Download ITER and RWI into data/raw
	mapaudit download

build:  ## Build locality and tile tables from data/raw
	mapaudit build

audit:  ## Audit the RWI against the census
	mapaudit audit

robustness:  ## Robustness checks from the pre-analysis plan
	mapaudit robustness

simulate:  ## Survey simulation + challenger models (needs satellite features)
	mapaudit simulate

report:  ## Figures + docs/results.md
	mapaudit report

all: build audit robustness simulate report  ## Full real-data pipeline

demo:  ## Run everything on synthetic data (fast; what CI runs)
	mapaudit demo

validate:  ## Planted-bias validation on synthetic worlds
	mapaudit validate

test:  ## Run tests
	$(PY) -m pytest

notebooks:  ## Execute notebooks 01-06 in demo mode (what CI does)
	MAPAUDIT_NOTEBOOK_MODE=demo $(PY) -m pytest --nbmake notebooks/0[1-6]_*.ipynb -o addopts=""

upload:  ## Stage new/changed files in upload/ for GitHub's web uploader
	mapaudit upload

lint:  ## Lint and format check
	ruff check src tests scripts
	ruff format --check src tests scripts

format:  ## Auto-format
	ruff format src tests scripts
	ruff check --fix src tests scripts

docs:  ## Build the documentation site
	mkdocs build --strict

serve:  ## Preview the documentation site at http://127.0.0.1:8000
	mkdocs serve

clean-demo:  ## Delete synthetic data and demo results
	rm -rf data/demo results/demo
