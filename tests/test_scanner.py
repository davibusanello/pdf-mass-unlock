import tempfile
from pathlib import Path

from pdf_mass_unlock.scanner import find_pdfs


def test_find_pdfs_basic():
    """Test that find_pdfs discovers PDF files in a directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create some test files
        (temp_path / "file1.pdf").touch()
        (temp_path / "file2.PDF").touch()  # Test case insensitivity
        (temp_path / "document.pdf").touch()
        (temp_path / "not_a_pdf.txt").touch()

        # Create a subdirectory with PDFs
        subdir = temp_path / "subdir"
        subdir.mkdir()
        (subdir / "another.pdf").touch()
        (subdir / "not_pdf.jpg").touch()

        # Find PDFs
        pdfs = list(find_pdfs(temp_path))

        # Check that we found the correct PDFs
        expected_files = {"file1.pdf", "file2.PDF", "document.pdf", "another.pdf"}
        found_files = {p.name for p in pdfs}

        assert found_files == expected_files
        assert len(pdfs) == 4


def test_find_pdfs_skips_backup_dir():
    """Test that find_pdfs skips directories named with the backup directory name."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create backup directory
        backup_dir = temp_path / "pdf_with_password"
        backup_dir.mkdir()
        (backup_dir / "backup_file.pdf").touch()  # This should be skipped

        # Create regular PDF in main directory
        (temp_path / "regular.pdf").touch()

        # Find PDFs
        pdfs = list(find_pdfs(temp_path))

        # Should only find the regular PDF, not the one in backup directory
        assert len(pdfs) == 1
        assert pdfs[0].name == "regular.pdf"


def test_find_pdfs_with_custom_backup_dir():
    """Test that find_pdfs skips custom backup directory name."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create custom backup directory
        backup_dir = temp_path / "my_backup"
        backup_dir.mkdir()
        (backup_dir / "backup_file.pdf").touch()  # This should be skipped

        # Create regular PDF in main directory
        (temp_path / "regular.pdf").touch()

        # Find PDFs using custom backup directory name
        pdfs = list(find_pdfs(temp_path, backup_dir_name="my_backup"))

        # Should only find the regular PDF, not the one in backup directory
        assert len(pdfs) == 1
        assert pdfs[0].name == "regular.pdf"


def test_find_pdfs_case_insensitive():
    """Test that find_pdfs matches PDF extension case-insensitively."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create PDFs with different case extensions
        (temp_path / "file1.pdf").touch()
        (temp_path / "file2.PDF").touch()
        (temp_path / "file3.Pdf").touch()
        (temp_path / "file4.PdF").touch()

        # Find PDFs
        pdfs = list(find_pdfs(temp_path))

        assert len(pdfs) == 4
        extensions = {p.suffix.lower() for p in pdfs}
        assert extensions == {".pdf"}


if __name__ == "__main__":
    test_find_pdfs_basic()
    test_find_pdfs_skips_backup_dir()
    test_find_pdfs_with_custom_backup_dir()
    test_find_pdfs_case_insensitive()
    print("All scanner tests passed!")
