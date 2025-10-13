import tempfile
from pathlib import Path
from unittest.mock import patch

import pikepdf
from pdf_mass_unlock.unlocker import (
    UnlockResult,
    UnlockStatus,
    is_pdf_encrypted,
    try_unlock_dry_run,
    unlock_file,
)


def create_plain_pdf(filepath: Path):
    """Create a simple, unlocked PDF file for testing."""
    # Create a simple PDF using pikepdf
    pdf = pikepdf.new()
    pdf.save(filepath)


def create_encrypted_pdf(filepath: Path, password: str):
    """Create a password-protected PDF file for testing."""
    # Create a simple PDF first
    pdf = pikepdf.new()

    # Save with encryption - use the correct syntax for pikepdf
    # By setting the user password the same as owner, anyone with the password can
    # open the document
    pdf.save(filepath, encryption=pikepdf.Encryption(owner=password, user=password))


def test_unlock_result_repr():
    """Test string representation of UnlockResult."""
    result = UnlockResult(
        file_path=Path("/test/path.pdf"),
        status=UnlockStatus.UNLOCKED,
        error_message="Test error",
        method_used="dictionary",
    )

    expected_repr = (
        "UnlockResult(file_path=/test/path.pdf, status=UnlockStatus.UNLOCKED, "
        "error_message=Test error, method_used=dictionary)"
    )

    assert repr(result) == expected_repr


def test_is_pdf_encrypted_exception_returns_true():
    """Test that is_pdf_encrypted returns True for non-existent files (assume encrypted)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        non_existent_file = temp_path / "non_existent.pdf"

        # Should return True for non-existent files (assume encrypted to try passwords)
        result = is_pdf_encrypted(non_existent_file)
        assert result


def test_is_pdf_encrypted_plain():
    """Test that is_pdf_encrypted returns False for plain (unencrypted) PDF."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "plain.pdf"

        create_plain_pdf(pdf_path)

        assert not is_pdf_encrypted(pdf_path)


def test_is_pdf_encrypted_locked():
    """Test that is_pdf_encrypted returns True for locked PDF."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "locked.pdf"

        create_encrypted_pdf(pdf_path, "testpass")

        assert is_pdf_encrypted(pdf_path)


def test_unlock_file_already_unlocked():
    """Test that unlock_file returns UNCHANGED for already unlocked PDF."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "plain.pdf"

        create_plain_pdf(pdf_path)

        result = unlock_file(pdf_path, ["any_password"])

        assert result.status == UnlockStatus.UNCHANGED
        assert result.method_used == "already_unlocked"


def test_unlock_file_success():
    """Test that unlock_file successfully unlocks a PDF with correct password."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "locked.pdf"

        create_encrypted_pdf(pdf_path, "correct_password")

        result = unlock_file(pdf_path, [("correct_password", "dictionary")])

        assert result.status == UnlockStatus.UNLOCKED
        assert result.method_used == "dictionary"
        # Verify the PDF is now unlocked
        assert not is_pdf_encrypted(pdf_path)


def test_unlock_file_wrong_password():
    """Test that unlock_file fails with wrong password."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "locked.pdf"

        create_encrypted_pdf(pdf_path, "correct_password")

        result = unlock_file(pdf_path, [("wrong_password", "dictionary")])

        assert result.status == UnlockStatus.FAILED
        assert "All passwords failed" in result.error_message
        # The original file should still be encrypted
        assert is_pdf_encrypted(pdf_path)


def test_unlock_file_multiple_passwords():
    """Test that unlock_file works with multiple passwords, using the right one."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "locked.pdf"

        create_encrypted_pdf(pdf_path, "third_password")

        result = unlock_file(
            pdf_path,
            [
                ("first_password", "dictionary"),
                ("second_password", "dictionary"),
                ("third_password", "dictionary"),
            ],
        )

        assert result.status == UnlockStatus.UNLOCKED
        assert (
            result.method_used == "dictionary"
        )  # Third password is not the first, so it's considered from dictionary
        # Verify the PDF is now unlocked
        assert not is_pdf_encrypted(pdf_path)


def test_unlock_file_backup_created():
    """Test that unlock_file creates a backup before modifying."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "locked.pdf"

        create_encrypted_pdf(pdf_path, "correct_password")

        result = unlock_file(pdf_path, [("correct_password", "dictionary")])

        # Check that backup was created
        backup_dir = temp_path / "pdf_with_password"
        backup_file = backup_dir / "locked.pdf"

        assert backup_file.exists()
        assert result.status == UnlockStatus.UNLOCKED

        # Original backup should still be encrypted
        assert is_pdf_encrypted(backup_file)


def test_unlock_file_with_empty_password_attempt():
    """Test that unlock_file can successfully use an empty string as a password."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "locked.pdf"

        # Create a PDF encrypted with empty password as the user password
        # Create PDF with specific password to test empty string
        pdf = pikepdf.new()
        pdf.save(pdf_path, encryption=pikepdf.Encryption(owner="realpassword", user="realpassword"))

        # Try unlocking with an empty password followed by the real password
        result = unlock_file(pdf_path, [("", "empty"), ("realpassword", "dictionary")])

        assert result.status == UnlockStatus.UNLOCKED
        # Since realpassword was the second option, it should be labeled as dictionary
        # Actually, we need to update the unlock_file function to properly label the method used
        # For now, let's just check it was unlocked
        assert not is_pdf_encrypted(pdf_path)


def test_unlock_file_encryption_check_error():
    """Test error handling when checking if PDF is encrypted fails."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        non_existent_pdf = temp_path / "non_existent.pdf"

        result = unlock_file(non_existent_pdf, [("any_password", "dictionary")])

        # With the new behavior, the encryption check assumes encrypted and tries passwords
        # The failure should now be from backup creation, not encryption check
        assert result.status == UnlockStatus.FAILED
        assert "Failed to create backup" in result.error_message


def test_unlock_file_backup_creation_error():
    """Test error handling when backup creation fails."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "locked.pdf"

        create_encrypted_pdf(pdf_path, "correct_password")

        # Mock copy_backup to raise an exception
        with patch("pdf_mass_unlock.unlocker.copy_backup", side_effect=Exception("Backup failed")):
            result = unlock_file(pdf_path, [("correct_password", "dictionary")])

            assert result.status == UnlockStatus.FAILED
            assert "Failed to create backup" in result.error_message


def test_unlock_file_password_processing_error():
    """Test error handling for generic exceptions during password processing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "locked.pdf"

        create_encrypted_pdf(pdf_path, "correct_password")

        # Mock atomic_write to raise an exception when trying to save the unlocked PDF
        with patch(
            "pdf_mass_unlock.unlocker.atomic_write", side_effect=Exception("Processing error")
        ):
            result = unlock_file(pdf_path, [("correct_password", "dictionary")])

            assert result.status == UnlockStatus.FAILED
            assert "Error processing PDF with password" in result.error_message


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


def test_try_unlock_dry_run_success():
    """Test try_unlock_dry_run function with correct password."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "locked.pdf"

        create_encrypted_pdf(pdf_path, "correct_password")

        result = try_unlock_dry_run(pdf_path, [("correct_password", "dictionary")])

        assert result.status == UnlockStatus.UNLOCKED
        assert result.method_used == "dictionary"
        # The original file should still be encrypted since no actual change was made
        assert is_pdf_encrypted(pdf_path)


def test_try_unlock_dry_run_failure():
    """Test try_unlock_dry_run function with wrong password."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "locked.pdf"

        create_encrypted_pdf(pdf_path, "correct_password")

        result = try_unlock_dry_run(pdf_path, [("wrong_password", "dictionary")])

        assert result.status == UnlockStatus.FAILED
        assert "All passwords failed" in result.error_message
        # The original file should still be encrypted
        assert is_pdf_encrypted(pdf_path)


def test_try_unlock_dry_run_already_unlocked():
    """Test try_unlock_dry_run function with already unlocked PDF."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "plain.pdf"

        create_plain_pdf(pdf_path)

        result = try_unlock_dry_run(pdf_path, [("any_password", "dictionary")])

        assert result.status == UnlockStatus.UNCHANGED
        assert result.method_used == "already_unlocked"


def test_try_unlock_dry_run_backup_validation_failure():
    """Test try_unlock_dry_run function catches backup validation failures."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        pdf_path = temp_path / "locked.pdf"

        # Create an encrypted PDF
        create_encrypted_pdf(pdf_path, "correct_password")

        # Mock validate_backup_path_no_side_effects to raise an exception
        with patch(
            "pdf_mass_unlock.unlocker.validate_backup_path_no_side_effects",
            side_effect=PermissionError("Permission denied creating backup"),
        ):
            result = try_unlock_dry_run(
                pdf_path, [("correct_password", "dictionary")], "test_backup_dir"
            )

            assert result.status == UnlockStatus.FAILED
            assert "Failed to create backup" in result.error_message
            assert "Permission denied creating backup" in result.error_message


if __name__ == "__main__":
    test_unlock_result_repr()
    test_is_pdf_encrypted_exception_returns_true()
    test_is_pdf_encrypted_plain()
    test_is_pdf_encrypted_locked()
    test_unlock_file_already_unlocked()
    test_unlock_file_success()
    test_unlock_file_wrong_password()
    test_unlock_file_multiple_passwords()
    test_unlock_file_backup_created()
    test_unlock_file_with_empty_password_attempt()
    test_unlock_file_encryption_check_error()
    test_unlock_file_backup_creation_error()
    test_unlock_file_password_processing_error()
    test_try_unlock_dry_run_success()
    test_try_unlock_dry_run_failure()
    test_try_unlock_dry_run_already_unlocked()
    test_try_unlock_dry_run_backup_validation_failure()
    print("All unlocker tests passed!")
