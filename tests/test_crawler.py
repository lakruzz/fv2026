"""Tests for the web crawler implementation."""

from unittest.mock import MagicMock, patch


class TestWebCrawler:
    """Test the WebCrawler class."""

    def test_crawler_initialization(self):
        """Test crawler can be initialized with required parameters."""
        from web_scraper_rag.crawler import WebCrawler

        crawler = WebCrawler(
            start_url="https://example.com",
            allowed_domains=["example.com"],
            max_depth=2,
            verbose=False,
        )

        assert crawler.start_url == "https://example.com"
        assert crawler.allowed_domains == ["example.com"]
        assert crawler.max_depth == 2
        assert crawler.verbose is False
        assert crawler.visited_urls == set()

    def test_is_valid_url_respects_max_depth(self):
        """Test that URLs beyond max depth are rejected."""
        from web_scraper_rag.crawler import WebCrawler

        crawler = WebCrawler(
            start_url="https://example.com",
            allowed_domains=["example.com"],
            max_depth=1,  # Set max_depth to 1 for this test
        )

        # Depth 0 and 1 should be valid
        assert crawler._is_valid_url("https://example.com", 0) is True
        assert crawler._is_valid_url("https://example.com/page", 1) is True

        # Depth 2 exceeds max_depth of 1
        assert crawler._is_valid_url("https://example.com/page", 2) is False

    def test_is_valid_url_rejects_visited(self):
        """Test that already visited URLs are rejected."""
        from web_scraper_rag.crawler import WebCrawler

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])

        url = "https://example.com/page"
        crawler.visited_urls.add(url)

        # URL should be rejected because it's already visited
        assert crawler._is_valid_url(url, 0) is False

    def test_is_valid_url_rejects_anchors(self):
        """Test that anchor links are rejected."""
        from web_scraper_rag.crawler import WebCrawler

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])

        assert crawler._is_valid_url("#section", 0) is False
        assert crawler._is_valid_url("data:text/html,test", 0) is False

    def test_is_valid_url_respects_domain_whitelist(self):
        """Test that only whitelisted domains are crawled."""
        from web_scraper_rag.crawler import WebCrawler

        crawler = WebCrawler(
            start_url="https://example.com",
            allowed_domains=["example.com"],
        )

        # example.com should be allowed
        assert crawler._is_valid_url("https://example.com/page", 0) is True

        # other.com should not be allowed
        assert crawler._is_valid_url("https://other.com/page", 0) is False

    def test_extract_links(self):
        """Test link extraction from HTML."""
        from bs4 import BeautifulSoup

        from web_scraper_rag.crawler import WebCrawler

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])

        html = """
        <html>
        <body>
        <a href="/page1">Page 1</a>
        <a href="https://example.com/page2">Page 2</a>
        <a href="https://other.com">Other</a>
        </body>
        </html>
        """

        soup = BeautifulSoup(html, "html.parser")
        links = crawler._extract_links(soup, "https://example.com")

        # Should extract relative and absolute links
        assert any("page1" in link for link in links)
        assert any("page2" in link for link in links)
        assert any("other.com" in link for link in links)

    def test_extract_content(self):
        """Test content extraction from HTML."""
        from bs4 import BeautifulSoup

        from web_scraper_rag.crawler import WebCrawler

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])

        html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
        <nav>Navigation</nav>
        <main>
        <h1>Main Content</h1>
        <p>This is important text.</p>
        </main>
        <footer>Footer</footer>
        </body>
        </html>
        """

        soup = BeautifulSoup(html, "html.parser")
        content = crawler._extract_content(soup)

        # Should extract main content but not nav/footer
        assert "Main Content" in content
        assert "important text" in content
        assert "Navigation" not in content
        assert "Footer" not in content


class TestCrawlParty:
    """Test the crawl_party function."""

    def test_crawl_party_creates_output_directory(self, tmp_path):
        """Test that output directory is created."""
        from web_scraper_rag.crawler import crawl_party

        config = {
            "parties": [
                {
                    "name": "Test Party",
                    "website": "https://example.com",
                    "domains": ["example.com"],
                }
            ]
        }

        output_dir = str(tmp_path / "output")

        # Mock the WebCrawler to avoid real network calls
        with patch("web_scraper_rag.crawler.WebCrawler") as mock_crawler_class:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = "# Test Content"
            mock_crawler_class.return_value = mock_crawler

            crawl_party(
                party_name="Test Party",
                config=config,
                output_dir=output_dir,
                output_format="markdown",
                include_pdfs=False,
                follow_links=True,
                depth=2,
                verbose=False,
            )

            # Output directory should be created
            assert (tmp_path / "output").exists()

            # Output file should be created
            assert (tmp_path / "output" / "test_party.md").exists()


class TestCrawlAllParties:
    """Test the crawl_all_parties function."""

    def test_crawl_all_parties_count(self, tmp_path, sample_config):
        """Test that all parties are crawled."""
        from web_scraper_rag.crawler import crawl_all_parties

        output_dir = str(tmp_path)

        # Mock the WebCrawler to avoid real network calls
        with patch("web_scraper_rag.crawler.WebCrawler") as mock_crawler_class:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = "# Test Content"
            mock_crawler_class.return_value = mock_crawler

            crawl_all_parties(
                config=sample_config,
                output_dir=output_dir,
                output_format="markdown",
                include_pdfs=False,
                follow_links=True,
                depth=2,
                verbose=False,
            )

            # Should call WebCrawler for each party (sample has 2)
            assert mock_crawler_class.call_count == 2
