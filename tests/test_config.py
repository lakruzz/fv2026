"""Tests for configuration module."""

import pytest

from web_scraper_rag.config import (
    ConfigError,
    get_all_parties,
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


class TestValidatePartyConfig:
    """Test party configuration validation."""

    def test_valid_party(self):
        """Test validation of a valid party config."""
        party = {"name": "Test Party", "website": "https://example.com"}
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
        with pytest.raises(ConfigError, match="Party not found"):
            get_party_by_name(sample_config, "NonExistent")

    def test_no_parties_section(self):
        """Test error when config has no parties section."""
        config = {}
        with pytest.raises(ConfigError, match="no 'parties' section"):
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
        """Test error when config has no parties section."""
        config = {}
        with pytest.raises(ConfigError, match="no 'parties' section"):
            get_all_parties(config)

    def test_invalid_parties_format(self):
        """Test error when parties is not a list."""
        config = {"parties": "not a list"}
        with pytest.raises(ConfigError, match="must be a list"):
            get_all_parties(config)
