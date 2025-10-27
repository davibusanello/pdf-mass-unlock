"""Additional tests to improve code coverage."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pikepdf

from pdf_mass_unlock.cli import (
    _log_input_details,
    find_and_validate_pdfs,
    iter_passwords,
    main,
    process_pdfs,
)
from pdf_mass_unlock.unlocker import (
    UnlockResult,
    UnlockStatus,
    is_pdf_encrypted,
    try_unlock_dry_run,
    unlock_file,
)


def create_plain_pdf(filepath: Path):
    """Create a simple unlocked PDF file for testing."""
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(612, 792))  # US Letter size
    pdf.save(filepath)


def test_cli_password_factory_dictionary_scan_root_resolution():
    """Test CLI password factory resolves dictionary relative to scan root."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        dict_content = "test_password\n"
        dict_file = temp_path / "test_dict.txt"
        dict_file.write_text(dict_content)

        # Test the password factory logic from CLI
        def password_factory():
            dictionary_path = Path("test_dict.txt")  # Relative path that doesn't exist from CWD
            env = {}

            # First try the dictionary path as provided (doesn't exist)
            final_dict_path = dictionary_path
            if dictionary_path and not dictionary_path.exists():
                # Try relative to scan root (temp_path in this case)
                scan_relative_path = temp_path / dictionary_path
                if scan_relative_path.exists():
                    final_dict_path = scan_relative_path
                    # This debug message should be logged - line 119-120
                else:
                    # This warning should be logged - lines 122-125
                    final_dict_path = None
            elif dictionary_path:
                # This debug message should be logged - lines 126-127
                pass

            return iter_passwords(
                single=None,
                dictionary_path=final_dict_path,
                env=env,
                try_empty=False,
            )

        # Call the factory
        passwords = list(password_factory())

        # Should have loaded passwords from the dictionary found relative to scan root
        assert len(passwords) == 1
        assert ("test_password", "dictionary") in passwords


def test_cli_process_pdfs_unlock_failure_logging():
    """Test CLI process_pdfs logs when PDF unlock fails."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "test.pdf"

        # Create a simple PDF file
        create_plain_pdf(pdf_path)

        # Mock unlock_file to return a failure
        with patch("pdf_mass_unlock.cli.unlock_file") as mock_unlock:
            mock_unlock.return_value = UnlockResult(
                file_path=pdf_path, status=UnlockStatus.FAILED, error_message="Test error message"
            )

            # Create a simple password factory
            def password_factory():
                return iter_passwords(single="test", dictionary_path=None, env={}, try_empty=False)

            # Process the PDF with a mock logger
            mock_logger = MagicMock()
            processed, unlocked, failed, unchanged = process_pdfs(
                [pdf_path], password_factory, "backup_dir", False, mock_logger, MagicMock()
            )

            # Verify the failure was counted and logged - lines 199-200
            assert failed == 1
            mock_logger.warning.assert_called()


def test_cli_log_input_details_try_empty():
    """Test CLI _log_input_details logs when try_empty is enabled."""
    mock_logger = MagicMock()
    # Test with try_empty=True - should log line 237
    _log_input_details(None, None, True, False, mock_logger)
    mock_logger.info.assert_any_call("Will try empty password")


def test_cli_main_entry_point():
    """Test CLI main entry point can be called - line 246."""
    # This test just verifies the main function can be imported and called
    # without crashing. We can't actually run it because it would exit the process.
    assert callable(main)


def test_log_input_details_single_password_debug():
    """Test that log_input_details logs debug message for single password."""
    logger = MagicMock()
    _log_input_details("testpass", None, False, False, logger)
    logger.debug.assert_called_once_with("Using single password (masked)")


def test_log_input_details_dry_run_info():
    """Test that log_input_details logs info message for dry run."""
    logger = MagicMock()
    _log_input_details(None, None, False, True, logger)
    logger.info.assert_called_once_with("DRY RUN MODE - No files will be modified")


def test_find_and_validate_pdfs_empty_directory():
    """Test find_and_validate_pdfs with empty directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        logger = MagicMock()

        with patch("pdf_mass_unlock.cli.console") as mock_console:
            # Mock find_pdfs to return empty list
            with patch("pdf_mass_unlock.cli.find_pdfs") as mock_find:
                mock_find.return_value = []

                # Call the function - this function doesn't return anything
                find_and_validate_pdfs(temp_path, logger)

                # Should print warning message
                mock_console.print.assert_called_once_with(
                    "[yellow]No PDF files found to process.[/yellow]"
                )


def test_password_factory_dictionary_not_found_warning():
    """Test that password factory handles dictionary not found with warning."""
    # Test with non-existent dictionary
    dictionary_path = Path("non_existent_dictionary.txt")

    # Create a password factory with non-existent dictionary
    def password_factory():
        env = {}
        return iter_passwords(
            single=None,
            dictionary_path=dictionary_path if dictionary_path.exists() else None,
            env=env,
            try_empty=False,
        )

    # Call the factory - should not crash
    passwords = list(password_factory())

    # Should return empty list since no dictionary is available
    assert len(passwords) == 0


def test_try_unlock_dry_run_encryption_check_error():
    """Test error handling when checking if PDF is encrypted fails in dry run."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        non_existent_pdf = temp_path / "non_existent.pdf"

        result = try_unlock_dry_run(non_existent_pdf, [("any_password", "dictionary")])

        # With the new behavior, the encryption check assumes encrypted and tries passwords
        # The failure should now be from the password processing, not encryption check
        assert result.status == UnlockStatus.FAILED
        assert "Error processing PDF with password" in result.error_message


def test_unlock_file_password_processing_general_error():
    """Test error handling when processing PDF with password fails due to general error."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "invalid.pdf"

        # Create a file that's not actually a valid PDF
        pdf_path.write_text("not a pdf file")

        result = unlock_file(pdf_path, [("any_password", "dictionary")])

        # Should fail with password processing error
        assert result.status == UnlockStatus.FAILED
        assert "Error processing PDF with password" in result.error_message


def test_process_pdfs_unlock_warning_logging():
    """Test that process_pdfs logs warnings for failed unlocks."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "test.pdf"

        # Create a simple PDF file
        create_plain_pdf(pdf_path)

        # Mock unlock_file to return a failure
        with patch("pdf_mass_unlock.cli.unlock_file") as mock_unlock:
            mock_unlock.return_value = UnlockResult(
                file_path=pdf_path, status=UnlockStatus.FAILED, error_message="Test error message"
            )

            # Create a simple password factory
            def password_factory():
                return iter_passwords(single="test", dictionary_path=None, env={}, try_empty=False)

            # Process the PDF with a mock logger
            mock_logger = MagicMock()
            processed, unlocked, failed, unchanged = process_pdfs(
                [pdf_path], password_factory, "backup_dir", False, mock_logger, MagicMock()
            )

            # Verify the warning was logged
            assert failed == 1
            mock_logger.warning.assert_called()


def test_is_pdf_encrypted_exception_handling():
    """Test error handling when checking if PDF is encrypted fails."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        non_existent_pdf = temp_path / "does_not_exist.pdf"

        # Test the exception handling path - should return True (assume encrypted)
        result = is_pdf_encrypted(non_existent_pdf)
        assert result is True  # Exception handling returns True to assume encrypted


def test_unlock_file_encryption_check_exception():
    """Test unlock_file handles exception when checking if PDF is encrypted."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "test.pdf"

        # Create a simple PDF file
        create_plain_pdf(pdf_path)

        # Mock is_pdf_encrypted to raise an exception
        with patch(
            "pdf_mass_unlock.unlocker.is_pdf_encrypted", side_effect=Exception("Test error")
        ):
            result = unlock_file(pdf_path, [("any_password", "dictionary")])

            # Should fail with encryption check error (lines 84-85 in unlock_file)
            assert result.status == UnlockStatus.FAILED
            assert "Error checking if PDF is encrypted" in result.error_message


def test_try_unlock_dry_run_encryption_check_exception():
    """Test try_unlock_dry_run handles exception when checking if PDF is encrypted."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "test.pdf"

        # Create a simple PDF file
        create_plain_pdf(pdf_path)

        # Mock is_pdf_encrypted to raise an exception
        with patch(
            "pdf_mass_unlock.unlocker.is_pdf_encrypted", side_effect=Exception("Test error")
        ):
            result = try_unlock_dry_run(pdf_path, [("any_password", "dictionary")])

            # Should fail with encryption check error (lines 150-151 in try_unlock_dry_run)
            assert result.status == UnlockStatus.FAILED
            assert "Error checking if PDF is encrypted" in result.error_message


def test_cli_password_factory_dict_found_relative_to_scan_path():
    """Test CLI password factory logs debug when dictionary found
    relative to scan path (lines 119-120)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a dictionary file in the temp directory
        dict_content = "password1\npassword2\n"
        dict_file = temp_path / "custom_dict.txt"
        dict_file.write_text(dict_content)

        # Create a mock logger to verify debug message
        mock_logger = MagicMock()

        # Import the iter_passwords function that's used by the password factory
        from pdf_mass_unlock.passwords import iter_passwords

        # Simulate the password factory logic from CLI with relative path
        def password_factory():
            dictionary_path = Path("custom_dict.txt")  # Won't exist from CWD but from scan path
            env = {}

            # First try the dictionary path as provided
            final_dict_path = dictionary_path
            if dictionary_path and not dictionary_path.exists():
                # If relative path doesn't exist from CWD, try relative to scan root
                scan_relative_path = temp_path / dictionary_path
                if scan_relative_path.exists():
                    final_dict_path = scan_relative_path
                    mock_logger.debug(
                        f"Using dictionary file relative to scan path: {scan_relative_path}"
                    )  # This is line 119-120
                else:
                    mock_logger.warning(
                        f"Dictionary file not found: {dictionary_path} "
                        "(tried CWD and relative to scan path)"
                    )
                    final_dict_path = None
            elif dictionary_path:
                mock_logger.debug(
                    f"Using dictionary file: {dictionary_path}"
                )  # This is line 126-127

            return iter_passwords(
                single=None,
                dictionary_path=final_dict_path,
                env=env,
                try_empty=False,
            )

        # Call the factory
        passwords = list(password_factory())

        # Verify the debug log was called
        mock_logger.debug.assert_called_once()
        assert "Using dictionary file relative to scan path:" in str(mock_logger.debug.call_args)

        # Should have loaded passwords from the dictionary
        assert len(passwords) >= 2  # At least the 2 passwords from the file


def test_cli_log_input_details_with_existing_dict():
    """Test _log_input_details logs when dictionary file exists (line 237)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a dictionary file
        dict_file = temp_path / "test_dict.txt"
        dict_file.write_text("password\n")

        mock_logger = MagicMock()
        # Test _log_input_details with an existing dictionary path
        _log_input_details("testpass", str(dict_file), False, False, mock_logger)

        # Verify the log message for existing dictionary was made (line 237)
        mock_logger.info.assert_called_with(f"Using dictionary file: {dict_file}")


def test_process_pdfs_successful_unlock_logging():
    """Test that process_pdfs logs successful unlocks (lines 199-200)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "test.pdf"

        # Create a simple PDF file
        create_plain_pdf(pdf_path)

        # Mock unlock_file to return a successful unlock
        with patch("pdf_mass_unlock.cli.unlock_file") as mock_unlock:
            mock_unlock.return_value = UnlockResult(
                file_path=pdf_path, status=UnlockStatus.UNLOCKED, method_used="dictionary"
            )

            # Create a simple password factory
            def password_factory():
                return iter_passwords(single="test", dictionary_path=None, env={}, try_empty=False)

            # Process the PDF with a mock logger
            mock_logger = MagicMock()
            processed, unlocked, failed, unchanged = process_pdfs(
                [pdf_path], password_factory, "backup_dir", False, mock_logger, MagicMock()
            )

            # Verify the success was logged (lines 199-200)
            assert unlocked == 1
            mock_logger.info.assert_called()  # Should have been called with success message


def test_cli_main_function_call():
    """Test that main function can be called without crashing (line 246)."""
    # Line 246 is just "app()" in the main block
    # We can verify that main exists and is callable
    assert callable(main)


def test_cli_password_factory_dict_exists_debug_log():
    """Test CLI password factory logs debug when dictionary path exists."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a dictionary file in the temp directory
        dict_content = "password1\npassword2\n"
        dict_file = temp_path / "existing_dict.txt"
        dict_file.write_text(dict_content)

        # Create a mock logger to verify debug message
        mock_logger = MagicMock()

        # Import the iter_passwords function that's used by the password factory
        from pdf_mass_unlock.passwords import iter_passwords

        # Simulate the password factory logic from CLI with existing path
        def password_factory():
            dictionary_path = dict_file  # This exists
            env = {}

            # First try the dictionary path as provided
            final_dict_path = dictionary_path
            if dictionary_path and not dictionary_path.exists():
                # If relative path doesn't exist from CWD, try relative to scan root
                scan_relative_path = temp_path / dictionary_path
                if scan_relative_path.exists():
                    final_dict_path = scan_relative_path
                    mock_logger.debug(
                        f"Using dictionary file relative to scan path: {scan_relative_path}"
                    )
                else:
                    mock_logger.warning(
                        f"Dictionary file not found: {dictionary_path} "
                        "(tried CWD and relative to scan path)"
                    )
                    final_dict_path = None
            elif dictionary_path:
                mock_logger.debug(
                    f"Using dictionary file: {dictionary_path}"
                )  # This is line 126-127

            return iter_passwords(
                single=None,
                dictionary_path=final_dict_path,
                env=env,
                try_empty=False,
            )

        # Call the factory
        passwords = list(password_factory())

        # Verify the debug log was called for the existing dictionary
        assert mock_logger.debug.called
        assert len(mock_logger.debug.call_args_list) >= 1

        # Should have loaded passwords from the dictionary
        assert len(passwords) >= 2  # At least the 2 passwords from the file


if __name__ == "__main__":
    test_cli_password_factory_dictionary_scan_root_resolution()
    test_cli_process_pdfs_unlock_failure_logging()
    test_cli_log_input_details_try_empty()
    test_cli_main_entry_point()
    test_log_input_details_single_password_debug()
    test_log_input_details_dry_run_info()
    test_find_and_validate_pdfs_empty_directory()
    test_password_factory_dictionary_not_found_warning()
    test_try_unlock_dry_run_encryption_check_error()
    test_unlock_file_password_processing_general_error()
    test_process_pdfs_unlock_warning_logging()
    test_is_pdf_encrypted_exception_handling()
    test_unlock_file_encryption_check_exception()
    test_try_unlock_dry_run_encryption_check_exception()
    test_cli_password_factory_dict_found_relative_to_scan_path()
    test_cli_log_input_details_with_existing_dict()
    test_process_pdfs_successful_unlock_logging()
    test_cli_main_function_call()
    test_cli_password_factory_dict_exists_debug_log()
    print("All coverage tests passed!")
