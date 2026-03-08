"""Web crawling functionality."""

import sys
from pathlib import Path
from typing import Any


def crawl_party(
    party_name: str,
    config: dict[str, Any],
    output_dir: str,
    output_format: str,
    include_pdfs: bool,
    _follow_links: bool,
    _depth: int,
    verbose: bool = False,
) -> None:
    """Crawl a single party website.

    Args:
        party_name: Name of the party to crawl
        config: Configuration dictionary
        output_dir: Output directory for generated files
        output_format: Output format (markdown, html, text)
        include_pdfs: Whether to include PDF crawling
        follow_links: Whether to follow links within domain
        depth: Maximum crawl depth
        verbose: Enable verbose logging
    """
    from web_scraper_rag.config import get_party_by_name

    party = get_party_by_name(config, party_name)

    if verbose:
        print(f"Crawling party: {party['name']}", file=sys.stderr)
        print(f"  Website: {party['website']}", file=sys.stderr)
        print(f"  Format: {output_format}", file=sys.stderr)
        if include_pdfs:
            print("  Including PDFs", file=sys.stderr)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # TODO: Implement actual crawling logic using Firecrawl or custom crawler
    if verbose:
        print(f"[TODO] Crawling {party['website']} -> {output_format} format", file=sys.stderr)


def crawl_all_parties(
    config: dict[str, Any],
    output_dir: str,
    output_format: str,
    include_pdfs: bool,
    follow_links: bool,
    depth: int,
    verbose: bool = False,
) -> None:
    """Crawl all parties defined in configuration.

    Args:
        config: Configuration dictionary
        output_dir: Output directory for generated files
        output_format: Output format (markdown, html, text)
        include_pdfs: Whether to include PDF crawling
        follow_links: Whether to follow links within domain
        depth: Maximum crawl depth
        verbose: Enable verbose logging
    """
    from web_scraper_rag.config import get_all_parties

    parties = get_all_parties(config)

    if verbose:
        print(f"Crawling {len(parties)} parties...", file=sys.stderr)

    for party in parties:
        crawl_party(
            party_name=party["name"],
            config=config,
            output_dir=output_dir,
            output_format=output_format,
            include_pdfs=include_pdfs,
            _follow_links=follow_links,
            _depth=depth,
            verbose=verbose,
        )

    if verbose:
        print(f"Crawling complete. Output directory: {output_dir}", file=sys.stderr)
