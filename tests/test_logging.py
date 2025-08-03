"""Tests for logging utilities and functionality."""

import logging

from thought.logging_utils import (
    configure_logging,
    get_logger,
    log_api_call,
    log_dry_run_action,
    log_operation_complete,
    log_operation_start,
    log_progress,
)


class TestGetLogger:
    """Test get_logger functionality."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_get_logger_same_name_returns_same_instance(self):
        """Test that get_logger returns the same instance for the same name."""
        logger1 = get_logger("test.module")
        logger2 = get_logger("test.module")
        assert logger1 is logger2


class TestConfigureLogging:
    """Test configure_logging functionality."""

    def teardown_method(self):
        """Clean up logging configuration after each test."""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        root_logger.setLevel(logging.WARNING)

    def test_configure_logging_default(self):
        """Test default logging configuration."""
        configure_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)

    def test_configure_logging_verbose(self):
        """Test verbose logging configuration."""
        configure_logging(verbose=True)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_configure_logging_quiet(self):
        """Test quiet logging configuration."""
        configure_logging(quiet=True)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_configure_logging_with_file(self, temp_log_file):
        """Test logging configuration with file output."""
        configure_logging(log_file=str(temp_log_file))

        root_logger = logging.getLogger()
        # Should have console and file handlers
        expected_handler_count = 2
        assert len(root_logger.handlers) == expected_handler_count

        # Test that file handler was added
        file_handlers = [
            h for h in root_logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1

    def test_configure_logging_clears_existing_handlers(self):
        """Test that configure_logging clears existing handlers."""
        root_logger = logging.getLogger()

        # Add a dummy handler
        dummy_handler = logging.StreamHandler()
        root_logger.addHandler(dummy_handler)

        configure_logging()

        # Should not contain the dummy handler
        assert dummy_handler not in root_logger.handlers


class TestLoggingUtilities:
    """Test logging utility functions."""

    def test_log_operation_start(self, mock_logger):
        """Test log_operation_start function."""
        log_operation_start(
            mock_logger, "test operation", param1="value1", param2="value2"
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Starting test operation" in call_args
        assert "param1=value1" in call_args
        assert "param2=value2" in call_args

    def test_log_operation_start_no_kwargs(self, mock_logger):
        """Test log_operation_start without additional parameters."""
        log_operation_start(mock_logger, "simple operation")

        mock_logger.info.assert_called_once_with("Starting simple operation")

    def test_log_operation_complete(self, mock_logger):
        """Test log_operation_complete function."""
        log_operation_complete(
            mock_logger, "test operation", duration=1.234, result="success"
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Completed test operation" in call_args
        assert "(1.23s)" in call_args
        assert "result=success" in call_args

    def test_log_operation_complete_no_duration(self, mock_logger):
        """Test log_operation_complete without duration."""
        log_operation_complete(mock_logger, "test operation", result="success")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Completed test operation" in call_args
        assert "result=success" in call_args
        assert "(" not in call_args  # No duration in parentheses

    def test_log_progress(self, mock_logger):
        """Test log_progress function."""
        log_progress(mock_logger, 5, 10, "processing items", "item5.txt")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Progress: 5/10 (50.0%) processing items" in call_args
        assert "item5.txt" in call_args

    def test_log_progress_no_item(self, mock_logger):
        """Test log_progress without item description."""
        log_progress(mock_logger, 3, 7, "processing")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "Progress: 3/7 (42.9%) processing" in call_args

    def test_log_api_call_success(self, mock_logger):
        """Test log_api_call for successful API calls."""
        log_api_call(
            mock_logger,
            "POST",
            "/api/test",
            params={"key": "value"},
            response_status=200,
            duration=0.5,
        )

        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0][0]
        assert "API POST /api/test" in call_args
        assert "params={'key': 'value'}" in call_args
        assert "status=200" in call_args
        assert "duration=0.500s" in call_args

    def test_log_api_call_error(self, mock_logger):
        """Test log_api_call for failed API calls."""
        log_api_call(mock_logger, "GET", "/api/test", response_status=404, duration=0.2)

        # Should log as warning for 4xx/5xx status codes
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0][0]
        assert "API GET /api/test" in call_args
        assert "status=404" in call_args

    def test_log_api_call_filters_sensitive_params(self, mock_logger):
        """Test that log_api_call filters out sensitive parameters."""
        log_api_call(
            mock_logger,
            "POST",
            "/api/auth",
            params={
                "username": "user",
                "password": "secret",
                "token": "abc123",
                "data": "safe",
            },
            response_status=200,
        )

        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0][0]
        assert "username" in call_args
        assert "data" in call_args
        assert "password" not in call_args
        assert "token" not in call_args

    def test_log_dry_run_action(self, mock_logger):
        """Test log_dry_run_action function."""
        log_dry_run_action(
            mock_logger,
            "create page",
            "in database abc123",
            {"title": "Test Page", "properties": 3},
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "DRY RUN: Would create page in database abc123" in call_args
        assert "title=Test Page" in call_args
        assert "properties=3" in call_args

    def test_log_dry_run_action_no_details(self, mock_logger):
        """Test log_dry_run_action without additional details."""
        log_dry_run_action(mock_logger, "delete file", "test.txt")

        mock_logger.info.assert_called_once_with("DRY RUN: Would delete file test.txt")


class TestLoggingIntegration:
    """Integration tests for logging functionality."""

    def test_get_logger_returns_working_logger(self):
        """Test that get_logger returns a functional logger."""
        logger = get_logger("test.integration")

        # Should be a Logger instance
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.integration"

        # Should be able to call logging methods without error
        logger.info("Test message")
        logger.debug("Debug message")
        logger.warning("Warning message")
        logger.error("Error message")

    def test_configure_logging_sets_root_level(self):
        """Test that configure_logging sets the correct root logger level."""
        # Store original configuration
        root_logger = logging.getLogger()
        original_level = root_logger.level
        original_handlers = root_logger.handlers[:]

        try:
            # Test verbose mode
            configure_logging(verbose=True)
            assert root_logger.level == logging.DEBUG

            # Test quiet mode
            configure_logging(quiet=True)
            assert root_logger.level == logging.WARNING

            # Test default mode
            configure_logging()
            assert root_logger.level == logging.INFO

        finally:
            # Restore original configuration
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            for handler in original_handlers:
                root_logger.addHandler(handler)
            root_logger.setLevel(original_level)
