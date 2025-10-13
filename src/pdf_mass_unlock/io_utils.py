import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path


def ensure_backup(src: Path, backup_dir_name: str = "pdf_with_password") -> Path:
    """
    Ensure that a backup directory exists next to the source file.

    Args:
        src: Path to the source file
        backup_dir_name: Name for the backup directory (default: "pdf_with_password")

    Returns:
        Path to the backup directory
    """
    backup_dir = src.parent / backup_dir_name
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


def validate_backup_path_no_side_effects(
    src: Path, backup_dir_name: str = "pdf_with_password"
) -> Path:
    """
    Validate that backup can be created without actually creating any files or directories.

    This function checks if the backup directory exists or can be created and is writable
    without actually creating directories or temporary files. Useful for dry-run operations.

    Args:
        src: Path to the source file to back up
        backup_dir_name: Name for the backup directory (default: "pdf_with_password")

    Returns:
        Path to the backup file (without creating it)
    """
    backup_dir = src.parent / backup_dir_name
    backup_path = backup_dir / src.name

    # Check if backup directory already exists and is writable
    if backup_dir.exists():
        if not os.access(backup_dir, os.W_OK):
            raise PermissionError(f"Backup directory exists but is not writable: {backup_dir}")
    else:
        # Check if we can create the backup directory by checking parent directory permissions
        parent_dir = src.parent
        if not os.access(parent_dir, os.W_OK):
            raise PermissionError(f"Parent directory is not writable: {parent_dir}")

    return backup_path


def validate_backup_path(src: Path, backup_dir_name: str = "pdf_with_password") -> Path:
    """
    Validate that backup can be created without actually copying the file.

    This function ensures the backup directory can be created and is accessible
    without actually copying the file content. Creates directories and temporary
    files to fully simulate the backup process.

    Args:
        src: Path to the source file to back up
        backup_dir_name: Name for the backup directory (default: "pdf_with_password")

    Returns:
        Path to the backup file (without creating it)
    """
    # Create backup directory, potentially failing with permissions
    backup_dir = ensure_backup(src, backup_dir_name)
    backup_path = backup_dir / src.name

    # Check if the backup directory is writable by attempting to create a temporary file there
    # This simulates the conditions under which copy_backup would operate
    try:
        # Check if we can write to the backup directory by creating a temporary file
        # We don't need to actually create a file, just make sure the directory is accessible
        # If backup file already exists, check if we can stat it (access it)
        if backup_path.exists():
            backup_path.stat()
        # If not exists, the directory creation by ensure_backup already validated directory access
        # For a more thorough check, let's create and delete a temporary file
        test_path = backup_path.with_name(backup_path.name + ".tmp_test")
        test_path.touch()
        test_path.unlink()
    except OSError as e:
        # Re-raise the original exception which contains the specific error
        raise e

    return backup_path


def copy_backup(src: Path, backup_dir_name: str = "pdf_with_password") -> Path:
    """
    Create a backup of the source file in the backup directory.

    Args:
        src: Path to the source file to back up
        backup_dir_name: Name for the backup directory (default: "pdf_with_password")

    Returns:
        Path to the backup file
    """
    backup_dir = ensure_backup(src, backup_dir_name)
    backup_path = backup_dir / src.name

    # Use copy2 to preserve metadata
    shutil.copy2(src, backup_path)
    return backup_path


@contextmanager
def atomic_write(filepath: Path):
    """
    Context manager for atomic file writing using a temporary file.

    Args:
        filepath: Path to the target file that should be atomically written

    Yields:
        Temporary file object for writing
    """
    # Create a temporary file in the same directory as the target
    # to ensure atomic move (os.replace) works across filesystems
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=filepath.parent, delete=False, suffix=".tmp"
    ) as tmp_file:
        temp_path = Path(tmp_file.name)
        try:
            # Yield the temporary file for writing
            yield tmp_file
            # Flush and sync to ensure data is written
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        except:
            # If an exception occurs, cleanup the temporary file
            temp_path.unlink(missing_ok=True)
            raise

    # Replace the target file with the temporary file atomically
    os.replace(temp_path, filepath)
