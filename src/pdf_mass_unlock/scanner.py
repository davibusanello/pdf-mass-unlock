from pathlib import Path
from typing import Iterator


def find_pdfs(root: Path, backup_dir_name: str = "pdf_with_password") -> Iterator[Path]:
    """
    Recursively find PDF files in the given root directory, skipping backup directories.

    Args:
        root: Root directory to search for PDFs
        backup_dir_name: Name of backup directories to skip (default: "pdf_with_password")

    Yields:
        Path objects for PDF files found in the directory tree
    """
    for item in root.iterdir():
        # Skip if it's a directory with the backup name
        if item.is_dir() and item.name == backup_dir_name:
            continue

        # If it's a subdirectory, recurse into it
        if item.is_dir():
            yield from find_pdfs(item, backup_dir_name)

        # If it's a file with .pdf extension (case-insensitive), yield it
        elif item.is_file() and item.suffix.lower() == ".pdf":
            yield item
