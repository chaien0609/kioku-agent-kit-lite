# Contributing to kioku-lite

Thank you for your interest in contributing to kioku-lite! This document provides guidelines and instructions for contributing.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:

   ```bash
   git clone https://github.com/<your-username>/kioku-agent-kit-lite.git
   cd kioku-agent-kit-lite
   ```

3. **Set up** the development environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[cli,dev]"
   ```

4. **Run tests** to make sure everything works:

   ```bash
   pytest
   ```

## Development Workflow

1. Create a new branch for your feature or bugfix:

   ```bash
   git checkout -b feature/my-feature
   ```

2. Make your changes, following the code style guidelines below.

3. Run tests and linting:

   ```bash
   pytest
   ruff check src/ tests/
   ```

4. Commit your changes with a clear message:

   ```bash
   git commit -m "Add: description of your change"
   ```

5. Push to your fork and open a pull request.

## Code Style

- **Formatter & Linter:** [Ruff](https://docs.astral.sh/ruff/) with a line length of 100
- **Type hints:** Use Python 3.11+ type hints (`str | None` instead of `Optional[str]`)
- **Docstrings:** Use triple-quote docstrings for public functions and classes

## Project Structure

```
src/kioku_lite/
├── service.py         # Core business logic (KiokuLiteService)
├── cli.py             # Typer CLI commands
├── config.py          # Pydantic settings
├── pipeline/          # Write path: DB, embedder, graph store
├── search/            # Read path: BM25, semantic, graph, reranker
└── storage/           # Markdown file I/O
```

## Testing

- Tests are in the `tests/` directory
- Use `pytest` to run the full suite
- Use isolated test profiles (`test-*`) — never test against production data

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_service.py -v

# Run with coverage (if installed)
pytest --cov=kioku_lite
```

## Reporting Issues

- Use [GitHub Issues](https://github.com/phuc-nt/kioku-agent-kit-lite/issues) to report bugs or request features
- Include your Python version, OS, and kioku-lite version
- For bugs, include steps to reproduce and the full error traceback

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
