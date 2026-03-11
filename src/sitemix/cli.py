"""Command-line interface for web scraper RAG tool."""

import argparse
import sys
from pathlib import Path

from sitemix import __version__
from sitemix.config import discover_default_config_path, load_config
from sitemix.crawler import crawl_all_sites, crawl_site


def _build_crawl_parser() -> argparse.ArgumentParser:
    """Build parser for crawl mode."""
    parser = argparse.ArgumentParser(
        prog="sitemix",
        description="Web scraper for converting website content into RAG files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --site "my blog" --output-format markdown
  %(prog)s --all --output-format markdown
    %(prog)s --site "my blog" --include-pdfs
  %(prog)s --config custom-config.yaml --all --include-pdfs
  %(prog)s merge output/done
        """,
    )

    # Global options
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default=None,
        help=("Path to configuration file (default: auto-discover in ./.web-scraber-rag)"),
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

    # Site selection (mutually exclusive)
    selection_group = parser.add_mutually_exclusive_group(required=True)
    selection_group.add_argument(
        "-s",
        "--site",
        type=str,
        help='Name of specific site entry to crawl (e.g., "my blog")',
    )
    selection_group.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Crawl all sites defined in config",
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
        default=None,
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
        help="Maximum crawl depth cap. If omitted, use per-site depth from config",
    )
    parser.add_argument(
        "--dryrun",
        action="store_true",
        default=False,
        help="Discover URLs and report crawl/ignore decisions without collecting content",
    )
    parser.add_argument(
        "--assisted-browser",
        action="store_true",
        default=False,
        help="Launch a headed persistent browser and allow manual challenge solving before crawl",
    )
    parser.add_argument(
        "--browser-profile",
        type=str,
        default=".web-scraber-rag/browser-profile",
        help="Persistent browser profile directory for assisted runs",
    )
    parser.set_defaults(command="crawl")
    return parser


def _build_merge_parser() -> argparse.ArgumentParser:
    """Build parser for markdown merge mode."""
    parser = argparse.ArgumentParser(
        prog="sitemix merge",
        description="Merge markdown files from a folder into one output file",
    )
    parser.add_argument(
        "command",
        choices=["merge"],
        help="Subcommand name",
    )
    parser.add_argument(
        "input_dir",
        type=str,
        help="Folder containing markdown files to merge",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Merged output file path (default: merge-<folder-name>.md in parent folder)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Reduce output",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose output",
    )
    return parser


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """Parse and return command-line arguments."""
    effective_args = sys.argv[1:] if args is None else args
    if effective_args and effective_args[0] == "merge":
        return _build_merge_parser().parse_args(effective_args)

    return _build_crawl_parser().parse_args(effective_args)


def merge_markdown_folder(
    input_dir: str,
    output: str | None = None,
    *,
    quiet: bool = False,
) -> Path:
    """Merge markdown files from a folder into a single markdown file.

    Args:
        input_dir: Directory containing markdown files to merge
        output: Optional output file path
        quiet: Whether to suppress informational output

    Returns:
        Path to the merged output file

    Raises:
        ValueError: If input directory is invalid or has no markdown files
    """
    input_path = Path(input_dir).expanduser().resolve()
    if not input_path.exists() or not input_path.is_dir():
        raise ValueError(f"Input folder does not exist or is not a directory: {input_dir}")

    output_path = (
        Path(output).expanduser().resolve()
        if output is not None
        else input_path.parent / f"merge-{input_path.name}.md"
    )

    markdown_files = sorted(
        file
        for file in input_path.iterdir()
        if file.is_file() and file.suffix.lower() == ".md" and file.resolve() != output_path
    )

    if not markdown_files:
        raise ValueError(f"No markdown files found in: {input_path}")

    chunks: list[str] = []
    chunks.append(f"# Merged Output: {input_path.name}\n")
    chunks.append(f"Source folder: {input_path}\n")
    chunks.append("## Table of Contents\n")

    for file_path in markdown_files:
        chunks.append(f"- [{file_path.name}](#file-{file_path.stem})")

    chunks.append("")

    for file_path in markdown_files:
        content = file_path.read_text(encoding="utf-8").rstrip()
        chunks.append(f"\n---\n\n## File: {file_path.stem}\n")
        chunks.append(f"Filename: `{file_path.name}`\n")
        chunks.append(content)
        chunks.append("\n")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(chunks).rstrip() + "\n", encoding="utf-8")

    if not quiet:
        print(f"Merged {len(markdown_files)} files into {output_path}")

    return output_path


def main(args: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    try:
        parsed_args = parse_arguments(args)
        if parsed_args.command == "merge":
            merge_markdown_folder(
                input_dir=parsed_args.input_dir,
                output=parsed_args.output,
                quiet=parsed_args.quiet,
            )
            return 0

        verbose = parsed_args.verbose
        quiet = parsed_args.quiet

        config_path = (
            parsed_args.config
            if parsed_args.config is not None
            else str(discover_default_config_path())
        )

        # Load configuration
        config = load_config(config_path, verbose=verbose)

        # Execute appropriate action
        if parsed_args.site:
            crawl_site(
                site_name=parsed_args.site,
                config=config,
                output_dir=parsed_args.output_dir,
                output_format=parsed_args.output_format,
                include_pdfs=parsed_args.include_pdfs,
                follow_links=not parsed_args.no_follow_links,
                depth=parsed_args.depth,
                dry_run=parsed_args.dryrun,
                quiet=quiet,
                verbose=verbose,
                config_file=config_path,
                assisted_browser=parsed_args.assisted_browser,
                browser_profile=parsed_args.browser_profile,
            )
        elif parsed_args.all:
            crawl_all_sites(
                config=config,
                output_dir=parsed_args.output_dir,
                output_format=parsed_args.output_format,
                include_pdfs=parsed_args.include_pdfs,
                follow_links=not parsed_args.no_follow_links,
                depth=parsed_args.depth,
                dry_run=parsed_args.dryrun,
                quiet=quiet,
                verbose=verbose,
                config_file=config_path,
                assisted_browser=parsed_args.assisted_browser,
                browser_profile=parsed_args.browser_profile,
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
