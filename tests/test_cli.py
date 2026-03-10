"""Tests for CLI module."""

import pytest

from web_scraper_rag.cli import parse_arguments


class TestParseArguments:
    """Test CLI argument parsing."""

    def test_single_party_crawl(self):
        """Test parsing single party crawl command."""
        args = parse_arguments(["--party", "alternativet", "--output-format", "markdown"])
        assert args.party == "alternativet"
        assert args.all is False
        assert args.output_format == "markdown"

    def test_all_parties_crawl(self):
        """Test parsing all parties crawl command."""
        args = parse_arguments(["--all", "--output-format", "markdown"])
        assert args.all is True
        assert args.party is None
        assert args.output_format == "markdown"

    def test_with_pdfs(self):
        """Test parsing command with PDF inclusion."""
        args = parse_arguments(["--party", "alternativet", "--include-pdfs"])
        assert args.party == "alternativet"
        assert args.include_pdfs is True

    def test_custom_output_dir(self):
        """Test parsing custom output directory."""
        args = parse_arguments(["--party", "alternativet", "--output-dir", "/custom/path"])
        assert args.output_dir == "/custom/path"

    def test_custom_config(self):
        """Test parsing custom config file path."""
        args = parse_arguments(["--party", "alternativet", "--config", "custom.yaml"])
        assert args.config == "custom.yaml"

    def test_quiet_flag(self):
        """Test quiet flag parsing."""
        args = parse_arguments(["--party", "alternativet", "--quiet"])
        assert args.quiet is True

    def test_verbose_flag(self):
        """Test verbose flag parsing."""
        args = parse_arguments(["--party", "alternativet", "--verbose"])
        assert args.verbose is True

    def test_dryrun_flag(self):
        """Test dryrun flag parsing."""
        args = parse_arguments(["--party", "alternativet", "--dryrun"])
        assert args.dryrun is True

    def test_no_follow_links(self):
        """Test no-follow-links flag."""
        args = parse_arguments(["--party", "alternativet", "--no-follow-links"])
        assert args.no_follow_links is True

    def test_custom_depth(self):
        """Test custom crawl depth."""
        args = parse_arguments(["--party", "alternativet", "--depth", "5"])
        assert args.depth == 5

    def test_assisted_browser_flag(self):
        """Test assisted browser mode flag."""
        args = parse_arguments(["--party", "alternativet", "--assisted-browser"])
        assert args.assisted_browser is True

    def test_browser_profile_option(self):
        """Test custom browser profile path."""
        args = parse_arguments(
            [
                "--party",
                "alternativet",
                "--browser-profile",
                ".web-scraber-rag/custom-profile",
            ]
        )
        assert args.browser_profile == ".web-scraber-rag/custom-profile"

    def test_mutually_exclusive_party_all(self):
        """Test that --party and --all are mutually exclusive."""
        with pytest.raises(SystemExit):
            parse_arguments(["--party", "alternativet", "--all"])

    def test_mutually_exclusive_verbose_quiet(self):
        """Test that --verbose and --quiet are mutually exclusive."""
        with pytest.raises(SystemExit):
            parse_arguments(["--party", "alternativet", "--verbose", "--quiet"])

    def test_required_selection(self):
        """Test that either --party or --all is required."""
        with pytest.raises(SystemExit):
            parse_arguments(["--output-format", "markdown"])

    def test_default_values(self):
        """Test default argument values."""
        args = parse_arguments(["--all"])
        assert args.config is None
        assert args.output_dir == "output"
        assert args.output_format == "markdown"
        assert args.include_pdfs is False
        assert args.verbose is False
        assert args.quiet is False
        assert args.dryrun is False
        assert args.depth is None
        assert args.assisted_browser is False
        assert args.browser_profile == ".web-scraber-rag/browser-profile"

    def test_short_options(self):
        """Test short option aliases."""
        args = parse_arguments(["-p", "alternativet", "-f", "markdown", "-o", "/out"])
        assert args.party == "alternativet"
        assert args.output_format == "markdown"
        assert args.output_dir == "/out"
        assert args.config is None
