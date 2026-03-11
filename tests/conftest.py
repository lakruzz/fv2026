"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_config():
    """Provide a sample configuration dictionary."""
    return {
        "sites": [
            {
                "name": "Example Site",
                "website": "https://www.example.com",
                "depth": 2,
                "ignore_urls": [],
                "domains": ["example.com"],
                "pdf_patterns": ["*.pdf"],
            },
            {
                "name": "Another Site",
                "website": "https://www.another-example.org",
                "depth": 2,
                "ignore_urls": [],
                "domains": ["another-example.org"],
                "pdf_patterns": ["*.pdf"],
            },
        ]
    }
