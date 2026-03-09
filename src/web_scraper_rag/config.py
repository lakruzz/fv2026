"""Configuration management for web scraper."""

import sys
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """Raised when configuration is invalid."""


def load_config(config_path: str, verbose: bool = False) -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to the configuration file
        verbose: Enable verbose logging

    Returns:
        Parsed configuration dictionary

    Raises:
        ConfigError: If configuration file cannot be loaded or parsed
    """
    path = Path(config_path)

    if not path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not config:
            raise ConfigError(f"Configuration file is empty: {config_path}")

        if verbose:
            print(f"Configuration loaded from: {config_path}", file=sys.stderr)

        return config
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse YAML configuration: {e}") from e
    except OSError as e:
        raise ConfigError(f"Failed to read configuration file: {e}") from e


def validate_party_config(party: dict[str, Any]) -> None:
    """Validate a party configuration object.

    Args:
        party: Party configuration dictionary

    Raises:
        ConfigError: If required fields are missing
    """
    required_fields = ["name", "website", "depth", "ignore_urls"]
    for field in required_fields:
        if field not in party:
            raise ConfigError(f"Party config missing required field: {field}")

    if not isinstance(party["depth"], int) or party["depth"] < 0:
        raise ConfigError("Party config field 'depth' must be a non-negative integer")

    if not isinstance(party["ignore_urls"], list):
        raise ConfigError("Party config field 'ignore_urls' must be a list")


def get_party_by_name(config: dict[str, Any], party_name: str) -> dict[str, Any]:
    """Get party configuration by name.

    Args:
        config: Full configuration dictionary
        party_name: Name or identifier of the party

    Returns:
        Party configuration dictionary

    Raises:
        ConfigError: If party not found in configuration
    """
    if "parties" not in config:
        raise ConfigError("Configuration has no 'parties' section")

    parties = config["parties"]
    if not isinstance(parties, list):
        raise ConfigError("'parties' in configuration must be a list")

    # Case-insensitive search by name
    for party in parties:
        validate_party_config(party)
        if party.get("name", "").lower() == party_name.lower():
            return party

    raise ConfigError(f"Party not found in configuration: {party_name}")


def get_all_parties(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Get all party configurations.

    Args:
        config: Full configuration dictionary

    Returns:
        List of party configuration dictionaries

    Raises:
        ConfigError: If configuration is invalid
    """
    if "parties" not in config:
        raise ConfigError("Configuration has no 'parties' section")

    parties = config["parties"]
    if not isinstance(parties, list):
        raise ConfigError("'parties' in configuration must be a list")

    for party in parties:
        validate_party_config(party)

    return parties
