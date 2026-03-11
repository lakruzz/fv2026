# sitemix

Given a website location, sitemix scrapes content from HTML and PDF and creates a compact Markdown file — with the specific purpose of serving as RAG input or a source for LLM chat.

> A pendant to [repomix](https://github.com/yamadashy/repomix): what repomix does for code repositories, sitemix does for websites.

## Overview

Sitemix crawls websites and consolidates their content into optimised Markdown files for RAG systems and LLM chat. Configure one or more sites in a simple YAML file, then run a single command to produce clean, structured Markdown output.

## Quick Start

### Prerequisites

- Python 3.11+
- `uv` package manager (installed automatically in devcontainer)

### Installation

```bash
# Use uv to sync dependencies
uv sync --all-extras

# Or install directly
pip install -e ".[dev]"
```

### Basic Usage

```bash
# Show help
python -m sitemix --help

# Crawl a single site
python -m sitemix --site "my blog" --output-format markdown

# Crawl all configured sites
python -m sitemix --all --output-format markdown

# Crawl with PDF merging
python -m sitemix --all --include-pdfs
```

## Features

- **Domain-specific crawling** — Follows links only within the configured domain
- **Markdown output** — Optimised format for RAG systems
- **PDF merging** — Consolidates multiple PDFs per site into single documents
- **Configurable** — YAML-based site definitions
- **Flexible CLI** — Named arguments (no positional args) for intuitive usage
- **Depth control** — Crawl just the homepage (depth 0) to multiple levels (depth 2+)
- **Error resilience** — Gracefully handles network errors and continues crawling
- **Dry run mode** — Discover URLs and ignore decisions without collecting content

## Crawler Usage Examples

### Depth Parameter Explained

The `--depth` parameter controls how many levels of links to follow:

- **Depth 0** — Only homepage (~5s, 7 KB)

  ```bash
  python -m sitemix --site "my blog" --depth 0
  ```

- **Depth 1** — Homepage + all linked pages (~30-45s, 100-500 KB) — **Recommended**

  ```bash
  python -m sitemix --site "my blog" --depth 1
  ```

- **Depth 2** — Three levels deep (~2-3 min, 2-5 MB)

  ```bash
  python -m sitemix --site "my blog" --depth 2
  ```

### Common Usage Patterns

**Quick validation (just get a feel for the output):**

```bash
python -m sitemix --site "my blog" --depth 0
```

**Full site overview (most common):**

```bash
python -m sitemix --site "my blog" --depth 1
```

**Comprehensive crawl:**

```bash
python -m sitemix --site "my blog" --depth 2
```

**Crawl all configured sites:**

```bash
python -m sitemix --all --depth 1
```

**Disable link following (homepage only, same as depth 0):**

```bash
python -m sitemix --site "my blog" --no-follow-links
```

**Custom output location:**

```bash
python -m sitemix --site "my blog" --output-dir my_data/ --depth 1
```

**Quiet mode:**

```bash
python -m sitemix --site "my blog" --depth 1 --quiet
```

**Dry run (discover pages and ignore decisions only):**

```bash
python -m sitemix --site "my blog" --depth 2 --dryrun
```

**Verbose output for debugging:**

```bash
python -m sitemix --site "my blog" --depth 1 --verbose
```

## Project Structure

```txt
sitemix/
├── src/sitemix/             # Main application code
│   ├── cli.py               # CLI argument parsing
│   ├── config.py            # Configuration loading
│   ├── crawler.py           # Crawling logic
│   └── __main__.py          # Entry point
├── tests/                   # Test suite
├── output/                  # Generated files (gitignored)
├── pyproject.toml           # Project metadata & dependencies
└── README.md
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov

# Watch mode
pytest --watch
```

### Code Quality

```bash
# Check code with ruff
ruff check src/ tests/

# Auto-fix issues
ruff check --fix

# Format code
ruff format src/ tests/
```

### Adding Dependencies

```bash
# Add production dependency
uv add package-name

# Add dev-only dependency
uv add --group dev package-name
```

## Configuration

Site definitions are discovered from `./.sitemix/` in this order:

1. `./.sitemix/sites.yml`
2. `./.sitemix/sites.yaml`
3. First alphanumeric `./.sitemix/*.yml` or `./.sitemix/*.yaml`

Example config:

```yaml
sites:
  - name: "My Blog"
    website: "https://www.example.com"
    domains: ["example.com"]
    depth: 2
    ignore_urls: []
    pdf_patterns: ["*.pdf"]
    description: "My personal blog"
```

Custom config files can be specified with `--config path/to/config.yaml`.

## CLI Options

| Option                   | Short | Description              | Default                        |
| ------------------------ | ----- | ------------------------ | ------------------------------ |
| `--site NAME`            | `-s`  | Crawl specific site      | -                              |
| `--all`                  | `-a`  | Crawl all sites          | -                              |
| `--config PATH`          | `-c`  | Config file path         | Auto-discover in `./.sitemix/` |
| `--output-dir PATH`      | `-o`  | Output directory         | `output/`                      |
| `--output-format FORMAT` | `-f`  | `markdown`/`html`/`text` | `markdown`                     |
| `--include-pdfs`         | -     | Include PDF crawling     | `false`                        |
| `--no-follow-links`      | -     | Only crawl initial URL   | `false`                        |
| `--depth N`              | -     | Max crawl depth          | `2`                            |
| `--verbose`              | `-v`  | Verbose logging          | `false`                        |
| `--version`              | -     | Show version             | -                              |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.
