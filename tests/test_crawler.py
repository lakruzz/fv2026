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
        assert crawler.ignore_urls == []
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

    def test_is_valid_url_rejects_canonical_visited(self):
        """Test that canonical URL variants are treated as visited."""
        from web_scraper_rag.crawler import WebCrawler

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])
        crawler.visited_urls.add("https://example.com/")

        assert crawler._is_valid_url("https://example.com", 0) is False

    def test_is_valid_url_rejects_anchors(self):
        """Test that anchor links are rejected."""
        from web_scraper_rag.crawler import WebCrawler

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])

        assert crawler._is_valid_url("#section", 0) is False
        assert crawler._is_valid_url("data:text/html,test", 0) is False

    def test_is_valid_url_rejects_ignored_patterns(self):
        """Test that configured ignored URL patterns are rejected."""
        from web_scraper_rag.crawler import WebCrawler

        crawler = WebCrawler(
            start_url="https://example.com",
            allowed_domains=["example.com"],
            ignore_urls=["/admin", "?print=true"],
        )

        assert crawler._is_valid_url("https://example.com/admin", 0) is False
        assert crawler._is_valid_url("https://example.com/page?print=true", 0) is False
        assert crawler._is_valid_url("https://example.com/page", 0) is True

    def test_is_valid_url_rejects_ignored_glob_patterns(self):
        """Test that glob ignore patterns are applied to URL and path."""
        from web_scraper_rag.crawler import WebCrawler

        crawler = WebCrawler(
            start_url="https://www.alternativet.dk",
            allowed_domains=["alternativet.dk"],
            ignore_urls=["*/personer/*", "https://dialog.alternativet.dk/*"],
        )

        assert (
            crawler._is_valid_url("https://www.alternativet.dk/personer/folketingskandidater", 1)
            is False
        )
        assert crawler._is_valid_url("https://dialog.alternativet.dk/", 1) is False
        assert crawler._is_valid_url("https://www.alternativet.dk/aktuelt/", 1) is True

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

    def test_dryrun_logs_ignore_once(self, capsys):
        """Test dry-run logs ignored URLs once with visual marker."""
        from web_scraper_rag.crawler import WebCrawler

        crawler = WebCrawler(
            start_url="https://example.com",
            allowed_domains=["example.com"],
            ignore_urls=["*/personer/*"],
            dry_run=True,
            verbose=False,
        )

        crawler._log_dryrun_decision(
            "https://example.com/personer/folketing",
            should_crawl=False,
            reason="ignored by pattern: */personer/*",
        )
        crawler._log_dryrun_decision(
            "https://example.com/personer/folketing",
            should_crawl=False,
            reason="ignored by pattern: */personer/*",
        )

        output = capsys.readouterr().err
        assert output.count("https://example.com/personer/folketing") == 1
        assert "❌ [ignore]" in output

    def test_dryrun_hides_already_visited_when_not_verbose(self, capsys):
        """Test dry-run suppresses low-signal ignore reasons unless verbose."""
        from web_scraper_rag.crawler import WebCrawler

        crawler = WebCrawler(
            start_url="https://example.com",
            allowed_domains=["example.com"],
            dry_run=True,
            verbose=False,
        )

        crawler._log_dryrun_decision(
            "https://example.com/page",
            should_crawl=False,
            reason="already visited",
        )

        output = capsys.readouterr().err
        assert output == ""

    def test_dryrun_shows_already_visited_when_verbose(self, capsys):
        """Test dry-run includes low-signal reasons when verbose is enabled."""
        from web_scraper_rag.crawler import WebCrawler

        crawler = WebCrawler(
            start_url="https://example.com",
            allowed_domains=["example.com"],
            dry_run=True,
            verbose=True,
        )

        crawler._log_dryrun_decision(
            "https://example.com/page",
            should_crawl=False,
            reason="already visited",
        )

        output = capsys.readouterr().err
        assert "❌ [ignore]" in output
        assert "already visited" in output

    def test_detects_cloudflare_challenge_and_reports_once(self, capsys):
        """Test that Cloudflare challenge pages are detected and reported once."""
        from web_scraper_rag.crawler import WebCrawler

        crawler = WebCrawler(
            start_url="https://example.com",
            allowed_domains=["example.com"],
            verbose=False,
        )

        html = (
            "<html><head><title>Just a moment...</title></head>"
            "<body><script src='/cdn-cgi/challenge-platform/h/g/orchestrate/chl_page/v1'></script>"
            "</body></html>"
        )

        provider = crawler._detect_bot_challenge(html=html, title="Just a moment...")
        assert provider == "Cloudflare"

        crawler._report_bot_challenge("https://konservative.dk/", provider)
        crawler._report_bot_challenge("https://konservative.dk/", provider)

        output = capsys.readouterr().err
        assert output.count("Challenge detected (Cloudflare)") == 1

    def test_has_graphical_display_false_without_env(self, monkeypatch):
        """Test display detection when no GUI environment variables are set."""
        from web_scraper_rag.crawler import WebCrawler

        monkeypatch.setattr("web_scraper_rag.crawler.system", lambda: "Linux")
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])
        assert crawler._has_graphical_display() is False

    def test_has_graphical_display_true_with_display_env(self, monkeypatch):
        """Test display detection when DISPLAY is set."""
        from web_scraper_rag.crawler import WebCrawler

        monkeypatch.setattr("web_scraper_rag.crawler.system", lambda: "Linux")
        monkeypatch.setenv("DISPLAY", ":0")

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])
        assert crawler._has_graphical_display() is True

    def test_has_graphical_display_true_on_macos_without_display_env(self, monkeypatch):
        """Test display detection accepts macOS native GUI without DISPLAY vars."""
        from web_scraper_rag.crawler import WebCrawler

        monkeypatch.setattr("web_scraper_rag.crawler.system", lambda: "Darwin")
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])
        assert crawler._has_graphical_display() is True


class TestCrawlParty:
    """Test the crawl_party function."""

    def test_crawl_party_creates_output_directory(self, tmp_path):
        """Test that output directory is created."""
        from web_scraper_rag.crawler import crawl_party

        config = {
            "sites": [
                {
                    "name": "Test Party",
                    "website": "https://example.com",
                    "depth": 2,
                    "ignore_urls": [],
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
                dry_run=False,
                quiet=False,
                verbose=False,
            )

            # Output directory should be created
            assert (tmp_path / "output").exists()

            # Output file should be created
            assert (tmp_path / "output" / "test_party.md").exists()

    def test_crawl_party_uses_global_depth_when_site_missing_depth(self, tmp_path):
        """Test global depth is used when site depth is not set."""
        from web_scraper_rag.crawler import crawl_party

        config = {
            "sites": [
                {"name": "Test Party", "website": "https://example.com", "domains": ["example.com"]}
            ],
            "crawl_settings": {"depth": 4, "ignore_urls": []},
        }

        with patch("web_scraper_rag.crawler.WebCrawler") as mock_crawler_class:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = "# Test Content"
            mock_crawler_class.return_value = mock_crawler

            crawl_party(
                party_name="Test Party",
                config=config,
                output_dir=str(tmp_path / "output"),
                output_format="markdown",
                include_pdfs=False,
                follow_links=True,
                depth=None,
                dry_run=False,
                quiet=False,
                verbose=False,
            )

            assert mock_crawler_class.call_args.kwargs["max_depth"] == 4

    def test_crawl_party_site_depth_overrides_global_depth(self, tmp_path):
        """Test site depth overrides global depth."""
        from web_scraper_rag.crawler import crawl_party

        config = {
            "sites": [
                {
                    "name": "Test Party",
                    "website": "https://example.com",
                    "depth": 2,
                    "ignore_urls": [],
                    "domains": ["example.com"],
                }
            ],
            "crawl_settings": {"depth": 4, "ignore_urls": []},
        }

        with patch("web_scraper_rag.crawler.WebCrawler") as mock_crawler_class:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = "# Test Content"
            mock_crawler_class.return_value = mock_crawler

            crawl_party(
                party_name="Test Party",
                config=config,
                output_dir=str(tmp_path / "output"),
                output_format="markdown",
                include_pdfs=False,
                follow_links=True,
                depth=None,
                dry_run=False,
                quiet=False,
                verbose=False,
            )

            assert mock_crawler_class.call_args.kwargs["max_depth"] == 2

    def test_crawl_party_merges_global_and_site_ignore_urls(self, tmp_path):
        """Test global ignore_urls are supplemented by site ignore_urls."""
        from web_scraper_rag.crawler import crawl_party

        config = {
            "sites": [
                {
                    "name": "Test Party",
                    "website": "https://example.com",
                    "depth": 2,
                    "ignore_urls": ["*/site-only*", "*/shared*"],
                    "domains": ["example.com"],
                }
            ],
            "crawl_settings": {"depth": 4, "ignore_urls": ["*/global*", "*/shared*"]},
        }

        with patch("web_scraper_rag.crawler.WebCrawler") as mock_crawler_class:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = "# Test Content"
            mock_crawler_class.return_value = mock_crawler

            crawl_party(
                party_name="Test Party",
                config=config,
                output_dir=str(tmp_path / "output"),
                output_format="markdown",
                include_pdfs=False,
                follow_links=True,
                depth=None,
                dry_run=False,
                quiet=False,
                verbose=False,
            )

            assert mock_crawler_class.call_args.kwargs["ignore_urls"] == [
                "*/global*",
                "*/shared*",
                "*/site-only*",
            ]


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
                dry_run=False,
                quiet=False,
                verbose=False,
            )

            # Should call WebCrawler for each party (sample has 2)
            assert mock_crawler_class.call_count == 2

    def test_dry_run_does_not_write_output(self, tmp_path):
        """Test that dry-run mode does not create output files."""
        from web_scraper_rag.crawler import crawl_party

        config = {
            "sites": [
                {
                    "name": "Test Party",
                    "website": "https://example.com",
                    "depth": 2,
                    "ignore_urls": [],
                    "domains": ["example.com"],
                }
            ]
        }

        output_dir = str(tmp_path / "output")

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
                dry_run=True,
                quiet=False,
                verbose=False,
            )

            # Directory can exist, but output file should not be written in dry run.
            assert not (tmp_path / "output" / "test_party.md").exists()
