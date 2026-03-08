# fv2026 - Danish Election RAG Gem

Web scraper tool for creating RAG (Retrieval-Augmented Generation) files from Danish political party websites for use with Gemini Gem.

## Overview

This project crawls Danish political party websites and consolidates their programs, manifestos, and policy documents into optimized formats for RAG systems. Users can then upload these files to a Gemini Gem to enable semantic search and retrieval of party policy information.

**Goal:** Help Danish voters understand which political party's platform aligns best with their values by enabling conversational AI to retrieve and match party positions on key issues.

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
python -m web_scraper_rag --help

# Crawl a single party
python -m web_scraper_rag --party alternativet --output-format markdown

# Crawl all parties
python -m web_scraper_rag --all --output-format markdown

# Crawl with PDF merging
python -m web_scraper_rag --all --include-pdfs --verbose
```

## Features

- **Domain-specific crawling** — Follows links only within party domain
- **Markdown output** — Optimized format for RAG systems
- **PDF merging** — Consolidates multiple PDFs per party into single documents
- **Configurable** — YAML-based party definitions with custom patterns
- **Flexible CLI** — Named arguments (no positional args) for intuitive usage

## Project Structure

```txt
fv2026/
├── src/web_scraper_rag/     # Main application code
│   ├── cli.py               # CLI argument parsing
│   ├── config.py            # Configuration loading
│   ├── crawler.py           # Crawling logic
│   └── __main__.py          # Entry point
├── tests/                    # Test suite
├── config/
│   └── parties.yaml         # Party configurations
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

# Add optional extra (e.g., Firecrawl)
uv add --optional firecrawl firecrawl-py
```

## Configuration

Party websites are defined in `config/parties.yaml`:

```yaml
parties:
  - name: "Alternativet"
    website: "https://www.alternativet.dk"
    domains: ["alternativet.dk"]
    pdf_patterns: ["manifest", "program", "*.pdf"]
    description: "The Alternative – An idealistic political party"
```

Custom config files can be specified with `--config path/to/config.yaml`.

## CLI Options

| Option                   | Short | Description              | Default               |
| ------------------------ | ----- | ------------------------ | --------------------- |
| `--party NAME`           | `-p`  | Crawl specific party     | -                     |
| `--all`                  | `-a`  | Crawl all parties        | -                     |
| `--config PATH`          | `-c`  | Config file path         | `config/parties.yaml` |
| `--output-dir PATH`      | `-o`  | Output directory         | `output/`             |
| `--output-format FORMAT` | `-f`  | `markdown`/`html`/`text` | `markdown`            |
| `--include-pdfs`         | -     | Include PDF crawling     | `false`               |
| `--no-follow-links`      | -     | Only crawl initial URL   | `false`               |
| `--depth N`              | -     | Max crawl depth          | `2`                   |
| `--verbose`              | `-v`  | Verbose logging          | `false`               |
| `--version`              | -     | Show version             | -                     |

## Implementation Status

### Phase 1: Single Party Markdown ✅

- [x] Project structure setup
- [x] CLI with argparse
- [x] Config loading & validation
- [x] Test infrastructure
- [ ] Actual crawling implementation (Firecrawl or DIY)

### Phase 2: All Parties Markdown

- [ ] `--all` flag implementation
- [ ] Batch crawling logic

### Phase 3-5: PDF Handling

- [ ] PDF discovery & download
- [ ] PDF merging

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.
