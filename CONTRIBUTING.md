# Contributing to video2pptx

## Development Setup

```bash
git clone https://github.com/kucheryavenkovn/video2pptx.git
cd video2pptx
pip install -e ".[dev]"
```

For GUI development:
```bash
pip install -e ".[gui,dev]"
```

## GRACE Methodology

This project follows the [GRACE framework](AGENTS.md). Before making changes:

1. Read the relevant `MODULE_CONTRACT` in the source file
2. Check `docs/knowledge-graph.xml` for module dependencies
3. After changes, update `docs/knowledge-graph.xml` and `docs/verification-plan.xml`
4. Record non-obvious findings in `docs/findings.md`

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Core logic only (fast)
python -m pytest tests/ -v -k "not gui"

# GUI tests (requires offscreen platform on headless)
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_gui_*.py -v

# With coverage
python -m pytest tests/ --cov=src/video2pptx --cov-report=term-missing
```

## Linting

```bash
ruff check src/ tests/
ruff check src/ tests/ --fix  # auto-fix
```

## Building

```bash
python -m build
python -m twine check dist/*
```

## Commit Style

Follow the existing GRACE commit format:

```
fix(MODULE_ID): short description

Detailed explanation of what changed and why.

F-NNNN: finding reference
```

## Pull Requests

1. Create a branch from `master`
2. Make atomic, logical commits
3. Ensure `ruff check` and `pytest` pass
4. Update `docs/findings.md` for any new discoveries
5. Reference finding IDs (F-NNNN) in commit messages
