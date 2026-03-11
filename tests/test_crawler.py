"""Tests for the web crawler implementation."""

from unittest.mock import MagicMock, patch


class TestWebCrawler:
    """Test the WebCrawler class."""

    def test_crawler_initialization(self):
        """Test crawler can be initialized with required parameters."""
        from sitemix.crawler import WebCrawler

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
        from sitemix.crawler import WebCrawler

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
        from sitemix.crawler import WebCrawler

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])

        url = "https://example.com/page"
        crawler.visited_urls.add(url)

        # URL should be rejected because it's already visited
        assert crawler._is_valid_url(url, 0) is False

    def test_is_valid_url_rejects_canonical_visited(self):
        """Test that canonical URL variants are treated as visited."""
        from sitemix.crawler import WebCrawler

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])
        crawler.visited_urls.add("https://example.com/")

        assert crawler._is_valid_url("https://example.com", 0) is False

    def test_is_valid_url_rejects_anchors(self):
        """Test that anchor links are rejected."""
        from sitemix.crawler import WebCrawler

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])

        assert crawler._is_valid_url("#section", 0) is False
        assert crawler._is_valid_url("data:text/html,test", 0) is False

    def test_is_valid_url_rejects_ignored_patterns(self):
        """Test that configured ignored URL patterns are rejected."""
        from sitemix.crawler import WebCrawler

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
        from sitemix.crawler import WebCrawler

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
        from sitemix.crawler import WebCrawler

        crawler = WebCrawler(
            start_url="https://example.com",
            allowed_domains=["example.com"],
        )

        # example.com should be allowed
        assert crawler._is_valid_url("https://example.com/page", 0) is True

        # other.com should not be allowed
        assert crawler._is_valid_url("https://other.com/page", 0) is False

    def test_is_valid_url_literal_domain_does_not_match_arbitrary_subdomains(self):
        """Test literal domains match exact host and not unrelated subdomains."""
        from sitemix.crawler import WebCrawler

        crawler = WebCrawler(
            start_url="https://enhedslisten.dk",
            allowed_domains=["enhedslisten.dk"],
        )

        assert crawler._is_valid_url("https://enhedslisten.dk/politik", 0) is True
        assert crawler._is_valid_url("https://www.enhedslisten.dk/politik", 0) is True
        assert crawler._is_valid_url("https://shop.enhedslisten.dk/", 0) is False
        assert crawler._is_valid_url("https://mit.enhedslisten.dk/", 0) is False

    def test_is_valid_url_glob_domain_matches_subdomains(self):
        """Test wildcard domains enable explicit subdomain matching."""
        from sitemix.crawler import WebCrawler

        crawler = WebCrawler(
            start_url="https://shop.enhedslisten.dk",
            allowed_domains=["*.enhedslisten.dk"],
        )

        assert crawler._is_valid_url("https://shop.enhedslisten.dk/", 0) is True
        assert crawler._is_valid_url("https://mit.enhedslisten.dk/", 0) is True
        assert crawler._is_valid_url("https://enhedslisten.dk/", 0) is False

    def test_extract_links(self):
        """Test link extraction from HTML."""
        from bs4 import BeautifulSoup

        from sitemix.crawler import WebCrawler

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

        from sitemix.crawler import WebCrawler

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

    def test_is_pdf_url_detection(self):
        """Test PDF URL detection based on path suffix."""
        from sitemix.crawler import WebCrawler

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])

        assert crawler._is_pdf_url("https://example.com/files/program.pdf") is True
        assert crawler._is_pdf_url("https://example.com/files/program.PDF") is True
        assert crawler._is_pdf_url("https://example.com/page?id=123") is False

    def test_is_valid_url_rejects_known_binary_assets(self):
        """Test known non-PDF binary assets are skipped automatically."""
        from sitemix.crawler import WebCrawler

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])

        assert crawler._is_valid_url("https://example.com/image.jpg", 0) is False
        assert crawler._is_valid_url("https://example.com/clip.mov", 0) is False
        assert crawler._is_valid_url("https://example.com/document.pdf", 0) is True

    def test_process_page_pdf_uses_pdf_parser_when_enabled(self):
        """Test PDF URLs are parsed via PDF path when include_pdfs is enabled."""
        from sitemix.crawler import WebCrawler

        crawler = WebCrawler(
            start_url="https://example.com",
            allowed_domains=["example.com"],
            include_pdfs=True,
        )

        with patch.object(crawler, "_fetch_pdf_text", return_value=("[PDF] test.pdf", "PDF text")):
            result = crawler._process_page("https://example.com/test.pdf", 0, [])

        assert result == ("[PDF] test.pdf", "PDF text")

    def test_process_page_pdf_skipped_when_disabled(self):
        """Test PDF URLs are skipped when include_pdfs is disabled."""
        from sitemix.crawler import WebCrawler

        crawler = WebCrawler(
            start_url="https://example.com",
            allowed_domains=["example.com"],
            include_pdfs=False,
        )

        result = crawler._process_page("https://example.com/test.pdf", 0, [])
        assert result is None

    def test_dryrun_logs_ignore_once(self, capsys):
        """Test dry-run logs ignored URLs once with visual marker."""
        from sitemix.crawler import WebCrawler

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
        from sitemix.crawler import WebCrawler

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
        from sitemix.crawler import WebCrawler

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

    def test_dryrun_suppresses_unsupported_scheme_even_verbose(self, capsys):
        """Test unsupported schemes (e.g., mailto:) are never shown in dry-run output."""
        from sitemix.crawler import WebCrawler

        crawler = WebCrawler(
            start_url="https://example.com",
            allowed_domains=["example.com"],
            dry_run=True,
            verbose=True,
        )

        crawler._log_dryrun_decision(
            "mailto:test@example.com",
            should_crawl=False,
            reason="unsupported scheme",
        )

        output = capsys.readouterr().err
        assert output == ""

    def test_detects_cloudflare_challenge_and_reports_once(self, capsys):
        """Test that Cloudflare challenge pages are detected and reported once."""
        from sitemix.crawler import WebCrawler

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
        from sitemix.crawler import WebCrawler

        monkeypatch.setattr("sitemix.crawler.system", lambda: "Linux")
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])
        assert crawler._has_graphical_display() is False

    def test_has_graphical_display_true_with_display_env(self, monkeypatch):
        """Test display detection when DISPLAY is set."""
        from sitemix.crawler import WebCrawler

        monkeypatch.setattr("sitemix.crawler.system", lambda: "Linux")
        monkeypatch.setenv("DISPLAY", ":0")

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])
        assert crawler._has_graphical_display() is True

    def test_has_graphical_display_true_on_macos_without_display_env(self, monkeypatch):
        """Test display detection accepts macOS native GUI without DISPLAY vars."""
        from sitemix.crawler import WebCrawler

        monkeypatch.setattr("sitemix.crawler.system", lambda: "Darwin")
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

        crawler = WebCrawler(start_url="https://example.com", allowed_domains=["example.com"])
        assert crawler._has_graphical_display() is True


class TestCrawlSite:
    """Test the crawl_site function."""

    def test_crawl_site_creates_output_directory(self, tmp_path):
        """Test that output directory is created."""
        from sitemix.crawler import crawl_site

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
        with patch("sitemix.crawler.WebCrawler") as mock_crawler_class:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = "# Test Content"
            mock_crawler_class.return_value = mock_crawler

            crawl_site(
                site_name="Test Party",
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

    def test_crawl_site_uses_global_depth_when_site_missing_depth(self, tmp_path):
        """Test global depth is used when site depth is not set."""
        from sitemix.crawler import crawl_site

        config = {
            "sites": [
                {"name": "Test Party", "website": "https://example.com", "domains": ["example.com"]}
            ],
            "crawl_settings": {"depth": 4, "ignore_urls": []},
        }

        with patch("sitemix.crawler.WebCrawler") as mock_crawler_class:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = "# Test Content"
            mock_crawler_class.return_value = mock_crawler

            crawl_site(
                site_name="Test Party",
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

    def test_crawl_site_site_depth_overrides_global_depth(self, tmp_path):
        """Test site depth overrides global depth."""
        from sitemix.crawler import crawl_site

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

        with patch("sitemix.crawler.WebCrawler") as mock_crawler_class:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = "# Test Content"
            mock_crawler_class.return_value = mock_crawler

            crawl_site(
                site_name="Test Party",
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

    def test_crawl_site_merges_global_and_site_ignore_urls(self, tmp_path):
        """Test global ignore_urls are supplemented by site ignore_urls."""
        from sitemix.crawler import crawl_site

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

        with patch("sitemix.crawler.WebCrawler") as mock_crawler_class:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = "# Test Content"
            mock_crawler_class.return_value = mock_crawler

            crawl_site(
                site_name="Test Party",
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

    def test_crawl_site_uses_global_include_pdfs_default(self, tmp_path):
        """Test global include_pdfs is used when CLI flag is omitted."""
        from sitemix.crawler import crawl_site

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
            "crawl_settings": {"depth": 3, "ignore_urls": [], "include_pdfs": True},
        }

        with patch("sitemix.crawler.WebCrawler") as mock_crawler_class:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = "# Test Content"
            mock_crawler_class.return_value = mock_crawler

            crawl_site(
                site_name="Test Party",
                config=config,
                output_dir=str(tmp_path / "output"),
                output_format="markdown",
                include_pdfs=None,
                follow_links=True,
                depth=None,
                dry_run=False,
                quiet=False,
                verbose=False,
            )

            assert mock_crawler_class.call_args.kwargs["include_pdfs"] is True

    def test_crawl_site_site_include_pdfs_overrides_global(self, tmp_path):
        """Test site include_pdfs overrides global include_pdfs."""
        from sitemix.crawler import crawl_site

        config = {
            "sites": [
                {
                    "name": "Test Party",
                    "website": "https://example.com",
                    "depth": 2,
                    "include_pdfs": False,
                    "ignore_urls": [],
                    "domains": ["example.com"],
                }
            ],
            "crawl_settings": {"depth": 3, "ignore_urls": [], "include_pdfs": True},
        }

        with patch("sitemix.crawler.WebCrawler") as mock_crawler_class:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = "# Test Content"
            mock_crawler_class.return_value = mock_crawler

            crawl_site(
                site_name="Test Party",
                config=config,
                output_dir=str(tmp_path / "output"),
                output_format="markdown",
                include_pdfs=None,
                follow_links=True,
                depth=None,
                dry_run=False,
                quiet=False,
                verbose=False,
            )

            assert mock_crawler_class.call_args.kwargs["include_pdfs"] is False

    def test_crawl_site_cli_include_pdfs_overrides_config(self, tmp_path):
        """Test CLI include_pdfs=True overrides site/global config defaults."""
        from sitemix.crawler import crawl_site

        config = {
            "sites": [
                {
                    "name": "Test Party",
                    "website": "https://example.com",
                    "depth": 2,
                    "include_pdfs": False,
                    "ignore_urls": [],
                    "domains": ["example.com"],
                }
            ],
            "crawl_settings": {"depth": 3, "ignore_urls": [], "include_pdfs": False},
        }

        with patch("sitemix.crawler.WebCrawler") as mock_crawler_class:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = "# Test Content"
            mock_crawler_class.return_value = mock_crawler

            crawl_site(
                site_name="Test Party",
                config=config,
                output_dir=str(tmp_path / "output"),
                output_format="markdown",
                include_pdfs=True,
                follow_links=True,
                depth=None,
                dry_run=False,
                quiet=False,
                verbose=False,
            )

            assert mock_crawler_class.call_args.kwargs["include_pdfs"] is True


class TestCrawlAllSites:
    """Test the crawl_all_sites function."""

    def test_crawl_all_sites_count(self, tmp_path, sample_config):
        """Test that all parties are crawled."""
        from sitemix.crawler import crawl_all_sites

        output_dir = str(tmp_path)

        # Mock the WebCrawler to avoid real network calls
        with patch("sitemix.crawler.WebCrawler") as mock_crawler_class:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = "# Test Content"
            mock_crawler_class.return_value = mock_crawler

            crawl_all_sites(
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
        from sitemix.crawler import crawl_site

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

        with patch("sitemix.crawler.WebCrawler") as mock_crawler_class:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = "# Test Content"
            mock_crawler_class.return_value = mock_crawler

            crawl_site(
                site_name="Test Party",
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
