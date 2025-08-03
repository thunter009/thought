"""Logging utilities for the Thought CLI application."""

import logging
import sys
from typing import Any


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with consistent configuration.

    Args:
        name: Logger name, typically __name__ from the calling module

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Don't add handlers to individual loggers - let the root logger handle it
    # This ensures compatibility with pytest's caplog fixture
    root_logger = logging.getLogger()

    # Only set up handlers if we're not in a testing environment
    # (pytest's caplog sets up its own handlers on the root logger)
    has_pytest = hasattr(root_logger, "_pytest_caplog_handler")
    if not root_logger.handlers and not has_pytest:
        # Fallback configuration if root logger isn't set up
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

    return logger


def configure_logging(
    level: str = "INFO",
    verbose: bool = False,
    quiet: bool = False,
    log_file: str | None = None,
) -> None:
    """Configure application-wide logging.

    Args:
        level: Base logging level (DEBUG, INFO, WARNING, ERROR)
        verbose: Enable verbose logging (DEBUG level)
        quiet: Enable quiet mode (WARNING level only)
        log_file: Optional log file path
    """
    # Determine logging level
    if quiet:
        log_level = logging.WARNING
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatter
    if verbose:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S",
        )
    else:
        formatter = logging.Formatter("%(levelname)s: %(message)s")

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


def log_operation_start(logger: logging.Logger, operation: str, **kwargs: Any) -> None:
    """Log the start of an operation with context.

    Args:
        logger: Logger instance
        operation: Operation description
        **kwargs: Additional context to log
    """
    context = " | ".join([f"{k}={v}" for k, v in kwargs.items() if v is not None])
    message = f"Starting {operation}"
    if context:
        message += f" | {context}"
    logger.info(message)


def log_operation_complete(
    logger: logging.Logger, operation: str, duration: float | None = None, **kwargs: Any
) -> None:
    """Log the completion of an operation with context.

    Args:
        logger: Logger instance
        operation: Operation description
        duration: Operation duration in seconds
        **kwargs: Additional context to log
    """
    context = " | ".join([f"{k}={v}" for k, v in kwargs.items() if v is not None])
    message = f"Completed {operation}"
    if duration is not None:
        message += f" ({duration:.2f}s)"
    if context:
        message += f" | {context}"
    logger.info(message)


def log_progress(
    logger: logging.Logger,
    current: int,
    total: int,
    operation: str,
    item: str | None = None,
) -> None:
    """Log progress for batch operations.

    Args:
        logger: Logger instance
        current: Current item number (1-based)
        total: Total number of items
        operation: Operation description
        item: Optional item description
    """
    percentage = (current / total) * 100
    message = f"Progress: {current}/{total} ({percentage:.1f}%) {operation}"
    if item:
        message += f" | {item}"
    logger.info(message)


def log_api_call(
    logger: logging.Logger,
    method: str,
    endpoint: str,
    **kwargs: Any,
) -> None:
    """Log API call details.

    Args:
        logger: Logger instance
        method: HTTP method
        endpoint: API endpoint
        **kwargs: Additional parameters (params, response_status, duration)
    """
    message = f"API {method} {endpoint}"

    # Extract parameters from kwargs
    params = kwargs.get("params")
    response_status = kwargs.get("response_status")
    duration = kwargs.get("duration")

    details = []
    if params:
        # Don't log sensitive parameters (use exact matches, not substring)
        sensitive_keys = {
            "token",
            "password",
            "secret",
            "auth_token",
            "api_key",
            "access_token",
        }
        safe_params = {
            k: v for k, v in params.items() if k.lower() not in sensitive_keys
        }
        if safe_params:
            details.append(f"params={safe_params}")
        elif params:  # Had params but all were filtered
            details.append("params=[filtered]")

    if response_status is not None:
        details.append(f"status={response_status}")

    if duration is not None:
        details.append(f"duration={duration:.3f}s")

    if details:
        message += f" | {' | '.join(details)}"

    client_error_threshold = 400
    if response_status and response_status >= client_error_threshold:
        logger.warning(message)
    else:
        logger.debug(message)


def log_dry_run_action(
    logger: logging.Logger,
    action: str,
    target: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Log dry-run actions to show what would happen.

    Args:
        logger: Logger instance
        action: Action that would be taken
        target: Target of the action
        details: Additional action details
    """
    message = f"DRY RUN: Would {action} {target}"

    if details:
        detail_str = " | ".join([f"{k}={v}" for k, v in details.items()])
        message += f" | {detail_str}"

    logger.info(message)
