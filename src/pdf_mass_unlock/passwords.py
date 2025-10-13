import unicodedata
from pathlib import Path
from typing import Iterator, Mapping, Set


def iter_passwords(
    single: str = None,
    dictionary_path: Path = None,
    env: Mapping[str, str] = None,
    try_empty: bool = False,
) -> Iterator[tuple[str, str]]:
    """
    Generate passwords with their source in the correct order: single, dictionary, env var, empty.

    Args:
        single: A single password provided via CLI flag
        dictionary_path: Path to dictionary file with one password per line
        env: Environment mapping (to get PDFMASSUNLOCK_PASSWORD)
        try_empty: Whether to try an empty password

    Yields:
        Tuples of (password, source) in the correct order
    """
    seen: Set[str] = set()

    # 1. Single password from CLI
    if single is not None and single not in seen:
        seen.add(single)
        yield (single, "single")

    # 2. Dictionary file
    if dictionary_path and dictionary_path.exists():
        for password in _iter_from_dictionary(dictionary_path):
            if password not in seen:
                seen.add(password)
                yield (password, "dictionary")

    # 3. Environment variable
    if env:
        env_password = env.get("PDFMASSUNLOCK_PASSWORD")
        if env_password and env_password not in seen:
            seen.add(env_password)
            yield (env_password, "environment")

    # 4. Empty password if requested
    if try_empty and "" not in seen:
        seen.add("")
        yield ("", "empty")


def _iter_from_dictionary(dictionary_path: Path) -> Iterator[str]:
    """
    Read passwords from a dictionary file, one per line.

    Args:
        dictionary_path: Path to the dictionary file

    Yields:
        Password strings (trimmed of whitespace)
    """
    with dictionary_path.open("r", encoding="utf-8-sig") as f:
        for _, line in enumerate(f, 1):
            # Only strip line endings, preserve any leading/trailing
            # spaces that might be part of the password
            password = line.rstrip("\r\n")

            # Normalize the Unicode string to handle different character representations
            password = unicodedata.normalize("NFKC", password)

            # Skip blank lines (after normalization)
            if not password.strip():  # Still skip if it's just whitespace after normalization
                continue

            # Skip comment lines (starting with #), using lstrip to handle potential leading spaces
            if password.lstrip().startswith("#"):
                continue

            yield password
