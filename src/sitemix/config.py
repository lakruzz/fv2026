"""Configuration management for web scraper."""

import sys
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """Raised when configuration is invalid."""


def discover_default_config_path(base_dir: Path | None = None) -> Path:
    """Discover the default config file in .web-scraber-rag.

    Resolution order:
    1. ./.web-scraber-rag/sites.yml
    2. ./.web-scraber-rag/sites.yaml
    3. first alphanumeric match of ./.web-scraber-rag/*.yml and *.yaml
    """
    root = base_dir or Path.cwd()
    config_dir = root / ".web-scraber-rag"

    if not config_dir.exists() or not config_dir.is_dir():
        raise ConfigError("Configuration directory not found: .web-scraber-rag")

    preferred_candidates = [config_dir / "sites.yml", config_dir / "sites.yaml"]
    for candidate in preferred_candidates:
        if candidate.is_file():
            return candidate

    wildcard_candidates = sorted(
        [
            path
            for pattern in ("*.yml", "*.yaml")
            for path in config_dir.glob(pattern)
            if path.is_file()
        ],
        key=lambda path: path.name,
    )

    if wildcard_candidates:
        return wildcard_candidates[0]

    raise ConfigError("No YAML config file found in .web-scraber-rag")


def load_config(config_path: str | None = None, verbose: bool = False) -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to the configuration file. If omitted, discover a
            default file in ./.web-scraber-rag
        verbose: Enable verbose logging

    Returns:
        Parsed configuration dictionary

    Raises:
        ConfigError: If configuration file cannot be loaded or parsed
    """
    path = Path(config_path) if config_path else discover_default_config_path()

    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")

    try:
        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not config:
            raise ConfigError(f"Configuration file is empty: {path}")

        if verbose:
            print(f"Configuration loaded from: {path}", file=sys.stderr)

        return config
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse YAML configuration: {e}") from e
    except OSError as e:
        raise ConfigError(f"Failed to read configuration file: {e}") from e


def validate_site_config(site: dict[str, Any]) -> None:
    """Validate a site configuration object.

    Args:
        site: Site configuration dictionary

    Raises:
        ConfigError: If required fields are missing
    """
    required_fields = ["name", "website"]
    for field in required_fields:
        if field not in site:
            raise ConfigError(f"Site config missing required field: {field}")

    if "depth" in site and (not isinstance(site["depth"], int) or site["depth"] < 0):
        raise ConfigError("Site config field 'depth' must be a non-negative integer")

    if "ignore_urls" in site and not isinstance(site["ignore_urls"], list):
        raise ConfigError("Site config field 'ignore_urls' must be a list")

    if "include_pdfs" in site and not isinstance(site["include_pdfs"], bool):
        raise ConfigError("Site config field 'include_pdfs' must be a boolean")


def get_global_crawl_defaults(config: dict[str, Any]) -> tuple[int | None, list[str], bool | None]:
    """Return global crawl defaults from config.

    Global defaults are read from top-level `crawl_settings` and currently
    support:
    - depth (non-negative int)
    - ignore_urls (list[str])
    - include_pdfs (bool)
    """
    crawl_settings = config.get("crawl_settings", {})
    if not isinstance(crawl_settings, dict):
        raise ConfigError("'crawl_settings' in configuration must be a mapping")

    depth = crawl_settings.get("depth")
    if depth is not None and (not isinstance(depth, int) or depth < 0):
        raise ConfigError("Global crawl setting 'depth' must be a non-negative integer")

    ignore_urls = crawl_settings.get("ignore_urls", [])
    if not isinstance(ignore_urls, list):
        raise ConfigError("Global crawl setting 'ignore_urls' must be a list")

    include_pdfs = crawl_settings.get("include_pdfs")
    if include_pdfs is not None and not isinstance(include_pdfs, bool):
        raise ConfigError("Global crawl setting 'include_pdfs' must be a boolean")

    return depth, ignore_urls, include_pdfs


def get_site_by_name(config: dict[str, Any], site_name: str) -> dict[str, Any]:
    """Get site configuration by name.

    Args:
        config: Full configuration dictionary
        site_name: Name or identifier of the site

    Returns:
        Site configuration dictionary

    Raises:
        ConfigError: If site not found in configuration
    """
    if "sites" not in config:
        raise ConfigError("Configuration has no 'sites' section")

    sites = config["sites"]
    if not isinstance(sites, list):
        raise ConfigError("'sites' in configuration must be a list")

    # Case-insensitive search by name
    for site in sites:
        validate_site_config(site)
        if site.get("name", "").lower() == site_name.lower():
            return site

    raise ConfigError(f"Site not found in configuration: {site_name}")


def get_all_sites(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Get all site configurations.

    Args:
        config: Full configuration dictionary

    Returns:
        List of site configuration dictionaries

    Raises:
        ConfigError: If configuration is invalid
    """
    if "sites" not in config:
        raise ConfigError("Configuration has no 'sites' section")

    sites = config["sites"]
    if not isinstance(sites, list):
        raise ConfigError("'sites' in configuration must be a list")

    for site in sites:
        validate_site_config(site)

    return sites
