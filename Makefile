# =============================================================================
# Poly-Spinor Nexus 7D - Makefile
# =============================================================================

.PHONY: help install install-dev test lint format clean docker-build docker-up docker-down

# Default target
help:
	@echo "Poly-Spinor Nexus 7D - Available commands:"
	@echo ""
	@echo "  install        Install production dependencies"
	@echo "  install-dev    Install development dependencies"
	@echo "  test           Run tests"
	@echo "  lint           Run linters"
	@echo "  format         Format code"
	@echo "  clean          Clean build artifacts"
	@echo "  docker-build   Build Docker images"
	@echo "  docker-up      Start Docker containers"
	@echo "  docker-down    Stop Docker containers"
	@echo "  gui            Launch GUI application"
	@echo "  cli            Launch CLI interface"
	@echo ""

# -----------------------------------------------------------------------------
# Installation
# -----------------------------------------------------------------------------
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	pre-commit install

# -----------------------------------------------------------------------------
# Testing
# -----------------------------------------------------------------------------
test:
	pytest tests/ -v --cov=core --cov=protocols --cov=ui --cov-report=html

test-fast:
	pytest tests/ -v -x --tb=short

test-unit:
	pytest tests/test_*.py -v --ignore=tests/integration/

# -----------------------------------------------------------------------------
# Code Quality
# -----------------------------------------------------------------------------
lint:
	flake8 core/ protocols/ ui/ utils/
	mypy core/ protocols/ ui/ utils/
	bandit -r core/ protocols/ -ll

format:
	black core/ protocols/ ui/ utils/ scripts/
	isort core/ protocols/ ui/ utils/ scripts/

check: lint test

# -----------------------------------------------------------------------------
# Cleaning
# -----------------------------------------------------------------------------
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# -----------------------------------------------------------------------------
# Docker
# -----------------------------------------------------------------------------
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-dev:
	docker-compose --profile dev up -d

# -----------------------------------------------------------------------------
# Application
# -----------------------------------------------------------------------------
gui:
	python launch_vault_monitor.py --gui

cli:
	python scripts/vault_launcher.py cli --vault main_vault --password

daemon:
	python scripts/vault_launcher.py daemon --vault main_vault --interval 60

setup:
	python scripts/vault_launcher.py setup

# -----------------------------------------------------------------------------
# Build & Release
# -----------------------------------------------------------------------------
build:
	python -m build

publish-test:
	twine upload --repository testpypi dist/*

publish:
	twine upload dist/*
