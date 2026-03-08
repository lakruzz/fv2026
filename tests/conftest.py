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
        "parties": [
            {
                "name": "Alternativet",
                "website": "https://www.alternativet.dk",
                "domains": ["alternativet.dk"],
                "pdf_patterns": ["manifest", "program", "*.pdf"],
            },
            {
                "name": "Enhedslisten",
                "website": "https://www.enhedslisten.dk",
                "domains": ["enhedslisten.dk"],
                "pdf_patterns": ["*.pdf"],
            },
        ]
    }
