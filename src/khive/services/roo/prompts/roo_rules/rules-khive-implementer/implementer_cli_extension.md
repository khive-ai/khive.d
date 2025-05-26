# ⚙️ Implementer CLI Extension

_You have all global commands plus:_

## Implementer Development Tools

### khive new-doc - Your Templates

- `khive new-doc IP <issue>` - Implementation Plan (PRIMARY)
- `khive new-doc TI <issue>` - Test Implementation (when needed)

### Python Development (FULL DOCS)

# Environment setup

khive init # Initialize all dependencies uv sync # Sync Python dependencies uv
pip install <package> # Add new dependency

# Testing (FULL DOCS)

khive ci # Run all tests uv run pytest tests/ # Run Python tests uv run pytest
--cov=src --cov-report=term # Coverage uv run pytest -xvs tests/test_specific.py

# Debug one test

# Code Quality (FULL DOCS)

khive fmt # Format all code uv run pre-commit run --all-files # All hooks uv run
mypy src/ # Type checking uv run ruff check # Linting

### khive pr - Create Pull Requests

[FULL documentation]

### TDD Workflow

[Full TDD examples with pytest]

### Development Commands

```bash
# Initialize project
khive init            # Sets up all dependencies

# Test everything
khive ci              # Runs all tests for all languages
uv run pytest         # Python-specific tests
uv run pytest --cov=src --cov-report=term  # With coverage

# Format code
khive fmt             # Formats all code
uv run pre-commit run --all-files  # Pre-commit hooks

# TDD Helper
echo "def test_feature():\n    assert False" > test_feature.py
uv run pytest test_feature.py -v
```
