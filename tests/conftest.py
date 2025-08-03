"""Test configuration and fixtures."""

import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from thought.client import NotionAPIClient
from thought.logging_utils import configure_logging

# Set a fake token for testing if not already set
if "NOTION_ACCESS_TOKEN" not in os.environ:
    os.environ["NOTION_ACCESS_TOKEN"] = "fake-test-token"


@pytest.fixture(name="notion_api_client")
def notion_api_client() -> NotionAPIClient:
    """
    Mocked instance of NotionAPIClient for testing
    """
    with patch("thought.client.NotionClient") as mock_notion_client:
        # Create a mock Notion client instance
        mock_notion_client_instance = MagicMock()
        mock_notion_client.return_value = mock_notion_client_instance

        # Create the NotionAPIClient which will use the mocked NotionClient
        client = NotionAPIClient()

        return client


@pytest.fixture()
def notion_api_client_client(
    notion_api_client: NotionAPIClient,
):
    """
    Fixture: NotionAPIClient.client
    """
    return notion_api_client.client


@pytest.fixture
def caplog_at_level(caplog):
    """Configure caplog to capture logs at specific levels."""

    def _set_level(level):
        caplog.set_level(level)
        return caplog

    return _set_level


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing log calls."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def temp_log_file(tmp_path):
    """Create a temporary log file for testing file logging."""
    log_file = tmp_path / "test.log"
    return log_file


@pytest.fixture
def configure_test_logging():
    """Configure logging for tests to avoid interfering with test output."""
    # Store original handlers
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level

    # Configure for testing (quiet mode)
    configure_logging(quiet=True)

    yield

    # Restore original configuration
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    for handler in original_handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(original_level)


@pytest.fixture
def sample_markdown_files(tmp_path):
    """Create sample markdown files for testing."""
    files = []

    # Create a simple markdown file
    file1 = tmp_path / "test1.md"
    file1.write_text("""---
title: Test Document 1
tags: [test, sample]
priority: 5
---

# Test Document 1

This is a test document.
""")
    files.append(file1)

    # Create another markdown file with different frontmatter
    file2 = tmp_path / "test2.md"
    file2.write_text("""---
title: Test Document 2
status: In Progress
assignee: test@example.com
---

# Test Document 2

Another test document.
""")
    files.append(file2)

    # Create a subdirectory with a file
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    file3 = subdir / "nested.md"
    file3.write_text("""---
title: Nested Document
tags: [nested, test]
---

# Nested Document

This is nested in a subdirectory.
""")
    files.append(file3)

    return files
