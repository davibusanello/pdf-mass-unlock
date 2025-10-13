import logging

from pdf_mass_unlock.logging_utils import get_logger, mask


def test_get_logger():
    """Test that get_logger returns a properly configured logger."""
    logger = get_logger("test_logger")

    assert logger is not None
    assert logger.name == "test_logger"
    assert logger.level == logging.INFO  # Default level


def test_get_logger_with_level():
    """Test that get_logger respects custom logging level."""
    logger = get_logger("test_logger", "DEBUG")

    assert logger.level == logging.DEBUG


def test_mask_empty_string():
    """Test that masking an empty string returns an empty string."""
    result = mask("")
    assert result == ""


def test_mask_secret():
    """Test that masking replaces content with asterisks."""
    secret = "my_password"
    masked = mask(secret)

    assert len(masked) == len(secret)
    assert all(c == "*" for c in masked)


def test_mask_preserves_length():
    """Test that masked string has same length as original."""
    original = "very_long_password_with_special_chars"
    masked = mask(original)

    assert len(masked) == len(original)


if __name__ == "__main__":
    test_get_logger()
    test_get_logger_with_level()
    test_mask_empty_string()
    test_mask_secret()
    test_mask_preserves_length()
    print("All logging tests passed!")
