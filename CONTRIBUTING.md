# Contributing to Code Context Engine

Thanks for your interest in contributing! This guide will help you get started.

## Getting Started

1. **Fork the repo** on GitHub
2. **Clone your fork**:
   ```bash
   git clone git@github.com:YOUR_USERNAME/code-context-engine.git
   cd code-context-engine
   ```
3. **Set up the development environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```
4. **Create a branch** for your change:
   ```bash
   git checkout -b your-feature-name
   ```

## Development Workflow

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=context_engine

# Specific module
pytest tests/storage/
```

### Code Style

- Follow existing patterns in the codebase
- Use type hints for function signatures
- Keep functions focused and small
- Add docstrings for public classes and methods

### Project Structure

```
src/context_engine/
  cli.py              # CLI entry point
  config.py           # Configuration loading
  models.py           # Shared data models
  daemon.py           # Background daemon orchestrator
  event_bus.py        # Async event system
  indexer/            # Code chunking, embedding, file watching
  storage/            # sqlite-vec vectors, SQLite graph, remote backend
  retrieval/          # Hybrid search, confidence scoring
  compression/        # LLM and fallback compression
  integration/        # MCP server, session capture
```

## Submitting Changes

1. **Make sure tests pass**: `pytest`
2. **Commit with a descriptive message**:
   ```
   feat: add support for Rust tree-sitter parsing
   fix: prevent duplicate chunks on re-index
   docs: add remote mode setup guide
   ```
3. **Push your branch** and open a Pull Request
4. **Describe what your PR does** and why

## What to Work On

### Good First Issues

- Add tree-sitter support for more languages (Go, Rust, Java, C/C++)
- Improve the fallback compression for non-code files
- Add more CLI status information (chunk counts, index age)

### Larger Contributions

- Smarter graph edge detection (call graph analysis, import resolution)
- Persistent session storage with search
- Web dashboard for index inspection
- Support for additional embedding models

## Reporting Bugs

Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your Python version and OS

## Questions?

Open a discussion or issue on GitHub. We're happy to help.
