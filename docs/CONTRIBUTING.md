# Contributing to Eidolon

Thank you for your interest in contributing to Eidolon!

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- (Optional) Docker and Docker Compose

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/polyspinor/nexus-7d.git
cd nexus-7d
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

3. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

## Development Workflow

### Code Style

We use the following tools to maintain code quality:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking
- **bandit** for security analysis

Run all checks:
```bash
make lint
```

Format code:
```bash
make format
```

### Testing

Run the test suite:
```bash
make test
```

Run specific tests:
```bash
pytest tests/test_vault.py -v
```

### Commits

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

Example:
```
feat(vault): add automatic backup scheduling

- Added cron-like scheduler for backups
- Configurable retention period
- Compression support
```

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Run tests and linting
5. Commit your changes
6. Push to your fork
7. Open a Pull Request

## Security

### Reporting Vulnerabilities

If you discover a security vulnerability, please do NOT open a public issue.

Instead, please email: security@polyspinor.io

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Security Guidelines

When contributing:

- Never commit secrets, keys, or credentials
- Use parameterized queries for any database operations
- Validate and sanitize all inputs
- Follow the principle of least privilege
- Use cryptographically secure random generators

## Architecture

```
poly_spinor_nexus_7d/
├── core/           # Core cryptographic modules
├── protocols/      # Security protocols
├── ui/             # User interfaces
├── utils/          # Utilities
├── config/         # Configuration
├── scripts/        # CLI scripts
├── vault_storage/  # Storage management
├── tests/          # Test suite
└── docker/         # Docker configuration
```

## Contact

- GitHub Issues: For bugs and feature requests
- Email: contact@polyspinor.io

Thank you for contributing!
