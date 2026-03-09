"""Web crawling functionality."""

import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


class WebCrawler:
    """Crawl a website and extract content as Markdown."""

    def __init__(
        self,
        start_url: str,
        allowed_domains: list[str],
        max_depth: int = 2,
        ignore_urls: list[str] | None = None,
        follow_links: bool = True,
        dry_run: bool = False,
        quiet: bool = False,
        verbose: bool = False,
    ):
        """Initialize the crawler.

        Args:
            start_url: The initial URL to crawl
            allowed_domains: List of domains to crawl within
            max_depth: Maximum depth to follow links
            ignore_urls: URL prefixes or fragments to skip while crawling
            follow_links: Whether to follow links to other pages
            dry_run: Discover crawl decisions without collecting page content
            quiet: Reduce output to minimum
            verbose: Enable verbose logging
        """
        self.start_url = start_url
        self.allowed_domains = allowed_domains
        self.max_depth = max_depth
        self.ignore_urls = ignore_urls or []
        self.follow_links = follow_links
        self.dry_run = dry_run
        self.quiet = quiet
        self.verbose = verbose
        self.visited_urls = set()
        self.reported_urls = set()
        self.content_pages = []  # List of (url, title, content) tuples

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for stable dedup and matching."""
        parsed = urlparse(url)

        # Keep non-http(s) URLs unchanged (filtered elsewhere).
        if parsed.scheme and parsed.scheme not in {"http", "https"}:
            return url

        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path or "/"

        # Treat /foo and /foo/ as the same page for crawl dedup.
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")

        return urlunparse((scheme, netloc, path, "", parsed.query, ""))

    def _is_glob_pattern(self, pattern: str) -> bool:
        """Return True when a pattern uses glob syntax."""
        # We intentionally ignore '?' as a glob marker because '?' is also common
        # in URL query strings (e.g. '?page=2').
        return any(char in pattern for char in "*[]")

    def _matched_ignore_pattern(self, url: str) -> str | None:
        """Check whether a URL matches any ignore pattern.

        Supports both:
        - substring matching (backward compatible)
        - glob matching via fnmatch when pattern contains wildcard chars
        """
        normalized = self._normalize_url(url)
        normalized_url = normalized.lower()
        parsed = urlparse(normalized)
        path_and_query = f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path
        normalized_path_and_query = path_and_query.lower()

        for pattern in self.ignore_urls:
            normalized_pattern = pattern.lower()

            if self._is_glob_pattern(pattern):
                if fnmatch(normalized_url, normalized_pattern) or fnmatch(
                    normalized_path_and_query, normalized_pattern
                ):
                    return pattern
                continue

            if normalized_pattern in normalized_url:
                return pattern

        return None

    def _url_decision(self, url: str, depth: int) -> tuple[bool, str]:
        """Decide whether a URL should be crawled and explain why."""
        normalized_url = self._normalize_url(url)

        if depth > self.max_depth:
            return (False, "depth limit exceeded")

        if normalized_url in self.visited_urls:
            return (False, "already visited")

        if normalized_url.startswith(("#", "data:")):
            return (False, "unsupported scheme")

        matched_ignore = self._matched_ignore_pattern(normalized_url)
        if matched_ignore:
            return (False, f"ignored by pattern: {matched_ignore}")

        parsed = urlparse(normalized_url)
        domain = parsed.netloc.lower()
        for allowed in self.allowed_domains:
            if domain.endswith(allowed) or domain == allowed:
                return (True, "allowed")

        return (False, "outside allowed domains")

    def _is_valid_url(self, url: str, depth: int) -> bool:
        """Check if URL should be crawled.

        Args:
            url: URL to check
            depth: Current crawl depth

        Returns:
            True if URL should be crawled
        """
        should_crawl, _reason = self._url_decision(url, depth)
        return should_crawl

    def _extract_links(self, soup: BeautifulSoup, current_url: str) -> list[str]:
        """Extract all links from a page.

        Args:
            soup: BeautifulSoup object
            current_url: Current page URL (for relative URL resolution)

        Returns:
            List of absolute URLs
        """
        links = []
        for link in soup.find_all("a", href=True):
            href = link.get("href")
            if not href:
                continue

            # Convert relative URLs to absolute
            absolute_url = urljoin(current_url, href)

            # Remove fragments
            absolute_url = absolute_url.split("#")[0]
            absolute_url = self._normalize_url(absolute_url)

            if absolute_url not in links:
                links.append(absolute_url)

        return links

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from a page.

        Args:
            soup: BeautifulSoup object

        Returns:
            Extracted text content
        """
        # Remove noise elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()

        # Try to find main content area (try semantic tags first)
        content_elem = soup.find(["main", "article"])

        # Fall back to body if no semantic tags found
        if not content_elem:
            content_elem = soup.find("body")

        # Get text from the found element
        content = content_elem.get_text() if content_elem else soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in content.splitlines())
        return "\n".join(line for line in lines if line)

    def _fetch_page(self, url: str) -> tuple[str, str] | None:
        """Fetch a page and extract content.

        Args:
            url: URL to fetch

        Returns:
            Tuple of (title, content) or None if failed
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(url, wait_until="networkidle")

                # Get title
                title = page.title()

                # Get HTML
                html = page.content()
                browser.close()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # Extract content
            content = self._extract_content(soup)

            return (title, content)
        except Exception as e:
            if self.verbose:
                print(f"Error fetching {url}: {e}", file=sys.stderr)
            return None

    def _fetch_and_extract_links(self, url: str) -> list[str]:
        """Fetch a page and extract links from it.

        Args:
            url: URL to fetch

        Returns:
            List of links found on the page
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(url, wait_until="networkidle")
                soup = BeautifulSoup(page.content(), "html.parser")
                browser.close()
                return self._extract_links(soup, url)
        except Exception as e:
            if self.verbose:
                print(f"Error fetching links from {url}: {e}", file=sys.stderr)
            return []

    def _process_page(
        self, url: str, depth: int, to_visit: list[tuple[str, int]]
    ) -> tuple[str, str] | None:
        """Process a single page: fetch, extract content, and queue new links.

        Args:
            url: URL to process
            depth: Current crawl depth
            to_visit: Queue of URLs to visit

        Returns:
            Tuple of (title, content) if successful, None otherwise
        """
        result = self._fetch_page(url)
        if not result:
            return None

        title, content = result

        if not content.strip():
            return None

        # Extract and queue links for next iteration (if following links)
        if self.follow_links and depth < self.max_depth:
            self._enqueue_links(url, depth, to_visit, dry_run=False)

        return (title, content)

    def _enqueue_links(
        self,
        source_url: str,
        depth: int,
        to_visit: list[tuple[str, int]],
        dry_run: bool,
    ) -> None:
        """Inspect links from a page and enqueue crawlable URLs."""
        links = self._fetch_and_extract_links(source_url)
        next_depth = depth + 1
        for link in links:
            should_crawl, reason = self._url_decision(link, next_depth)
            if dry_run or self._should_log_concise():
                self._log_dryrun_decision(link, should_crawl, reason)
            elif (not should_crawl) and self.verbose and "ignored by pattern:" in reason:
                print(f"Ignoring ({next_depth}): {link} ({reason})", file=sys.stderr)

            if should_crawl:
                to_visit.append((link, next_depth))

    def _can_follow_links(self, depth: int) -> bool:
        """Return True if links should be discovered at this depth."""
        return self.follow_links and depth < self.max_depth

    def _should_log_concise(self) -> bool:
        """Return True when concise output should be printed."""
        return (not self.verbose) and (not self.quiet)

    def _log_dryrun_decision(self, url: str, should_crawl: bool, reason: str) -> None:
        """Print a concise dry-run decision once per URL.

        Default output intentionally focuses on actionable information:
        - URLs selected for crawling
        - URLs ignored by ignore patterns

        Extra reasons such as "already visited" are only shown with `--verbose`.
        """
        if url in self.reported_urls:
            return

        if self.quiet:
            return

        is_pattern_ignore = "ignored by pattern:" in reason
        if (not should_crawl) and (not is_pattern_ignore) and (not self.verbose):
            return

        icon = "✅" if should_crawl else "❌"
        label = "[crawl]" if should_crawl else "[ignore]"
        message = f"{icon} {label:<8} {url}"

        if not should_crawl and (is_pattern_ignore or self.verbose):
            message = f"{message} ({reason})"

        print(message, file=sys.stderr)
        self.reported_urls.add(url)

    def _handle_skipped_url(self, url: str, depth: int, reason: str) -> None:
        """Handle logging for a skipped URL."""
        if self.verbose and "ignored by pattern:" in reason:
            print(f"Ignoring ({depth}): {url} ({reason})", file=sys.stderr)

    def _handle_crawlable_url(
        self,
        url: str,
        depth: int,
        to_visit: list[tuple[str, int]],
        markdown_content: list[str],
    ) -> None:
        """Handle processing for a crawlable URL."""
        self.visited_urls.add(url)

        if self._should_log_concise():
            self._log_dryrun_decision(url, should_crawl=True, reason="allowed")

        if self.verbose:
            print(f"Crawling ({depth}): {url}", file=sys.stderr)

        if self.dry_run:
            if self._can_follow_links(depth):
                self._enqueue_links(url, depth, to_visit, dry_run=True)
            return

        result = self._process_page(url, depth, to_visit)
        if result:
            title, content = result
            markdown_content.append(f"# {title}\n\nSource: {url}\n\n{content}\n")

    def crawl(self) -> str:
        """Crawl the website and return consolidated markdown.

        Returns:
            Markdown string with all crawled content
        """
        to_visit = [(self.start_url, 0)]  # (url, depth)
        markdown_content = []

        if self.verbose:
            print(f"Starting crawl from: {self.start_url}", file=sys.stderr)

        while to_visit:
            url, depth = to_visit.pop(0)
            url = self._normalize_url(url)

            should_crawl, reason = self._url_decision(url, depth)
            if not should_crawl:
                self._handle_skipped_url(url, depth, reason)
                continue

            self._handle_crawlable_url(url, depth, to_visit, markdown_content)

        # Consolidate all content
        final_markdown = "\n\n---\n\n".join(markdown_content)

        if self.verbose:
            print(f"Crawled {len(self.visited_urls)} pages", file=sys.stderr)

        return final_markdown


def crawl_party(
    party_name: str,
    config: dict[str, Any],
    output_dir: str,
    output_format: str,
    include_pdfs: bool,
    follow_links: bool,
    depth: int | None,
    dry_run: bool = False,
    quiet: bool = False,
    verbose: bool = False,
    config_file: str | None = None,
) -> None:
    """Crawl a single party website.

    Args:
        party_name: Name of the party to crawl
        config: Configuration dictionary
        output_dir: Output directory for generated files
        output_format: Output format (markdown, html, text)
        include_pdfs: Whether to include PDF crawling
        follow_links: Whether to follow links within domain
        depth: Maximum crawl depth cap; if None, use per-party config depth
        dry_run: Discover crawl/ignore decisions without collecting data
        quiet: Reduce output to minimum
        verbose: Enable verbose logging
        config_file: Resolved config file path used for this run
    """
    from web_scraper_rag.config import get_site_by_name

    party = get_site_by_name(config, party_name)

    # Party-specific depth is default. CLI depth, when provided, acts as global cap.
    effective_depth = party["depth"] if depth is None else min(depth, party["depth"])

    if verbose:
        print(f"Crawling party: {party['name']}", file=sys.stderr)
        print(f"  Website: {party['website']}", file=sys.stderr)
        print(f"  Format: {output_format}", file=sys.stderr)
        if dry_run:
            print("  Dry run mode enabled", file=sys.stderr)
        if include_pdfs:
            print("  Including PDFs", file=sys.stderr)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / f"{party['name'].lower().replace(' ', '_')}.md"

    if not quiet:
        if config_file:
            print(f"Active config file: {config_file}")
        print(f"Active depth setting: {effective_depth}")
        print(f"Output file: {output_file}")

    # Create crawler
    crawler = WebCrawler(
        start_url=party["website"],
        allowed_domains=party.get("domains", []),
        max_depth=effective_depth,
        ignore_urls=party.get("ignore_urls", []),
        follow_links=follow_links,
        dry_run=dry_run,
        quiet=quiet,
        verbose=verbose,
    )

    # Crawl the site
    content = crawler.crawl()

    if dry_run:
        if not quiet:
            print("Dry run complete. Output file was not written.")
        elif verbose:
            print("Dry run complete. No output file written.", file=sys.stderr)
        return

    # Save to file
    output_file.write_text(content, encoding="utf-8")

    if verbose:
        print(f"Saved to: {output_file}", file=sys.stderr)


def crawl_all_parties(
    config: dict[str, Any],
    output_dir: str,
    output_format: str,
    include_pdfs: bool,
    follow_links: bool,
    depth: int | None,
    dry_run: bool = False,
    quiet: bool = False,
    verbose: bool = False,
    config_file: str | None = None,
) -> None:
    """Crawl all parties defined in configuration.

    Args:
        config: Configuration dictionary
        output_dir: Output directory for generated files
        output_format: Output format (markdown, html, text)
        include_pdfs: Whether to include PDF crawling
        follow_links: Whether to follow links within domain
        depth: Maximum crawl depth cap; if None, use per-party config depth
        dry_run: Discover crawl/ignore decisions without collecting data
        quiet: Reduce output to minimum
        verbose: Enable verbose logging
        config_file: Resolved config file path used for this run
    """
    from web_scraper_rag.config import get_all_sites

    parties = get_all_sites(config)

    if verbose:
        print(f"Crawling {len(parties)} parties...", file=sys.stderr)

    for party in parties:
        crawl_party(
            party_name=party["name"],
            config=config,
            output_dir=output_dir,
            output_format=output_format,
            include_pdfs=include_pdfs,
            follow_links=follow_links,
            depth=depth,
            dry_run=dry_run,
            quiet=quiet,
            verbose=verbose,
            config_file=config_file,
        )

    if verbose:
        print(f"Crawling complete. Output directory: {output_dir}", file=sys.stderr)
