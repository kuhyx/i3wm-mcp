## Commands

- run: `i3wm-mcp`
- test: `python -m pytest -q`
- test-changed: `scripts/test_changed.sh`
- lint: `ruff check .`
- coverage: `python3 -m pytest -q --cov --cov-branch --cov-report=xml`
- coverage-gaps: `coverage-gaps coverage.xml`
