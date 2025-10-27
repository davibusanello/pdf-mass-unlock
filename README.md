# PDF Mass Unlock

[![CI](https://github.com/davibusanello/pdf-mass-unlock/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/davibusanello/pdf-mass-unlock/actions/workflows/ci.yml?query=branch:main)
[![codecov](https://codecov.io/github/davibusanello/pdf-mass-unlock/graph/badge.svg?token=PKEJ9SBMDV)](https://codecov.io/github/davibusanello/pdf-mass-unlock)

PDF Mass Unlock is a safe, cross-platform CLI tool to recursively find PDFs, attempt password removal using supplied credentials, and save decrypted files while keeping reliable backups.

## Features

- Recursively scan directories for PDF files (case-insensitive)
- Try passwords from multiple sources in order:
  1. Explicit `--password` CLI flag
  2. Dictionary file (one password per line)
  3. Environment variable `PDFMASSUNLOCK_PASSWORD`
  4. Empty password (if `--try-empty` is used)
- Create backups before modifying any files
- Atomic writes to prevent data corruption
- Clear progress indicators and summary reports
- Cross-platform compatibility (Windows, macOS, Linux)

## Installation

### For Development (Current)
```bash
# Install dependencies using uv (recommended)
uv sync --group dev

# Show CLI help
uv run pdf-mass-unlock --help
```

### For General Use (Future)
```bash
# After publishing to PyPI (future)
pip install pdf-mass-unlock
```

## Usage

### Basic Usage

```bash
uv run pdf-mass-unlock --path /path/to/search
```

### With a Single Password

```bash
uv run pdf-mass-unlock --path /path/to/search --password "your_password"
```

### With a Dictionary File

```bash
uv run pdf-mass-unlock --path /path/to/search --dictionary /path/to/dictionary.txt
```

The dictionary file should contain one password per line:
```
password1
password2
password3
```

### With Summary and Dry Run

```bash
uv run pdf-mass-unlock --path /path/to/search --password "your_password" --summary --dry-run
```

### With Custom Backup Directory Name

```bash
uv run pdf-mass-unlock --path /path --password "secret" --backup-dir-name backups --summary
```

## Options

- `--path PATH`: Root directory to scan for PDFs (required)
- `--password TEXT`: Single password to try for unlocking PDFs
- `--dictionary FILE`: Path to dictionary file with passwords (one per line) [default: dictionary.txt]
- `--try-empty`: Also try an empty password
- `--backup-dir-name TEXT`: Name of sibling backup directories created alongside PDFs [default: pdf_with_password]
- `--dry-run`: Do not modify files; only report planned actions
- `--summary`: Print a final summary table
- `--log-level TEXT`: Logging level (INFO, WARN, DEBUG) [default: INFO]
- `--version`: Show version and exit
- `--backup-root PATH`: Deprecated alias for `--backup-dir-name`

## Safety Features

- **Backups**: Creates a backup of each PDF before attempting to unlock it
- **Atomic Writes**: Uses temporary files and atomic replacement to prevent corruption
- **Secret Protection**: Passwords are never logged or printed to console
- **Error Handling**: Comprehensive exception handling with user-friendly messages

## Security Notes

- This tool does not crack passwords or bypass security by force
- It only attempts to unlock PDFs using provided credentials
- Decrypted PDFs and backups may contain sensitive information - handle with care
- Passwords should be managed securely and not stored in plain text if possible

## Development

This project uses `uv` for dependency management and follows modern Python practices (Python 3.13, TDD).

To set up the development environment:

```bash
uv sync
```

To run tests:

```bash
uv run pytest
```

To format code:

```bash
uv run ruff format .
```

To lint code:

```bash
uv run ruff check .
```

## License

GPLv3
