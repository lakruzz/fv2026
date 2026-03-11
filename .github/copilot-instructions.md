# Python Project Setup & Best Practices

This project follows established patterns from the [gh-tt](https://github.com/devx-cafe/gh-tt) project.

## Project Structure

The project is organized as follows:

```txt
fv2026/
├── .devcontainer/
│   ├── devcontainer.json (dev container config)
│   ├── postCreateCommand.sh (setup script)
│   └── .gh_alias.yml (GitHub CLI aliases)
├── .github/
│   ├── instructions/
│   │   └── sitemix-tool.instructions.md (project specs)
│   └── copilot-instructions.md (this file)
├── src/
│   └── sitemix/
│       ├── __init__.py
│       ├── __main__.py (entry point for python -m)
│       ├── cli.py (CLI with argparse)
│       ├── config.py (configuration loading)
│       └── crawler.py (crawling logic)
├── tests/
│   ├── __init__.py
│   ├── conftest.py (pytest shared fixtures)
│   ├── test_cli.py
│   └── test_config.py
├── config/
│   └── parties.yaml (party configuration)
├── output/ (generated during crawling)
├── pyproject.toml (project configuration)
├── README.md
└── .gitignore
```

## Development Tools

### Package Manager: `uv`

- **Install:** `uv sync` (syncs environment from pyproject.toml)
- **Add dependencies:** `uv add package-name` (adds to pyproject.toml)
- **Run scripts:** `uv run python -m sitemix --help`
- The devcontainer automatically runs `uv sync --all-extras` on creation

### Testing: `pytest`

- **Run tests:** `pytest` or `uv run pytest`
- **With coverage:** `pytest --cov` (configured in pyproject.toml)
- **Watch mode:** `uv run pytest --watch` (requires pytest-watch)
- **Specific test:** `pytest tests/test_cli.py::TestParseArguments::test_single_party_crawl`

### Linting & Code Quality: `ruff`

- **Check code:** `ruff check src/ tests/` or `uv run ruff check`
- **Auto-fix:** `ruff check --fix` (fixes auto-fixable issues)
- **Format:** `ruff format src/ tests/` (Python code formatting)
- Config is in `pyproject.toml` under `[tool.ruff]`

## CLI Design

The CLI uses **argparse** (no positional arguments) with a clean, documented interface.

### Command Examples

```bash
# Single party crawl (Markdown only)
python -m sitemix --site "my blog" --output-format markdown

# All parties (Markdown)
python -m sitemix --all --output-format markdown

# Single party with PDFs
python -m sitemix --site "my blog" --include-pdfs

# All parties with custom config
python -m sitemix --config custom-config.yaml --all --include-pdfs

# Using installed entry point
sitemix --all --verbose
```

### Key CLI Arguments

- `--party NAME` / `-p NAME`: Crawl specific party by name
- `--all` / `-a`: Crawl all parties from config
- `--config PATH`: Custom config file (default: `config/parties.yaml`)
- `--output-dir PATH` / `-o PATH`: Output directory (default: `output/`)
- `--output-format FORMAT` / `-f FORMAT`: Choose format (`markdown`, `html`, `text`)
- `--include-pdfs`: Include PDF crawling and merging
- `--no-follow-links`: Only crawl initial URL, don't follow links
- `--depth N`: Maximum crawl depth (default: 2)
- `--verbose` / `-v`: Verbose output (write to stderr)
- `--version`: Show version and exit
- `-h` / `--help`: Show help message

**Note:** `--party` and `--all` are mutually exclusive; one is required.

## Configuration

Configuration is stored in YAML format (`config/parties.yaml`). Each party has:

```yaml
parties:
  - name: "Party Name"
    website: "https://example.com"
    domains: ["example.com"]
    pdf_patterns: ["manifest", "program", "*.pdf"]
    description: "Party description"
```

**Key functions in `config.py`:**

- `load_config(path)` — Load YAML configuration
- `get_party_by_name(config, name)` — Get party config (case-insensitive)
- `get_all_parties(config)` — Get all parties from config
- `validate_party_config(party)` — Validate required fields

## Code Style & Standards

### Naming & Formatting

- **Module-level docstrings:** All files must have docstrings
- **Function docstrings:** Use Google-style format with Args/Returns/Raises
- **Line length:** 100 characters (configured in ruff)
- **Type hints:** Use where possible (e.g., `def foo(x: str) -> int:`)

### Best Practices

- **Error handling:** Use custom exceptions (e.g., `ConfigError`) in `config.py`
- **Type annotations:** Prefer over comments for clarity
- **Avoid print():** Use `sys.stderr` for logging: `print(msg, file=sys.stderr)`
- **DRY principle:** Extract reusable logic into functions/classes
- **Testability:** Write code that can be easily unit tested

### Ruff Rules (pyproject.toml)

Selected rules include: B (bugbear), I (isort), ERA (dead code), F (Pyflakes), S (bandit), SIM (simplify), UP (pyupgrade), N (naming), and more. See `pyproject.toml` for full list.

## Testing

### Structure

- Tests live in `tests/` folder, mirroring `src/` layout
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Writing Tests

- Use pytest fixtures from `conftest.py` (e.g., `sample_config`, `temp_dir`)
- Mock external calls with `pytest-mock`
- Aim for >80% code coverage (reported in HTML report)

### Example Test

```python
def test_my_feature(self, sample_config, temp_dir):
    """Test description."""
    result = my_function(sample_config)
    assert result == expected_value
```

## Workflow

### Daily Development

1. Make changes to code in `src/sitemix/`
2. Run tests: `pytest` or `uv run pytest`
3. Check linting: `ruff check --fix`
4. Format: `ruff format`
5. Commit and push

### Before Merging

- Ensure all tests pass: `pytest --cov`
- Fix any linting issues: `ruff check --fix && ruff format`
- Review test coverage (aim for >80%)
- Check for docstrings and type hints

### Adding Dependencies

```bash
# Production dependency
uv add package-name

# Development-only dependency
uv add --group dev package-name

# Optional extra (e.g., Firecrawl)
uv add --optional firecrawl firecrawl-py
```

## Environment Setup

The devcontainer automatically:

1. Installs Python 3.11
2. Installs `uv` package manager
3. Installs pytest
4. Runs `uv sync --all-extras` to set up virtualenv

To manually set up (outside devcontainer):

```bash
# Install uv (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Set up environment
uv sync --all-extras

# Run tests
uv run pytest
```

## Useful Commands

```bash
# Run the main script with help
uv run python -m sitemix --help

# Development: watch tests
uv run pytest --watch

# Development: format and lint all code
uv run ruff format && uv run ruff check --fix

# Production: create virtual environment
uv venv

# Production: install for CLI
uv pip install -e .
```

## Links & References

- **This Repository:** <https://github.com/lakruzz/fv2026>
- **gh-tt project:** <https://github.com/devx-cafe/gh-tt> (reference implementation for structure and best practices)
- **Ruff documentation:** <https://docs.astral.sh/ruff/>
- **Pytest documentation:** <https://docs.pytest.org/>
- **uv package manager:** <https://astral.sh/uv/>
