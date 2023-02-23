import os
import pikepdf
import logging
import coloredlogs
import shutil
import sys


pdf_password = sys.argv[1]
working_directory = sys.argv[2]
backup_directory = "pdf_with_password"


def backup_file(file_full_path: str) -> bool:
    """
    Backup the given file to a backup directory.

    :param file_full_path: The full path of the file to be backed up.
    :return: True if the backup is successful, False otherwise.
    """
    try:
        file_path = os.path.dirname(file_full_path)
        file_name = os.path.basename(file_full_path)
        backup_path = os.path.join(file_path, backup_directory)

        if not os.path.exists(backup_path):
            os.makedirs(backup_path)
        shutil.copy2(file_full_path, os.path.join(backup_path, file_name))
        return True
    except:
        mylogs.error("Failed to backup %s it was skipped",
                     os.path.basename(file_full_path))
        return False


def count_files(directory: str) -> int:
    """
    Count the number of PDF files in the given directory and its subdirectories.

    :param directory: The path of the directory to count PDF files in.
    :return: The number of PDF files found.
    """
    count = 0
    for filename in os.listdir(directory):
        path = os.path.join(directory, filename)
        if os.path.isfile(path) and path.endswith(".pdf"):
            count += 1
        elif os.path.isdir(path) and not path.endswith(backup_directory):
            count += count_files(path)
    return count


def configure_logging() -> logging.Logger:
    """
    Configure the logging settings and create a logger.

    :return: The configured logger instance.
    """
    script_name = os.path.basename(__file__)
    logging.basicConfig(level=logging.DEBUG,
                        filename=script_name + ".log",
                        filemode="a",
                        encoding='utf-8',
                        format='[%(asctime)s] [%(levelname)s] %(message)s')

    mylogs = logging.getLogger(__name__)
    stream = logging.StreamHandler()
    mylogs.addHandler(stream)
    coloredlogs.install(level=logging.DEBUG,
                        logger=mylogs,
                        fmt='[%(asctime)s] [%(levelname)s] %(message)s')
    return mylogs


def process_files(working_directory: str):
    """
    Process all PDF files in the working directory and its subdirectories,
    backing up the files and attempting to remove their passwords.

    :param working_directory: The path of the directory to process PDF files in.
    """
    nb = 0

    for subdir, _, files in os.walk(working_directory):
        if subdir.endswith(backup_directory):
            mylogs.debug("Backup directory, skipping...")
            continue

        for file in files:
            filepath = os.path.join(subdir, file)
            if filepath.endswith(".pdf"):
                nb += 1
                mylogs.info(f"{nb}) File processing: {file} ({filepath})")

                if backup_file(filepath):
                    mylogs.info(f"{file} was backed up")

                try:
                    pdf = pikepdf.open(filepath)
                    mylogs.info(f"{file} isn't locked with a password")
                except pikepdf.PasswordError:
                    try:
                        pdf = pikepdf.open(filepath, password=str(
                            pdf_password), allow_overwriting_input=True)
                        pdf.save(filepath)
                        mylogs.info(f"Successfully removed password on {file}")
                    except pikepdf.PasswordError:
                        mylogs.error(f"Bad password for {file}")
                    except:
                        mylogs.error(f"Failed to remove password on {file}")


if __name__ == "main":
    mylogs = configure_logging()
    mylogs.info("Starting script %s", os.path.basename(__file__))
    mylogs.info("Current directory: %s", os.getcwd())
    mylogs.info("Working directory: %s", working_directory)
    mylogs.info("Number of files to process: %s",
                str(count_files(working_directory)))
    mylogs.info("Password to remove: %s", pdf_password)
    mylogs.info("_" * 50)

    process_files(working_directory)

    os.system("pause")
