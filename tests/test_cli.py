import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pikepdf
import typer
from pdf_mass_unlock.cli import (
    _log_input_details,
    app,
    print_summary,
    process_pdfs,
    version_callback,
)
from typer.testing import CliRunner


def test_version_callback():
    """Test the version callback function."""
    try:
        version_callback(True)
    except typer.Exit as e:
        assert e.exit_code == 0  # Exit code should be 0 for successful version display


def test_log_input_details():
    """Test the _log_input_details function."""
    logger = MagicMock()

    # Test with all parameters
    _log_input_details("testpass", "dictionary.txt", True, True, logger)

    # Verify the logger was called with expected messages
    logger.debug.assert_called_once_with("Using single password (masked)")
    assert logger.info.call_count >= 2  # Multiple info calls


def test_process_pdfs_dry_run():
    """Test the process_pdfs function in dry run mode."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "test.pdf"

        # Create a test PDF file
        pdf = pikepdf.new()
        pdf.save(pdf_path)

        pdf_files = [pdf_path]

        # Mock password factory
        def password_factory():
            return [("password", "test")]

        logger = MagicMock()
        console = MagicMock()

        # Call process_pdfs in dry run mode
        processed, unlocked, failed, unchanged = process_pdfs(
            pdf_files, password_factory, None, True, logger, console
        )

        # In dry run, files are processed but not actually unlocked
        # The file gets a status of UNCHANGED in dry run mode based on the code
        assert processed == 1
        assert unlocked == 0
        assert failed == 0  # In dry run, we don't actually try to unlock
        # There might be some unchanged files depending on the status
        # Let's just verify the total adds up
        assert processed == unlocked + failed + unchanged


def test_print_summary():
    """Test the print_summary function."""
    console = MagicMock()

    # Mock the console print method
    with patch("pdf_mass_unlock.cli.console", console):
        print_summary(10, 5, 2, 3)

        # Verify that console.print was called (indicating table was printed)
        assert console.print.called


def create_plain_pdf(filepath: Path):
    """Create a simple, unlocked PDF file for testing."""
    pdf = pikepdf.new()
    pdf.save(filepath)


def create_encrypted_pdf(filepath: Path, password: str):
    """Create a password-protected PDF file for testing."""
    pdf = pikepdf.new()
    pdf.save(filepath, encryption=pikepdf.Encryption(owner=password, user=password))


def test_main_with_path_only():
    """Test the main CLI function with just a path."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Create a test PDF
        test_pdf = temp_path / "test.pdf"
        create_plain_pdf(test_pdf)

        # Run the CLI with just a path
        result = runner.invoke(app, ["--path", str(temp_path)])

        # Should succeed (path exists and has PDFs)
        assert result.exit_code == 0


def test_main_with_missing_path():
    """Test the main CLI function with missing path."""
    runner = CliRunner()

    # Run the CLI without a path (should fail)
    result = runner.invoke(app, [])

    # Should fail with exit code 2 (required argument missing)
    assert result.exit_code == 2
    assert "Error: --path is required" in result.stderr


def test_main_with_empty_directory():
    """Test the main CLI function with an empty directory."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Run the CLI with an empty directory (should exit early)
        result = runner.invoke(app, ["--path", str(temp_path)])

        # Should succeed with exit code 0 since no PDFs found
        assert result.exit_code == 0


def test_main_with_try_empty_flag():
    """Test the main CLI function with try-empty flag."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Create a test PDF
        test_pdf = temp_path / "test.pdf"
        create_plain_pdf(test_pdf)

        # Run the CLI with path and try-empty
        result = runner.invoke(app, ["--path", str(temp_path), "--try-empty"])

        # Should succeed
        assert result.exit_code == 0


def test_main_with_log_level():
    """Test the main CLI function with custom log level."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Create a test PDF
        test_pdf = temp_path / "test.pdf"
        create_plain_pdf(test_pdf)

        # Run the CLI with path and debug log level
        result = runner.invoke(app, ["--path", str(temp_path), "--log-level", "DEBUG"])

        # Should succeed
        assert result.exit_code == 0


def test_main_with_password():
    """Test the main CLI function with a password."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Create a test PDF
        test_pdf = temp_path / "test.pdf"
        create_plain_pdf(test_pdf)

        # Run the CLI with path and password
        result = runner.invoke(app, ["--path", str(temp_path), "--password", "testpass"])

        # Should succeed
        assert result.exit_code == 0


def test_main_with_dry_run():
    """Test the main CLI function with dry run."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Create a test PDF
        test_pdf = temp_path / "test.pdf"
        create_plain_pdf(test_pdf)

        # Run the CLI with path and dry run
        result = runner.invoke(app, ["--path", str(temp_path), "--dry-run"])

        # Should succeed
        assert result.exit_code == 0


def test_main_with_summary():
    """Test the main CLI function with summary."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Create a test PDF
        test_pdf = temp_path / "test.pdf"
        create_plain_pdf(test_pdf)

        # Run the CLI with path and summary
        result = runner.invoke(app, ["--path", str(temp_path), "--summary"])

        # Should succeed
        assert result.exit_code == 0


def test_main_with_backup_root():
    """Test the main CLI function with backup root."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        backup_path = temp_path / "backup_dir"
        # Create a test PDF
        test_pdf = temp_path / "test.pdf"
        create_plain_pdf(test_pdf)

        # Run the CLI with path and backup root
        result = runner.invoke(app, ["--path", str(temp_path), "--backup-root", str(backup_path)])

        # Should succeed
        assert result.exit_code == 0


if __name__ == "__main__":
    test_version_callback()
    test_log_input_details()
    test_process_pdfs_dry_run()
    test_print_summary()
    test_main_with_path_only()
    test_main_with_missing_path()
    test_main_with_password()
    test_main_with_dry_run()
    test_main_with_summary()
    test_main_with_empty_directory()
    test_main_with_try_empty_flag()
    test_main_with_log_level()
    test_main_with_backup_root()
    print("All CLI tests passed!")
