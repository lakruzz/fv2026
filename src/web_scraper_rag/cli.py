"""Command-line interface for web scraper RAG tool."""

import argparse
import sys

from web_scraper_rag import __version__
from web_scraper_rag.config import load_config
from web_scraper_rag.crawler import crawl_all_parties, crawl_party


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="web-scraper-rag",
        description="Web scraper for converting party websites into RAG files for Gemini Gem",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --party alternativet --output-format markdown
  %(prog)s --all --output-format markdown
  %(prog)s --party alternativet --include-pdfs
  %(prog)s --config custom-config.yaml --all --include-pdfs
        """,
    )

    # Global options
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="config/parties.yaml",
        help="Path to configuration file (default: config/parties.yaml)",
    )
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose output",
    )
    verbosity_group.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Reduce output",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show version and exit",
    )

    # Party selection (mutually exclusive)
    selection_group = parser.add_mutually_exclusive_group(required=True)
    selection_group.add_argument(
        "-p",
        "--party",
        type=str,
        help="Name of specific party to crawl (e.g., alternativet)",
    )
    selection_group.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Crawl all parties defined in config",
    )

    # Output options
    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default="output",
        help="Output directory for generated files (default: output)",
    )
    parser.add_argument(
        "-f",
        "--output-format",
        type=str,
        choices=["markdown", "html", "text"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    # Feature flags
    parser.add_argument(
        "--include-pdfs",
        action="store_true",
        default=False,
        help="Include PDF crawling and merging",
    )
    parser.add_argument(
        "--no-follow-links",
        action="store_true",
        default=False,
        help="Only crawl the initial URL, do not follow links",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=None,
        help="Maximum crawl depth cap. If omitted, use per-party depth from config",
    )
    parser.add_argument(
        "--dryrun",
        action="store_true",
        default=False,
        help="Discover URLs and report crawl/ignore decisions without collecting content",
    )

    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    try:
        parsed_args = parse_arguments(args)
        verbose = parsed_args.verbose
        quiet = parsed_args.quiet

        # Load configuration
        config = load_config(parsed_args.config, verbose=verbose)

        # Execute appropriate action
        if parsed_args.party:
            crawl_party(
                party_name=parsed_args.party,
                config=config,
                output_dir=parsed_args.output_dir,
                output_format=parsed_args.output_format,
                include_pdfs=parsed_args.include_pdfs,
                follow_links=not parsed_args.no_follow_links,
                depth=parsed_args.depth,
                dry_run=parsed_args.dryrun,
                quiet=quiet,
                verbose=verbose,
            )
        elif parsed_args.all:
            crawl_all_parties(
                config=config,
                output_dir=parsed_args.output_dir,
                output_format=parsed_args.output_format,
                include_pdfs=parsed_args.include_pdfs,
                follow_links=not parsed_args.no_follow_links,
                depth=parsed_args.depth,
                dry_run=parsed_args.dryrun,
                quiet=quiet,
                verbose=verbose,
            )

        return 0

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if "parsed_args" in locals() and parsed_args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
