"""Web crawling functionality."""

import sys
from fnmatch import fnmatch
from io import BytesIO
from os import environ
from pathlib import Path
from platform import system
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from pypdf import PdfReader


class WebCrawler:
    """Crawl a website and extract content as Markdown."""

    KNOWN_BINARY_EXTENSIONS = frozenset(
        {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".gif",
            ".mov",
            ".mp4",
            ".avi",
            ".mkv",
            ".webm",
            ".mp3",
            ".wav",
            ".zip",
            ".tar",
            ".gz",
            ".rar",
            ".7z",
            ".exe",
            ".dmg",
            ".iso",
        }
    )

    def __init__(
        self,
        start_url: str,
        allowed_domains: list[str],
        max_depth: int = 2,
        ignore_urls: list[str] | None = None,
        follow_links: bool = True,
        include_pdfs: bool = False,
        dry_run: bool = False,
        quiet: bool = False,
        verbose: bool = False,
        assisted_browser: bool = False,
        browser_profile: str = ".web-scraber-rag/browser-profile",
    ):
        """Initialize the crawler.

        Args:
            start_url: The initial URL to crawl
            allowed_domains: List of domains to crawl within
            max_depth: Maximum depth to follow links
            ignore_urls: URL prefixes or fragments to skip while crawling
            follow_links: Whether to follow links to other pages
            include_pdfs: Whether PDF links should be fetched and parsed
            dry_run: Discover crawl decisions without collecting page content
            quiet: Reduce output to minimum
            verbose: Enable verbose logging
            assisted_browser: Launch headed browser with manual checkpoint before crawling
            browser_profile: Persistent browser profile directory
        """
        self.start_url = start_url
        self.allowed_domains = allowed_domains
        self.max_depth = max_depth
        self.ignore_urls = ignore_urls or []
        self.follow_links = follow_links
        self.include_pdfs = include_pdfs
        self.dry_run = dry_run
        self.quiet = quiet
        self.verbose = verbose
        self.assisted_browser = assisted_browser
        self.browser_profile = browser_profile
        self.visited_urls = set()
        self.reported_urls = set()
        self.reported_challenges = set()
        self.content_pages = []  # List of (url, title, content) tuples
        self._assisted_playwright: Any | None = None
        self._assisted_context: Any | None = None
        self._assisted_page: Any | None = None

    def _create_page(self, playwright: Any) -> tuple[Any, Any]:
        """Create a non-assisted page and return (owner, page)."""
        browser = playwright.chromium.launch()
        page = browser.new_page()
        return browser, page

    def _prepare_assisted_session(self) -> None:
        """Open a headed browser once so user can solve anti-bot challenges."""
        if not self.assisted_browser:
            return

        if not self._has_graphical_display():
            raise RuntimeError(
                "Assisted browser requires a graphical display (DISPLAY/WAYLAND_DISPLAY not set). "
                "In a devcontainer this usually means no X server is available. "
                "Use normal mode, run assisted mode on a host with GUI, or configure GUI forwarding/noVNC."
            )

        if not self.quiet:
            print(
                "Assisted browser mode: a browser window will open. Solve any challenge, then press Enter.",
                file=sys.stderr,
            )

        Path(self.browser_profile).mkdir(parents=True, exist_ok=True)
        self._assisted_playwright = sync_playwright().start()
        self._assisted_context = self._launch_assisted_context()
        # Reduce trivial webdriver-based bot detection signals.
        self._assisted_context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        self._assisted_page = self._assisted_context.new_page()
        try:
            self._goto_with_fallback(self._assisted_page, self.start_url)
        except Exception as e:  # pragma: no cover - best effort UX step
            if self.verbose:
                print(f"Assisted browser warmup failed: {e}", file=sys.stderr)

        if sys.stdin.isatty():
            input("Press Enter to continue crawling... ")
        elif self.verbose:
            print("No interactive terminal detected; continuing without pause.", file=sys.stderr)

    def _teardown_assisted_session(self) -> None:
        """Close persistent assisted browser session resources."""
        if self._assisted_context is not None:
            self._assisted_context.close()
            self._assisted_context = None
            self._assisted_page = None

        if self._assisted_playwright is not None:
            self._assisted_playwright.stop()
            self._assisted_playwright = None

    def _launch_assisted_context(self) -> Any:
        """Launch assisted persistent context with conservative anti-detection settings.

        Prefer system Chrome channel when available, then fall back to bundled
        Chromium so assisted mode remains portable.
        """
        launch_kwargs = {
            "user_data_dir": self.browser_profile,
            "headless": False,
            "ignore_default_args": ["--enable-automation"],
            "args": ["--disable-blink-features=AutomationControlled"],
        }

        try:
            return self._assisted_playwright.chromium.launch_persistent_context(
                channel="chrome", **launch_kwargs
            )
        except Exception:
            return self._assisted_playwright.chromium.launch_persistent_context(**launch_kwargs)

    def _has_graphical_display(self) -> bool:
        """Return True when a graphical display is available for headed browser runs."""
        # macOS and Windows provide native windowing without DISPLAY/WAYLAND vars.
        if system() in {"Darwin", "Windows"}:
            return True

        return bool(environ.get("DISPLAY") or environ.get("WAYLAND_DISPLAY"))

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

    def _normalize_allowed_domain(self, allowed: str) -> str:
        """Normalize a configured allowed domain entry for host matching."""
        normalized = allowed.strip().lower()

        # Accept accidental full URLs in config by extracting the host.
        if "://" in normalized:
            parsed_allowed = urlparse(normalized)
            normalized = parsed_allowed.hostname or ""

        return normalized.rstrip(".")

    def _is_allowed_domain(self, host: str) -> bool:
        """Return True when host matches one of the configured allowed domains.

        Literal domains are treated as exact host matches. Glob patterns are
        supported explicitly via wildcard syntax in the configured domain.
        """
        normalized_host = host.lower().rstrip(".")

        for allowed in self.allowed_domains:
            normalized_allowed = self._normalize_allowed_domain(allowed)
            if not normalized_allowed:
                continue

            if self._is_glob_pattern(normalized_allowed):
                if fnmatch(normalized_host, normalized_allowed):
                    return True
                continue

            if normalized_host == normalized_allowed:
                return True

            # Backward-compatible convenience for configs that list the apex
            # domain while sites resolve to www.<domain>.
            if normalized_host == f"www.{normalized_allowed}":
                return True

        return False

    def _url_decision(self, url: str, depth: int) -> tuple[bool, str]:
        """Decide whether a URL should be crawled and explain why."""
        normalized_url = self._normalize_url(url)
        parsed = urlparse(normalized_url)

        if depth > self.max_depth:
            return (False, "depth limit exceeded")

        if normalized_url in self.visited_urls:
            return (False, "already visited")

        if normalized_url.startswith(("#", "data:")):
            return (False, "unsupported scheme")

        if parsed.scheme and parsed.scheme not in {"http", "https"}:
            return (False, "unsupported scheme")

        matched_ignore = self._matched_ignore_pattern(normalized_url)
        if matched_ignore:
            return (False, f"ignored by pattern: {matched_ignore}")

        if self._is_known_binary_url(normalized_url):
            return (False, "unsupported binary type")

        host = parsed.hostname or ""
        if self._is_allowed_domain(host):
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

    def _is_pdf_url(self, url: str) -> bool:
        """Return True when URL path points to a PDF document."""
        path = urlparse(url).path.lower()
        return path.endswith(".pdf")

    def _is_known_binary_url(self, url: str) -> bool:
        """Return True when URL path points to known non-HTML binary assets."""
        path = urlparse(url).path.lower()
        suffix = Path(path).suffix
        return suffix in self.KNOWN_BINARY_EXTENSIONS

    def _fetch_pdf_text(self, url: str) -> tuple[str, str] | None:
        """Download and extract text from PDF.

        Returns:
            Tuple of (title, extracted_text) or None on failure.
        """
        try:
            request = Request(  # noqa: S310 - URL scheme is constrained by crawler domain filtering.
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; sitemix/0.1.0)",
                },
            )
            with urlopen(request) as response:  # noqa: S310 - URL is user-config driven crawl target.
                pdf_bytes = response.read()

            reader = PdfReader(BytesIO(pdf_bytes))
            extracted_pages = [page.extract_text() or "" for page in reader.pages]
            content = "\n".join(page.strip() for page in extracted_pages if page.strip())

            title = f"[PDF] {Path(urlparse(url).path).name or url}"
            if not content:
                content = "[No extractable PDF text found]"

            return title, content
        except Exception as e:
            if self.verbose:
                print(f"Error fetching PDF {url}: {e}", file=sys.stderr)
            return None

    def _fetch_page(self, url: str) -> tuple[str, str] | None:
        """Fetch a page and extract content.

        Args:
            url: URL to fetch

        Returns:
            Tuple of (title, content) or None if failed
        """
        try:
            if self._assisted_page is not None:
                page = self._assisted_page
                self._goto_with_fallback(page, url)

                title = page.title()
                html = page.content()
            else:
                with sync_playwright() as p:
                    owner, page = self._create_page(p)
                    self._goto_with_fallback(page, url)

                    # Get title
                    title = page.title()

                    # Get HTML
                    html = page.content()
                    owner.close()

            challenge_provider = self._detect_bot_challenge(html=html, title=title)
            if challenge_provider:
                self._report_bot_challenge(url=url, provider=challenge_provider)
                return None

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # Extract content
            content = self._extract_content(soup)

            return (title, content)
        except Exception as e:
            if self.verbose:
                print(f"Error fetching {url}: {e}", file=sys.stderr)
            return None

    def _detect_bot_challenge(self, html: str, title: str = "") -> str | None:
        """Detect common anti-bot interstitial pages.

        Returns provider name when detected, otherwise None.
        """
        lowered_html = html.lower()
        lowered_title = title.lower()

        if (
            "cf-mitigated" in lowered_html
            or "__cf_chl_" in lowered_html
            or "cdn-cgi/challenge-platform" in lowered_html
            or "just a moment" in lowered_title
            or "enable javascript and cookies to continue" in lowered_html
        ):
            return "Cloudflare"

        return None

    def _report_bot_challenge(self, url: str, provider: str) -> None:
        """Log anti-bot challenge detection once per URL."""
        if url in self.reported_challenges:
            return

        if not self.quiet:
            print(
                f"Challenge detected ({provider}) at {url}; crawl results may be incomplete.",
                file=sys.stderr,
            )

        self.reported_challenges.add(url)

    def _goto_with_fallback(self, page: Any, url: str) -> None:
        """Navigate with fallback strategies for sites that never become network-idle.

        Some sites keep long-running network connections open (analytics, beacons,
        live widgets), so `networkidle` may timeout even though content is ready.
        """
        try:
            page.goto(url, wait_until="networkidle")
            return
        except PlaywrightTimeoutError:
            if self.verbose:
                print(
                    f"Timeout waiting for networkidle on {url}; retrying with domcontentloaded",
                    file=sys.stderr,
                )

        try:
            page.goto(url, wait_until="domcontentloaded")
            return
        except PlaywrightTimeoutError:
            if self.verbose:
                print(
                    f"Timeout waiting for domcontentloaded on {url}; retrying with load",
                    file=sys.stderr,
                )

        page.goto(url, wait_until="load")

    def _fetch_and_extract_links(self, url: str) -> list[str]:
        """Fetch a page and extract links from it.

        Args:
            url: URL to fetch

        Returns:
            List of links found on the page
        """
        try:
            if self._assisted_page is not None:
                page = self._assisted_page
                self._goto_with_fallback(page, url)
                html = page.content()
                title = page.title()
            else:
                with sync_playwright() as p:
                    owner, page = self._create_page(p)
                    self._goto_with_fallback(page, url)
                    html = page.content()
                    title = page.title()
                    owner.close()

            challenge_provider = self._detect_bot_challenge(html=html, title=title)
            if challenge_provider:
                self._report_bot_challenge(url=url, provider=challenge_provider)
                return []

            soup = BeautifulSoup(html, "html.parser")
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
        if self._is_pdf_url(url):
            if not self.include_pdfs:
                return None

            return self._fetch_pdf_text(url)

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

        if reason == "unsupported scheme":
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

        self._prepare_assisted_session()

        try:
            while to_visit:
                url, depth = to_visit.pop(0)
                url = self._normalize_url(url)

                should_crawl, reason = self._url_decision(url, depth)
                if not should_crawl:
                    self._handle_skipped_url(url, depth, reason)
                    continue

                self._handle_crawlable_url(url, depth, to_visit, markdown_content)
        finally:
            self._teardown_assisted_session()

        # Consolidate all content
        final_markdown = "\n\n---\n\n".join(markdown_content)

        if self.verbose:
            print(f"Crawled {len(self.visited_urls)} pages", file=sys.stderr)

        return final_markdown


def crawl_site(
    site_name: str,
    config: dict[str, Any],
    output_dir: str,
    output_format: str,
    include_pdfs: bool | None,
    follow_links: bool,
    depth: int | None,
    dry_run: bool = False,
    quiet: bool = False,
    verbose: bool = False,
    config_file: str | None = None,
    assisted_browser: bool = False,
    browser_profile: str = ".web-scraber-rag/browser-profile",
) -> None:
    """Crawl a single site.

    Args:
        site_name: Name of the site to crawl
        config: Configuration dictionary
        output_dir: Output directory for generated files
        output_format: Output format (markdown, html, text)
        include_pdfs: Whether to include PDF crawling
        follow_links: Whether to follow links within domain
        depth: Maximum crawl depth cap; if None, use per-site config depth
        dry_run: Discover crawl/ignore decisions without collecting data
        quiet: Reduce output to minimum
        verbose: Enable verbose logging
        config_file: Resolved config file path used for this run
        assisted_browser: Use interactive headed browser before crawl
        browser_profile: Persistent browser profile directory
    """
    from sitemix.config import get_site_by_name

    site = get_site_by_name(config, site_name)
    effective_depth, merged_ignore_urls, effective_include_pdfs = _resolve_site_depth_and_ignores(
        config, site, depth, include_pdfs
    )

    _log_crawl_start(
        site=site,
        output_format=output_format,
        dry_run=dry_run,
        include_pdfs=include_pdfs,
        effective_include_pdfs=effective_include_pdfs,
        verbose=verbose,
    )

    output_file = _prepare_output_file(output_dir, site["name"])
    _print_run_header(
        quiet=quiet,
        config_file=config_file,
        effective_depth=effective_depth,
        effective_include_pdfs=effective_include_pdfs,
        output_file=output_file,
    )

    # Create crawler
    crawler = WebCrawler(
        start_url=site["website"],
        allowed_domains=site.get("domains", []),
        max_depth=effective_depth,
        ignore_urls=merged_ignore_urls,
        follow_links=follow_links,
        include_pdfs=effective_include_pdfs,
        dry_run=dry_run,
        quiet=quiet,
        verbose=verbose,
        assisted_browser=assisted_browser,
        browser_profile=browser_profile,
    )

    # Crawl the site
    content = crawler.crawl()

    if dry_run:
        _handle_dry_run_completion(quiet=quiet, verbose=verbose)
        return

    # Save to file
    output_file.write_text(content, encoding="utf-8")

    if verbose:
        print(f"Saved to: {output_file}", file=sys.stderr)


def _resolve_site_depth_and_ignores(
    config: dict[str, Any],
    site: dict[str, Any],
    cli_depth: int | None,
    cli_include_pdfs: bool | None,
) -> tuple[int, list[str], bool]:
    """Resolve effective depth and merged ignore patterns for a site crawl."""
    from sitemix.config import get_global_crawl_defaults

    global_depth, global_ignore_urls, global_include_pdfs = get_global_crawl_defaults(config)

    site_depth = site.get("depth")
    default_depth = (
        site_depth if site_depth is not None else (global_depth if global_depth is not None else 2)
    )

    merged_ignore_urls = list(global_ignore_urls)
    for pattern in site.get("ignore_urls", []):
        if pattern not in merged_ignore_urls:
            merged_ignore_urls.append(pattern)

    # Site depth overrides global depth; CLI depth acts as a cap.
    effective_depth = default_depth if cli_depth is None else min(cli_depth, default_depth)

    if cli_include_pdfs is not None:
        effective_include_pdfs = cli_include_pdfs
    elif "include_pdfs" in site:
        effective_include_pdfs = site["include_pdfs"]
    elif global_include_pdfs is not None:
        effective_include_pdfs = global_include_pdfs
    else:
        effective_include_pdfs = False

    return effective_depth, merged_ignore_urls, effective_include_pdfs


def _log_crawl_start(
    site: dict[str, Any],
    output_format: str,
    dry_run: bool,
    include_pdfs: bool | None,
    effective_include_pdfs: bool,
    verbose: bool,
) -> None:
    """Emit verbose crawl start details."""
    if not verbose:
        return

    print(f"Crawling site: {site['name']}", file=sys.stderr)
    print(f"  Website: {site['website']}", file=sys.stderr)
    print(f"  Format: {output_format}", file=sys.stderr)
    if dry_run:
        print("  Dry run mode enabled", file=sys.stderr)
    if include_pdfs is None:
        print(f"  Include PDFs: {effective_include_pdfs} (from config/default)", file=sys.stderr)
    elif include_pdfs:
        print("  Including PDFs", file=sys.stderr)


def _prepare_output_file(output_dir: str, site_name: str) -> Path:
    """Create output directory and return target markdown file path."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path / f"{site_name.lower().replace(' ', '_')}.md"


def _print_run_header(
    quiet: bool,
    config_file: str | None,
    effective_depth: int,
    effective_include_pdfs: bool,
    output_file: Path,
) -> None:
    """Print standard non-verbose run header to stdout."""
    if quiet:
        return

    if config_file:
        print(f"Active config file: {config_file}")
    print(f"Active depth setting: {effective_depth}")
    print(f"Include PDFs: {effective_include_pdfs}")
    print(f"Output file: {output_file}")


def _handle_dry_run_completion(quiet: bool, verbose: bool) -> None:
    """Print dry-run completion message according to verbosity settings."""
    if not quiet:
        print("Dry run complete. Output file was not written.")
    elif verbose:
        print("Dry run complete. No output file written.", file=sys.stderr)


def crawl_all_sites(
    config: dict[str, Any],
    output_dir: str,
    output_format: str,
    include_pdfs: bool | None,
    follow_links: bool,
    depth: int | None,
    dry_run: bool = False,
    quiet: bool = False,
    verbose: bool = False,
    config_file: str | None = None,
    assisted_browser: bool = False,
    browser_profile: str = ".web-scraber-rag/browser-profile",
) -> None:
    """Crawl all sites defined in configuration.

    Args:
        config: Configuration dictionary
        output_dir: Output directory for generated files
        output_format: Output format (markdown, html, text)
        include_pdfs: Whether to include PDF crawling
        follow_links: Whether to follow links within domain
        depth: Maximum crawl depth cap; if None, use per-site config depth
        dry_run: Discover crawl/ignore decisions without collecting data
        quiet: Reduce output to minimum
        verbose: Enable verbose logging
        config_file: Resolved config file path used for this run
        assisted_browser: Use interactive headed browser before crawl
        browser_profile: Persistent browser profile directory
    """
    from sitemix.config import get_all_sites

    sites = get_all_sites(config)

    if verbose:
        print(f"Crawling {len(sites)} sites...", file=sys.stderr)

    for site in sites:
        crawl_site(
            site_name=site["name"],
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
            assisted_browser=assisted_browser,
            browser_profile=browser_profile,
        )

    if verbose:
        print(f"Crawling complete. Output directory: {output_dir}", file=sys.stderr)
