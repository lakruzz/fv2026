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
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose output",
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
        default=2,
        help="Maximum crawl depth for following links (default: 2)",
    )

    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    try:
        parsed_args = parse_arguments(args)

        # Load configuration
        config = load_config(parsed_args.config, verbose=parsed_args.verbose)

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
                verbose=parsed_args.verbose,
            )
        elif parsed_args.all:
            crawl_all_parties(
                config=config,
                output_dir=parsed_args.output_dir,
                output_format=parsed_args.output_format,
                include_pdfs=parsed_args.include_pdfs,
                follow_links=not parsed_args.no_follow_links,
                depth=parsed_args.depth,
                verbose=parsed_args.verbose,
            )

        return 0

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if parsed_args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
