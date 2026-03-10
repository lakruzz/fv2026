"""Tests for configuration module."""

import pytest

from web_scraper_rag.config import (
    ConfigError,
    discover_default_config_path,
    get_all_parties,
    get_global_crawl_defaults,
    get_party_by_name,
    load_config,
    validate_party_config,
)


class TestLoadConfig:
    """Test configuration loading."""

    def test_load_valid_config(self, sample_config, temp_dir):
        """Test loading a valid configuration file."""
        config_file = temp_dir / "config.yaml"
        import yaml

        with open(config_file, "w") as f:
            yaml.dump(sample_config, f)

        config = load_config(str(config_file))
        assert config == sample_config

    def test_load_missing_config(self):
        """Test loading a non-existent configuration file."""
        with pytest.raises(ConfigError, match="Configuration file not found"):
            load_config("/nonexistent/config.yaml")

    def test_load_empty_config(self, temp_dir):
        """Test loading an empty configuration file."""
        config_file = temp_dir / "empty.yaml"
        config_file.write_text("")

        with pytest.raises(ConfigError, match="Configuration file is empty"):
            load_config(str(config_file))

    def test_load_invalid_yaml(self, temp_dir):
        """Test loading an invalid YAML file."""
        config_file = temp_dir / "invalid.yaml"
        config_file.write_text("{ invalid yaml [")

        with pytest.raises(ConfigError, match="Failed to parse YAML"):
            load_config(str(config_file))

    def test_auto_discover_prefers_sites_yml(self, temp_dir, monkeypatch):
        """Test discovery prefers sites.yml over other YAML files."""
        config_dir = temp_dir / ".web-scraber-rag"
        config_dir.mkdir()
        (config_dir / "aaa.yaml").write_text("sites: []")
        (config_dir / "sites.yml").write_text("sites: []")
        (config_dir / "sites.yaml").write_text("sites: []")

        monkeypatch.chdir(temp_dir)

        assert discover_default_config_path() == (config_dir / "sites.yml")

    def test_auto_discover_falls_back_to_first_alphanumeric(self, temp_dir, monkeypatch):
        """Test discovery falls back to first alphanumeric YAML filename."""
        config_dir = temp_dir / ".web-scraber-rag"
        config_dir.mkdir()
        (config_dir / "zebra.yaml").write_text("sites: []")
        (config_dir / "alpha.yml").write_text("sites: []")

        monkeypatch.chdir(temp_dir)

        assert discover_default_config_path() == (config_dir / "alpha.yml")

    def test_auto_discover_missing_directory(self, temp_dir, monkeypatch):
        """Test discovery fails when .web-scraber-rag does not exist."""
        monkeypatch.chdir(temp_dir)

        with pytest.raises(ConfigError, match="Configuration directory not found"):
            discover_default_config_path()

    def test_load_config_auto_discovery(self, temp_dir, monkeypatch):
        """Test load_config discovers default config when path is omitted."""
        config_dir = temp_dir / ".web-scraber-rag"
        config_dir.mkdir()
        config_file = config_dir / "sites.yaml"
        config_file.write_text(
            "sites:\n  - name: Test\n    website: https://example.com\n    depth: 1\n    ignore_urls: []\n"
        )

        monkeypatch.chdir(temp_dir)
        config = load_config()
        assert "sites" in config


class TestValidatePartyConfig:
    """Test party configuration validation."""

    def test_valid_party(self):
        """Test validation of a valid party config."""
        party = {
            "name": "Test Party",
            "website": "https://example.com",
            "depth": 2,
            "ignore_urls": [],
        }
        validate_party_config(party)  # Should not raise

    def test_valid_party_without_depth_and_ignore_urls(self):
        """Test validation allows site defaults to be provided globally."""
        party = {
            "name": "Test Party",
            "website": "https://example.com",
        }
        validate_party_config(party)  # Should not raise

    def test_missing_name(self):
        """Test validation of party config missing name."""
        party = {"website": "https://example.com"}
        with pytest.raises(ConfigError, match="missing required field: name"):
            validate_party_config(party)

    def test_missing_website(self):
        """Test validation of party config missing website."""
        party = {"name": "Test Party"}
        with pytest.raises(ConfigError, match="missing required field: website"):
            validate_party_config(party)

    def test_missing_depth(self):
        """Test missing depth is allowed (can come from global defaults)."""
        party = {
            "name": "Test Party",
            "website": "https://example.com",
            "ignore_urls": [],
        }
        validate_party_config(party)  # Should not raise

    def test_missing_ignore_urls(self):
        """Test missing ignore_urls is allowed (can come from global defaults)."""
        party = {
            "name": "Test Party",
            "website": "https://example.com",
            "depth": 2,
        }
        validate_party_config(party)  # Should not raise

    def test_invalid_depth_type(self):
        """Test validation of party config with invalid depth type."""
        party = {
            "name": "Test Party",
            "website": "https://example.com",
            "depth": "2",
            "ignore_urls": [],
        }
        with pytest.raises(ConfigError, match="field 'depth' must be"):
            validate_party_config(party)

    def test_invalid_ignore_urls_type(self):
        """Test validation of party config with invalid ignore_urls type."""
        party = {
            "name": "Test Party",
            "website": "https://example.com",
            "depth": 2,
            "ignore_urls": "admin",
        }
        with pytest.raises(ConfigError, match="field 'ignore_urls' must be"):
            validate_party_config(party)

    def test_invalid_include_pdfs_type(self):
        """Test validation of party config with invalid include_pdfs type."""
        party = {
            "name": "Test Party",
            "website": "https://example.com",
            "include_pdfs": "yes",
        }
        with pytest.raises(ConfigError, match="field 'include_pdfs' must be"):
            validate_party_config(party)


class TestGetPartyByName:
    """Test getting party by name."""

    def test_get_existing_party(self, sample_config):
        """Test getting an existing party."""
        party = get_party_by_name(sample_config, "Alternativet")
        assert party["name"] == "Alternativet"
        assert party["website"] == "https://www.alternativet.dk"

    def test_get_party_case_insensitive(self, sample_config):
        """Test case-insensitive party lookup."""
        party = get_party_by_name(sample_config, "alternativet")
        assert party["name"] == "Alternativet"

    def test_get_missing_party(self, sample_config):
        """Test getting a non-existent party."""
        with pytest.raises(ConfigError, match="Site not found"):
            get_party_by_name(sample_config, "NonExistent")

    def test_no_parties_section(self):
        """Test error when config has no sites section."""
        config = {}
        with pytest.raises(ConfigError, match="no 'sites' section"):
            get_party_by_name(config, "Test")


class TestGetAllParties:
    """Test getting all parties."""

    def test_get_all_parties(self, sample_config):
        """Test getting all parties from config."""
        parties = get_all_parties(sample_config)
        assert len(parties) == 2
        assert parties[0]["name"] == "Alternativet"
        assert parties[1]["name"] == "Enhedslisten"

    def test_no_parties_section(self):
        """Test error when config has no sites section."""
        config = {}
        with pytest.raises(ConfigError, match="no 'sites' section"):
            get_all_parties(config)

    def test_invalid_parties_format(self):
        """Test error when sites is not a list."""
        config = {"sites": "not a list"}
        with pytest.raises(ConfigError, match="must be a list"):
            get_all_parties(config)


class TestGlobalCrawlDefaults:
    """Test global crawl defaults."""

    def test_get_defaults_present(self):
        """Test reading global depth and ignore defaults."""
        config = {
            "sites": [],
            "crawl_settings": {
                "depth": 3,
                "ignore_urls": ["*/privacy*", "*/terms*"],
                "include_pdfs": True,
            },
        }
        depth, ignore_urls, include_pdfs = get_global_crawl_defaults(config)
        assert depth == 3
        assert ignore_urls == ["*/privacy*", "*/terms*"]
        assert include_pdfs is True

    def test_get_defaults_missing(self):
        """Test defaults when crawl_settings are absent."""
        depth, ignore_urls, include_pdfs = get_global_crawl_defaults({"sites": []})
        assert depth is None
        assert ignore_urls == []
        assert include_pdfs is None

    def test_invalid_global_depth(self):
        """Test validation for invalid global depth."""
        config = {"sites": [], "crawl_settings": {"depth": -1}}
        with pytest.raises(ConfigError, match="Global crawl setting 'depth'"):
            get_global_crawl_defaults(config)

    def test_invalid_global_ignore_urls(self):
        """Test validation for invalid global ignore_urls."""
        config = {"sites": [], "crawl_settings": {"ignore_urls": "not-a-list"}}
        with pytest.raises(ConfigError, match="Global crawl setting 'ignore_urls'"):
            get_global_crawl_defaults(config)

    def test_invalid_global_include_pdfs(self):
        """Test validation for invalid global include_pdfs."""
        config = {"sites": [], "crawl_settings": {"include_pdfs": "true"}}
        with pytest.raises(ConfigError, match="Global crawl setting 'include_pdfs'"):
            get_global_crawl_defaults(config)
