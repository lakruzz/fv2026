"""Web crawling functionality."""

import sys
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


class WebCrawler:
    """Crawl a website and extract content as Markdown."""

    def __init__(
        self,
        start_url: str,
        allowed_domains: list[str],
        max_depth: int = 2,
        follow_links: bool = True,
        verbose: bool = False,
    ):
        """Initialize the crawler.

        Args:
            start_url: The initial URL to crawl
            allowed_domains: List of domains to crawl within
            max_depth: Maximum depth to follow links
            follow_links: Whether to follow links to other pages
            verbose: Enable verbose logging
        """
        self.start_url = start_url
        self.allowed_domains = allowed_domains
        self.max_depth = max_depth
        self.follow_links = follow_links
        self.verbose = verbose
        self.visited_urls = set()
        self.content_pages = []  # List of (url, title, content) tuples

    def _is_valid_url(self, url: str, depth: int) -> bool:
        """Check if URL should be crawled.

        Args:
            url: URL to check
            depth: Current crawl depth

        Returns:
            True if URL should be crawled
        """
        # Don't crawl beyond max depth
        if depth > self.max_depth:
            return False

        # Skip already visited
        if url in self.visited_urls:
            return False

        # Skip anchors and data URLs
        if url.startswith(("#", "data:")):
            return False

        # Check if domain is allowed
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        for allowed in self.allowed_domains:
            if domain.endswith(allowed) or domain == allowed:
                return True

        return False

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
            links = self._fetch_and_extract_links(url)
            for link in links:
                if self._is_valid_url(link, depth + 1):
                    to_visit.append((link, depth + 1))

        return (title, content)

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

            if not self._is_valid_url(url, depth):
                continue

            self.visited_urls.add(url)

            if self.verbose:
                print(f"Crawling ({depth}): {url}", file=sys.stderr)

            # Process page
            result = self._process_page(url, depth, to_visit)
            if result:
                title, content = result
                markdown_content.append(f"# {title}\n\nSource: {url}\n\n{content}\n")

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
    depth: int,
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

    # Create crawler
    crawler = WebCrawler(
        start_url=party["website"],
        allowed_domains=party.get("domains", []),
        max_depth=depth,
        follow_links=follow_links,
        verbose=verbose,
    )

    # Crawl the site
    content = crawler.crawl()

    # Save to file
    output_file = output_path / f"{party['name'].lower().replace(' ', '_')}.md"
    output_file.write_text(content, encoding="utf-8")

    if verbose:
        print(f"Saved to: {output_file}", file=sys.stderr)


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
            follow_links=follow_links,
            depth=depth,
            verbose=verbose,
        )

    if verbose:
        print(f"Crawling complete. Output directory: {output_dir}", file=sys.stderr)
