# =============================================================================
# Eidolon - Makefile
# =============================================================================

.PHONY: help install install-dev test lint format clean docker-build docker-up docker-down test-rust-bridge test-rust-native test-rust-hardening build-rust-wheel install-rust-wheel verify-rust-native check-release-consistency

# Default target
help:
	@echo "Eidolon - Available commands:"
	@echo ""
	@echo "  install        Install production dependencies"
	@echo "  install-dev    Install development dependencies"
	@echo "  test           Run tests"
	@echo "  test-rust-bridge  Run Python contract checks for the Rust migration"
	@echo "  test-rust-native  Run Rust crate tests"
	@echo "  test-rust-hardening  Run the Rust migration hardening checks"
	@echo "  build-rust-wheel  Build the native eidolon_crypto wheel"
	@echo "  install-rust-wheel  Install the freshly built native wheel"
	@echo "  verify-rust-native  Verify Python sees the native bridge"
	@echo "  check-release-consistency  Verify Python/Rust release metadata policy"
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

test-rust-bridge:
	python -m unittest \
		tests.test_rust_crypto_bridge \
		tests.test_registration_server_contract \
		tests.test_server_security_contract \
		tests.test_api_server_contract \
		tests.test_avatar_transfer_contract \
		tests.test_key_revocation_contract \
		tests.test_avatar_visualization_contract \
		tests.test_avatar_merkle_tree_contract \
		tests.test_evm_wallet_contract \
		tests.test_bitcoin_wallet_contract \
		tests.test_real_post_quantum_contract \
		tests.test_persistent_vault_contract \
		tests.test_alchemy_integration_contract \
		tests.test_universal_physical_fingerprint_contract \
		tests.test_post_quantum_keys_contract

test-rust-native:
	cd rust && cargo test -p eidolon_crypto

test-rust-hardening: test-rust-bridge test-rust-native

build-rust-wheel:
	maturin build --manifest-path rust/crates/eidolon_crypto/Cargo.toml --release --interpreter python

install-rust-wheel:
	pip install --force-reinstall rust/target/wheels/eidolon_crypto-*.whl

verify-rust-native:
	python -c "from src.crypto.rust_crypto import is_rust_crypto_available; assert is_rust_crypto_available(), 'native bridge unavailable'; print('native bridge ok')"

check-release-consistency:
	python scripts/check_release_consistency.py

# -----------------------------------------------------------------------------
# Code Quality
# -----------------------------------------------------------------------------
lint:
	flake8 src/ config/ scripts/
	mypy src/ config/
	bandit -r src/ -ll

format:
	black src/ config/ scripts/
	isort src/ config/ scripts/

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
	python src/ui/launcher.py

cli:
	python src/ui/launcher.py

daemon:
	python -m src.api.server

setup:
	python src/ui/launcher.py

# -----------------------------------------------------------------------------
# Build & Release
# -----------------------------------------------------------------------------
build:
	python -m build

publish-test:
	twine upload --repository testpypi dist/*

publish:
	twine upload dist/*
