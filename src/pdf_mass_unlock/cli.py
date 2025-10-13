import os
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .logging_utils import get_logger
from .passwords import iter_passwords
from .scanner import find_pdfs
from .unlocker import UnlockStatus, try_unlock_dry_run, unlock_file

app = typer.Typer(add_completion=False, invoke_without_command=True)
console = Console()


def version_callback(value: bool):
    if value:
        typer.echo("pdf-mass-unlock v0.1.0")
        raise typer.Exit()


@app.callback()
def main(
    path: Path = typer.Option(
        None,
        "--path",
        help="Root directory to scan for PDFs",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    password: str = typer.Option(
        None,
        "--password",
        help="Single password to try for unlocking PDFs",
    ),
    dictionary: str = typer.Option(
        "dictionary.txt",  # This is still a B008 issue but we need the default value
        "--dictionary",
        help="Path to dictionary file with passwords (one per line)",
        file_okay=True,
        dir_okay=False,
    ),
    try_empty: bool = typer.Option(
        False,
        "--try-empty",
        help="Also try an empty password",
    ),
    backup_dir_name: str = typer.Option(
        "pdf_with_password",
        "--backup-dir-name",
        help=(
            "Name of sibling backup directories created "
            "alongside PDFs (default: 'pdf_with_password')"
        ),
    ),
    backup_root: Path = typer.Option(  # Deprecated alias for backward compatibility
        None,
        "--backup-root",
        help="Deprecated alias for --backup-dir-name",
        hidden=True,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Do not modify files; only report planned actions",
    ),
    summary: bool = typer.Option(
        False,
        "--summary",
        help="Print a final summary table",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Logging level (INFO, WARN, DEBUG)",
    ),
    version: bool = typer.Option(
        None,
        "--version",
        help="Show version and exit",
        callback=version_callback,
    ),
):
    """
    PDF Mass Unlock - A safe, cross-platform CLI to recursively find PDFs,
    attempt password removal using supplied credentials, and save decrypted
    files while keeping reliable backups.
    """
    if path is None:
        typer.echo("Error: --path is required", err=True)
        raise typer.Exit(code=2)

    # Get logger
    logger = get_logger(__name__, log_level)

    # Log initialization details
    logger.info(f"Starting PDF mass unlock process in: {path}")
    _log_input_details(password, dictionary, try_empty, dry_run, logger)

    # Find PDF files
    pdf_files = list(find_pdfs(path))
    logger.info(f"Found {len(pdf_files)} PDF files to process")

    if not pdf_files:
        console.print("[yellow]No PDF files found to process.[/yellow]")
        raise typer.Exit(code=0)

    # Create a password factory to provide a fresh iterator for each file
    def password_factory():
        dictionary_path = Path(dictionary) if dictionary else None
        env = os.environ

        # First try the dictionary path as provided
        final_dict_path = dictionary_path
        if dictionary_path and not dictionary_path.exists():
            # If relative path doesn't exist from CWD, try relative to scan root
            scan_relative_path = path / dictionary_path
            if scan_relative_path.exists():
                final_dict_path = scan_relative_path
                logger.debug(f"Using dictionary file relative to scan path: {scan_relative_path}")
            else:
                logger.warning(
                    f"Dictionary file not found: {dictionary_path} "
                    "(tried CWD and relative to scan path)"
                )
                final_dict_path = None
        elif dictionary_path:
            logger.debug(f"Using dictionary file: {dictionary_path}")

        return iter_passwords(
            single=password,
            dictionary_path=final_dict_path,
            env=env,
            try_empty=try_empty,
        )

    # Handle deprecated --backup-root option
    if backup_root is not None:
        backup_dir_name = backup_root.name  # Use deprecated option value if provided
        logger.warning("--backup-root is deprecated; use --backup-dir-name instead")

    # Process files
    processed, unlocked, failed, unchanged = process_pdfs(
        pdf_files, password_factory, backup_dir_name, dry_run, logger, console
    )

    # Print summary if requested
    if summary:
        print_summary(processed, unlocked, failed, unchanged)

    # Determine exit code
    exit_code = 0 if failed == 0 else 1
    logger.info("PDF mass unlock process completed")
    raise typer.Exit(code=exit_code)


def find_and_validate_pdfs(path: Path, logger):
    """Find PDF files and validate there are any to process."""
    pdf_files = list(find_pdfs(path))
    logger.info(f"Found {len(pdf_files)} PDF files to process")

    if not pdf_files:
        console.print("[yellow]No PDF files found to process.[/yellow]")


def process_pdfs(pdf_files, password_factory, backup_dir_name, dry_run, logger, console):
    """Process all PDF files with progress tracking."""
    processed = 0
    unlocked = 0
    failed = 0
    unchanged = 0

    # Process files with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing PDFs...", total=len(pdf_files))

        for pdf_path in pdf_files:
            progress.update(task, description=f"Processing [blue]{pdf_path.name}[/blue]...")

            if dry_run:
                # In dry-run mode, simulate what would happen without modifying files
                logger.info(f"DRY RUN: Would attempt to unlock {pdf_path}")
                # Get a fresh password iterator for each file
                password_iter = password_factory()
                result = try_unlock_dry_run(
                    filepath=pdf_path, passwords=password_iter, backup_dir_name=backup_dir_name
                )
            else:
                # In normal mode, actually try to unlock the file
                # Get a fresh password iterator for each file
                password_iter = password_factory()
                result = unlock_file(
                    filepath=pdf_path, passwords=password_iter, backup_dir_name=backup_dir_name
                )

            # Update counts and log
            if result.status == UnlockStatus.UNLOCKED:
                unlocked += 1
                logger.info(f"✓ Unlocked {pdf_path.name}")
            elif result.status == UnlockStatus.UNCHANGED:
                unchanged += 1
                logger.debug(f"- {pdf_path.name} was already unlocked")
            else:  # FAILED
                failed += 1
                logger.warning(f"✗ Failed to unlock {pdf_path.name}: {result.error_message}")

            processed += 1
            progress.update(task, advance=1)

    return processed, unlocked, failed, unchanged


def print_summary(processed: int, unlocked: int, failed: int, unchanged: int):
    """Print a summary table of the operation results."""
    table = Table(title="Operation Summary")

    table.add_column("Status", style="cyan")
    table.add_column("Count", style="magenta")
    table.add_column("Description", style="green")

    table.add_row("Processed", str(processed), "Total PDF files processed")
    table.add_row("Unlocked", str(unlocked), "Files that were successfully unlocked")
    table.add_row("Failed", str(failed), "Files that failed to unlock")
    table.add_row("Unchanged", str(unchanged), "Files that were already unlocked")

    console.print(table)


def _log_input_details(password: str, dictionary: str, try_empty: bool, dry_run: bool, logger):
    """Log details about input parameters."""
    if password:
        logger.debug("Using single password (masked)")

    dict_path = Path(dictionary) if dictionary else None
    if dict_path and dict_path.exists():
        logger.info(f"Using dictionary file: {dict_path}")

    if try_empty:
        logger.info("Will try empty password")
    if dry_run:
        logger.info("DRY RUN MODE - No files will be modified")


if __name__ == "__main__":
    app()
