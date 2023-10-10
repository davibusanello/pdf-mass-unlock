import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import shutil
from main import backup_file, count_files

def test_backup_file(tmp_path):
    test_file = tmp_path / "test_file.txt"
    with open(test_file, "w") as f:
        f.write("test content")

    backup_success = backup_file(str(test_file))
    backup_dir = os.path.join(os.path.dirname(test_file), "pdf_with_password")
    backup_file_path = os.path.join(backup_dir, os.path.basename(test_file))

    assert backup_success
    assert os.path.exists(backup_file_path)

    shutil.rmtree(backup_dir)


def test_count_files(tmp_path):
    os.makedirs(tmp_path / "subdir")

    pdf_files = ["file1.pdf", "file2.pdf", "subdir/file3.pdf"]
    non_pdf_files = ["file4.txt", "subdir/file5.docx"]

    for file in pdf_files + non_pdf_files:
        with open(tmp_path / file, "w") as f:
            f.write("test content")

    count = count_files(str(tmp_path))
    assert count == len(pdf_files)

    for file in pdf_files + non_pdf_files:
        os.remove(tmp_path / file)

    os.rmdir(tmp_path / "subdir")
