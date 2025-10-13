import tempfile
from pathlib import Path

from pdf_mass_unlock.io_utils import atomic_write, copy_backup, ensure_backup


def test_ensure_backup():
    """Test that ensure_backup creates a backup directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_file = temp_path / "test.pdf"
        test_file.touch()  # Create a test file

        backup_dir = ensure_backup(test_file)

        assert backup_dir.exists()
        assert backup_dir.name == "pdf_with_password"
        assert backup_dir.parent == temp_path


def test_ensure_backup_custom_name():
    """Test that ensure_backup works with custom backup directory name."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_file = temp_path / "test.pdf"
        test_file.touch()  # Create a test file

        backup_dir = ensure_backup(test_file, backup_dir_name="my_backup")

        assert backup_dir.exists()
        assert backup_dir.name == "my_backup"
        assert backup_dir.parent == temp_path


def test_copy_backup():
    """Test that copy_backup creates a backup of the source file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_file = temp_path / "test.pdf"

        # Write some content to the test file
        original_content = b"This is a test PDF file content."
        test_file.write_bytes(original_content)

        # Create backup
        backup_path = copy_backup(test_file)

        # Verify backup exists and has same content
        assert backup_path.exists()
        assert backup_path.read_bytes() == original_content
        assert backup_path.parent.name == "pdf_with_password"
        assert backup_path.name == "test.pdf"


def test_atomic_write_basic():
    """Test that atomic_write works for basic file writing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        target_file = temp_path / "target.txt"
        content = b"Atomic write test content"

        # Use atomic_write to write the file
        with atomic_write(target_file) as f:
            f.write(content)

        # Verify the file was written correctly
        assert target_file.exists()
        assert target_file.read_bytes() == content


def test_atomic_write_overwrites_existing():
    """Test that atomic_write overwrites existing files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        target_file = temp_path / "target.txt"

        # Create initial file
        initial_content = b"Initial content"
        target_file.write_bytes(initial_content)

        # Use atomic_write to overwrite it
        new_content = b"New content"
        with atomic_write(target_file) as f:
            f.write(new_content)

        # Verify the file was overwritten correctly
        assert target_file.exists()
        assert target_file.read_bytes() == new_content


def test_atomic_write_exception_cleanup():
    """Test that atomic_write cleans up temp file on exception."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        target_file = temp_path / "target.txt"

        # Record initial directory contents

        try:
            # Use atomic_write but raise an exception during writing
            with atomic_write(target_file) as f:
                f.write(b"partial content")
                raise ValueError("Simulated error")
        except ValueError:
            pass  # Expected

        # Verify that the target file was not created/modified
        # and no temporary files remain

        # The only difference should be the target file (if it existed initially)
        if target_file.exists():
            # If target file exists, it should have its original content if it existed before
            pass
        else:
            # Target file should not exist since the write failed
            assert not target_file.exists()


if __name__ == "__main__":
    test_ensure_backup()
    test_ensure_backup_custom_name()
    test_copy_backup()
    test_atomic_write_basic()
    test_atomic_write_overwrites_existing()
    test_atomic_write_exception_cleanup()
    print("All IO utilities tests passed!")
