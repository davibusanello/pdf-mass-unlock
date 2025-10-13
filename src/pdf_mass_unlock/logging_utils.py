import logging


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Get a configured logger instance with the specified name.

    Args:
        name: Name for the logger (typically __name__)
        level: Logging level as string ('DEBUG', 'INFO', 'WARNING', 'ERROR')

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Prevent adding multiple handlers if logger already exists
    if logger.handlers:
        logger.setLevel(getattr(logging, level.upper()))
        logger.propagate = False  # Prevent duplicate logs if root logger is configured
        return logger

    # Set the logging level
    logger.setLevel(getattr(logging, level.upper()))

    # Create console handler with a higher log level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)

    # Add handler to the logger
    logger.addHandler(console_handler)

    # Prevent propagation to avoid duplicate logs when root logger is configured
    logger.propagate = False

    return logger


def mask(value: str) -> str:
    """
    Mask a potentially sensitive value for safe logging.

    Args:
        value: String value to mask

    Returns:
        Masked string with same length hint (e.g., "secret" -> "***")
    """
    if not value:
        return ""

    # Replace with asterisks but preserve length as hint
    return "*" * len(value)
