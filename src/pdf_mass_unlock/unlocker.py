from enum import Enum
from pathlib import Path
from typing import Iterable, Optional

import pikepdf

from .io_utils import (
    atomic_write,
    copy_backup,
    validate_backup_path,
    validate_backup_path_no_side_effects,
)


class UnlockStatus(Enum):
    """Status of the unlock operation."""

    UNCHANGED = "unchanged"  # File was already unlocked
    UNLOCKED = "unlocked"  # File was locked but successfully unlocked
    FAILED = "failed"  # File was locked but unlock failed


class UnlockResult:
    """Result of an unlock operation."""

    def __init__(
        self,
        file_path: Path,
        status: UnlockStatus,
        error_message: Optional[str] = None,
        method_used: Optional[str] = None,
    ):
        self.file_path = file_path
        self.status = status
        self.error_message = error_message
        self.method_used = method_used  # How the password was obtained (single, dictionary, etc.)

    def __repr__(self):
        return (
            f"UnlockResult(file_path={self.file_path}, status={self.status}, "
            f"error_message={self.error_message}, method_used={self.method_used})"
        )


def is_pdf_encrypted(filepath: Path) -> bool:
    """
    Check if a PDF file is encrypted (password-protected).

    Args:
        filepath: Path to the PDF file

    Returns:
        True if the PDF is encrypted, False otherwise
    """
    try:
        # Try to open the PDF without a password
        with pikepdf.open(filepath):
            # If we can open it without a password, it's not encrypted
            return False
    except pikepdf.PasswordError:
        # If we get a password error, the PDF is encrypted
        return True
    except Exception:
        # If we get any other error (parsing/IO issues), assume it's encrypted
        # and allow unlock attempts with passwords instead of failing completely
        return True


def unlock_file(
    filepath: Path, passwords: Iterable[tuple[str, str]], backup_dir_name: str = "pdf_with_password"
) -> UnlockResult:
    """
    Attempt to unlock a PDF file using the provided passwords.

    Args:
        filepath: Path to the PDF file to unlock
        passwords: Iterable of (password, source) tuples to try
        backup_dir_name: Name for the backup directory

    Returns:
        UnlockResult indicating the outcome
    """
    # Check if the file is already unlocked
    try:
        if not is_pdf_encrypted(filepath):
            return UnlockResult(
                file_path=filepath, status=UnlockStatus.UNCHANGED, method_used="already_unlocked"
            )
    except Exception as e:
        return UnlockResult(
            file_path=filepath,
            status=UnlockStatus.FAILED,
            error_message=f"Error checking if PDF is encrypted: {str(e)}",
        )

    # Validate backup can be created before attempting to modify the file
    try:
        validate_backup_path(
            filepath, backup_dir_name
        )  # Original function with side effects for real operations
        # Actually create the backup
        copy_backup(filepath, backup_dir_name)
    except Exception as e:
        return UnlockResult(
            file_path=filepath,
            status=UnlockStatus.FAILED,
            error_message=f"Failed to create backup: {str(e)}",
        )

    # Try each password
    for password, source in passwords:
        try:
            # Try to open the PDF with the current password
            with pikepdf.open(filepath, password=password) as pdf_file:
                # If successful, save the unlocked PDF atomically
                with atomic_write(filepath) as f:
                    pdf_file.save(f)

                return UnlockResult(
                    file_path=filepath,
                    status=UnlockStatus.UNLOCKED,
                    method_used=source,  # Use the source provided by the password iterator
                    error_message=None,
                )
        except pikepdf.PasswordError:
            # This password didn't work, continue to the next one
            continue
        except Exception as e:
            # Some other error occurred
            return UnlockResult(
                file_path=filepath,
                status=UnlockStatus.FAILED,
                error_message=f"Error processing PDF with password: {str(e)}",
            )

    # If we get here, no password worked
    return UnlockResult(
        file_path=filepath, status=UnlockStatus.FAILED, error_message="All passwords failed"
    )


def try_unlock_dry_run(
    filepath: Path, passwords: Iterable[tuple[str, str]], backup_dir_name: str = "pdf_with_password"
) -> UnlockResult:
    """
    Dry-run version of unlock_file that tests what would happen without modifying files.

    Args:
        filepath: Path to the PDF file to check
        passwords: Iterable of (password, source) tuples to try
        backup_dir_name: Name for the backup directory

    Returns:
        UnlockResult indicating what would happen in a real unlock attempt
    """
    # Check if the file is already unlocked
    try:
        if not is_pdf_encrypted(filepath):
            return UnlockResult(
                file_path=filepath, status=UnlockStatus.UNCHANGED, method_used="already_unlocked"
            )
    except Exception as e:
        return UnlockResult(
            file_path=filepath,
            status=UnlockStatus.FAILED,
            error_message=f"Error checking if PDF is encrypted: {str(e)}",
        )

    # Validate that backup can be created without actually creating any files/directories
    try:
        validate_backup_path_no_side_effects(filepath, backup_dir_name)
    except Exception as e:
        return UnlockResult(
            file_path=filepath,
            status=UnlockStatus.FAILED,
            error_message=f"Failed to create backup: {str(e)}",
        )

    # Try each password (without actually modifying the file)
    for password, source in passwords:
        try:
            # Try to open the PDF with the current password
            with pikepdf.open(filepath, password=password):
                # If successful, this is what would happen in a real unlock
                return UnlockResult(
                    file_path=filepath,
                    status=UnlockStatus.UNLOCKED,
                    method_used=source,  # Use the source provided by the password iterator
                    error_message=None,
                )
        except pikepdf.PasswordError:
            # This password didn't work, continue to the next one
            continue
        except Exception as e:
            # Some other error occurred
            return UnlockResult(
                file_path=filepath,
                status=UnlockStatus.FAILED,
                error_message=f"Error processing PDF with password: {str(e)}",
            )

    # If we get here, no password worked
    return UnlockResult(
        file_path=filepath, status=UnlockStatus.FAILED, error_message="All passwords failed"
    )
