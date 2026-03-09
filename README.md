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
python -m web_scraper_rag --all --include-pdfs
```

## Features

- **Domain-specific crawling** — Follows links only within party domain
- **Markdown output** — Optimized format for RAG systems
- **PDF merging** — Consolidates multiple PDFs per party into single documents
- **Configurable** — YAML-based party definitions with custom patterns
- **Flexible CLI** — Named arguments (no positional args) for intuitive usage
- **Depth control** — Crawl just homepage (depth 0) to multiple levels (depth 2+)
- **Error resilience** — Gracefully handles network errors and continues crawling
- **Verbose by default** — Detailed crawl output is shown unless `--quiet` is used
- **Dry run mode** — Discover URLs and ignore decisions without collecting content

## Crawler Usage Examples

### Depth Parameter Explained

The `--depth` parameter controls how many levels of links to follow:

- **Depth 0** — Only homepage (~5s, 7 KB)

  ```bash
  python -m web_scraper_rag --party alternativet --depth 0
  ```

- **Depth 1** — Homepage + all linked pages (~30-45s, 100-500 KB) — **Recommended**

  ```bash
  python -m web_scraper_rag --party alternativet --depth 1
  ```

- **Depth 2** — Three levels deep (~2-3 min, 2-5 MB)

  ```bash
  python -m web_scraper_rag --party alternativet --depth 2
  ```

### Common Usage Patterns

**Quick validation (just get a feel for the output):**

```bash
python -m web_scraper_rag --party alternativet --depth 0
```

**Full party overview (most common):**

```bash
python -m web_scraper_rag --party alternativet --depth 1
```

**Comprehensive crawl (all party info):**

```bash
python -m web_scraper_rag --party alternativet --depth 2
```

**Crawl all parties:**

```bash
python -m web_scraper_rag --all --depth 1
```

**Disable link following (homepage only, same as depth 0):**

```bash
python -m web_scraper_rag --party alternativet --no-follow-links
```

**Custom output location:**

```bash
python -m web_scraper_rag --party alternativet --output-dir my_data/ --depth 1
```

**Quiet mode:**

```bash
python -m web_scraper_rag --party alternativet --depth 1 --quiet
```

**Dry run (discover pages and ignore decisions only):**

```bash
python -m web_scraper_rag --party alternativet --depth 2 --dryrun
```

Output shows:

- Configuration loaded
- Party being crawled
- Each page being processed with depth level
- Each URL ignored by an ignore pattern, including the matching pattern
- Total pages crawled
- Final output file location
- **Depth control** — Crawl just homepage (depth 0) to multiple levels (depth 2+)
- **Error resilience** — Gracefully handles network errors and continues crawling
- **Verbose logging** — Optional stderr output for debugging

## Crawler Usage Examples

### Depth Parameter Explained

The `--depth` parameter controls how many levels of links to follow:

- **Depth 0** — Only homepage (~5s, 7 KB)

  ```bash
  python -m web_scraper_rag --party alternativet --depth 0
  ```

- **Depth 1** — Homepage + all linked pages (~30-45s, 100-500 KB) — **Recommended**

  ```bash
  python -m web_scraper_rag --party alternativet --depth 1
  ```

- **Depth 2** — Three levels deep (~2-3 min, 2-5 MB)

  ```bash
  python -m web_scraper_rag --party alternativet --depth 2
  ```

### Common Usage Patterns

**Quick validation (just get a feel for the output):**

```bash
python -m web_scraper_rag --party alternativet --depth 0 --verbose
```

**Full party overview (most common):**

```bash
python -m web_scraper_rag --party alternativet --depth 1 --verbose
```

**Comprehensive crawl (all party info):**

```bash
python -m web_scraper_rag --party alternativet --depth 2 --verbose
```

**Crawl all parties:**

```bash
python -m web_scraper_rag --all --depth 1
```

**Disable link following (homepage only, same as depth 0):**

```bash
python -m web_scraper_rag --party alternativet --no-follow-links
```

**Custom output location:**

```bash
python -m web_scraper_rag --party alternativet --output-dir my_data/ --depth 1
```

**Verbose output for debugging:**

```bash
python -m web_scraper_rag --party alternativet --depth 1 --verbose
```

Output shows:

- Configuration loaded
- Party being crawled
- Each page being processed with depth level
- Total pages crawled
- Final output file location

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

### Phase 1: Single Party Markdown ✅ **COMPLETE**

- [x] Project structure setup
- [x] CLI with argparse
- [x] Config loading & validation
- [x] Test infrastructure (35 tests passing)
- [x] Crawler implementation (Playwright + BeautifulSoup)
- [x] HTML parsing and content extraction
- [x] Markdown consolidation
- [x] Error handling and resilience

**Status:** Working and tested. Crawls party websites successfully, captures content intelligently, handles errors gracefully.

### Phase 2: All Parties Markdown

- [x] `--all` flag implementation
- [x] Batch crawling logic

### Phase 3-5: PDF Handling

- [ ] PDF discovery & download
- [ ] PDF merging

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.
