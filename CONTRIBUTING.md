# Contributing to Eidolon

Thank you for your interest in contributing to Eidolon! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Security](#security)

---

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Report security issues responsibly

---

## Getting Started

### Prerequisites

- Python 3.9+
- Rust 1.70+ (for crypto module development)
- Git

### Project Structure

```
eidolon/
├── src/
│   ├── daemon/          # CLI daemon (Python)
│   ├── identity/        # Vault identity management
│   ├── api/             # REST API server
│   └── ui/              # User interfaces
├── rust/
│   └── crates/
│       └── eidolon_crypto/  # Protected crypto (Rust)
├── tests/               # Test suites
├── examples/            # Usage examples
├── docs/                # Documentation
└── scripts/             # Build/utility scripts
```

---

## Development Setup

### 1. Clone the repository

```bash
git clone https://github.com/Oykdo/Eidolon.git
cd Eidolon
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate   # Windows
```

### 3. Install dependencies

```bash
pip install -e ".[dev]"
```

### 4. Install the Rust crypto module

```bash
pip install dist/eidolon_crypto-*.whl
```

### 5. Run tests

```bash
# Python tests
pytest tests/ -v

# Rust tests (if contributing to crypto)
cd rust/crates/eidolon_crypto
cargo test
```

---

## How to Contribute

### Bug Reports

Open an issue with:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Python/OS version
- Error messages/logs

### Feature Requests

Open an issue with:
- Clear description of the feature
- Use case / motivation
- Proposed API (if applicable)

### Code Contributions

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Commit with clear messages
7. Push to your fork
8. Open a Pull Request

---

## Pull Request Process

### Before submitting:

- [ ] All tests pass (`pytest tests/ -v`)
- [ ] Code follows project style
- [ ] Documentation updated (if needed)
- [ ] CHANGELOG.md updated
- [ ] No secrets or credentials in code

### PR Description should include:

- What changes were made
- Why the changes were made
- How to test the changes
- Related issue numbers

### Review Process:

1. Automated CI checks run
2. Code review by maintainers
3. Address feedback
4. Merge when approved

---

## Coding Standards

### Python

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use descriptive variable names

```python
# Good
def calculate_merkle_root(leaves: list[bytes]) -> bytes:
    """Calculate the Merkle root from leaf data."""
    ...

# Bad
def calc(l):
    ...
```

### Rust

- Follow Rust conventions
- Use `cargo fmt` before committing
- Run `cargo clippy` and address warnings
- Document public APIs

```rust
/// Generate a vault key using the holographic pipeline.
///
/// # Arguments
/// * `user_name` - The vault owner's name
/// * `enable_pq` - Whether to enable post-quantum crypto
///
/// # Returns
/// A tuple of (key_data, vault_key)
pub fn generate(user_name: &str, enable_pq: bool) -> (KeyData, [u8; 32]) {
    ...
}
```

### Commit Messages

Use conventional commits:

```
feat: add Merkle proof batching
fix: resolve race condition in registry
docs: update API documentation
test: add integration tests for ecosystem
refactor: simplify pipeline orchestration
```

---

## Security

### Reporting Vulnerabilities

**DO NOT** open public issues for security vulnerabilities.

Email security issues to: contact@polyspinor.io

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Security Guidelines

When contributing:

- Never commit secrets, keys, or credentials
- Use constant-time comparisons for sensitive data
- Validate all inputs
- Follow cryptographic best practices
- Don't implement your own crypto primitives

---

## Areas for Contribution

### Good First Issues

Look for issues labeled `good-first-issue`:
- Documentation improvements
- Test coverage
- Bug fixes with clear reproduction steps

### Advanced Contributions

- Rust crypto module improvements
- New Merkle tree features
- API server enhancements
- Performance optimizations

### Non-Code Contributions

- Documentation
- Tutorials and examples
- Translation
- Community support

---

## Questions?

- Open a Discussion on GitHub
- Check existing issues and PRs
- Read the documentation

Thank you for contributing to Eidolon! 🚀
