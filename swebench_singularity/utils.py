"""
Utility functions for SWE-bench Singularity Runner.

Common utilities for file operations, logging, formatting, etc.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import json


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """
    Setup logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        format_string: Optional format string

    Returns:
        Configured logger
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(format_string))
    handlers.append(console_handler)

    # File handler
    if log_file:
        log_file = os.path.expanduser(log_file)
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(format_string))
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers,
        force=True,
    )

    return logging.getLogger(__name__)


def format_time(seconds: float) -> str:
    """
    Format seconds to human-readable time string.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted time string (e.g., "1h 23m 45s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


def format_bytes(bytes_count: int) -> str:
    """
    Format bytes to human-readable size string.

    Args:
        bytes_count: Size in bytes

    Returns:
        Formatted size string (e.g., "1.23 GB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"


def ensure_dir(path: Path) -> Path:
    """
    Ensure directory exists, create if necessary.

    Args:
        path: Directory path

    Returns:
        Path object
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(file_path: Path) -> Dict[str, Any]:
    """
    Load JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data
    """
    with open(file_path, "r") as f:
        return json.load(f)


def save_json(data: Any, file_path: Path, indent: int = 2):
    """
    Save data to JSON file.

    Args:
        data: Data to save
        file_path: Output file path
        indent: JSON indentation
    """
    ensure_dir(file_path.parent)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=indent)


def print_table(headers: list, rows: list, title: Optional[str] = None):
    """
    Print formatted table to console.

    Args:
        headers: Column headers
        rows: List of row data
        title: Optional table title
    """
    if not rows:
        print("No data to display")
        return

    # Calculate column widths
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    # Print title
    if title:
        total_width = sum(widths) + 3 * (len(headers) - 1)
        print("\n" + "=" * total_width)
        print(title.center(total_width))
        print("=" * total_width)

    # Print header
    header_str = " | ".join(str(h).ljust(w) for h, w in zip(headers, widths))
    print("\n" + header_str)
    print("-" * len(header_str))

    # Print rows
    for row in rows:
        row_str = " | ".join(str(cell).ljust(w) for cell, w in zip(row, widths))
        print(row_str)

    print()


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Ask user for confirmation.

    Args:
        message: Confirmation message
        default: Default value if user just presses Enter

    Returns:
        True if confirmed, False otherwise
    """
    prompt = f"{message} [{'Y/n' if default else 'y/N'}]: "
    response = input(prompt).strip().lower()

    if not response:
        return default

    return response in ["y", "yes"]


def validate_instance_id(instance_id: str) -> bool:
    """
    Validate instance ID format.

    Args:
        instance_id: Instance ID to validate

    Returns:
        True if valid format
    """
    import re

    pattern = r"^[a-zA-Z0-9_-]+__[a-zA-Z0-9_.-]+-\d+$"
    return bool(re.match(pattern, instance_id))


def parse_instance_list(instance_list_path: Path) -> list[str]:
    """
    Parse instance list from file.

    Supports:
    - Plain text files with one instance ID per line
    - JSON files with list of instance IDs
    - JSON files with predictions format

    Args:
        instance_list_path: Path to instance list file

    Returns:
        List of instance IDs
    """
    if not instance_list_path.exists():
        raise FileNotFoundError(f"Instance list not found: {instance_list_path}")

    # Try JSON first
    try:
        data = load_json(instance_list_path)

        # Check if it's a list
        if isinstance(data, list):
            # Could be list of instance IDs or list of dicts
            if data and isinstance(data[0], dict):
                # Extract instance_id from dicts
                return [item.get("instance_id") for item in data if "instance_id" in item]
            else:
                return data

        # Check if it's a dict with predictions format
        if isinstance(data, dict):
            return list(data.keys())

    except json.JSONDecodeError:
        pass

    # Fall back to plain text
    with open(instance_list_path, "r") as f:
        instance_ids = [line.strip() for line in f if line.strip()]

    return instance_ids


class ProgressBar:
    """Simple progress bar for console output."""

    def __init__(self, total: int, prefix: str = "", width: int = 50):
        """
        Initialize progress bar.

        Args:
            total: Total number of items
            prefix: Prefix text
            width: Width of progress bar
        """
        self.total = total
        self.prefix = prefix
        self.width = width
        self.current = 0

    def update(self, increment: int = 1):
        """Update progress bar."""
        self.current += increment
        self._render()

    def _render(self):
        """Render progress bar."""
        if self.total == 0:
            return

        percent = self.current / self.total
        filled = int(self.width * percent)
        bar = "█" * filled + "░" * (self.width - filled)

        print(
            f"\r{self.prefix} |{bar}| {self.current}/{self.total} ({percent*100:.1f}%)",
            end="",
            flush=True,
        )

        if self.current >= self.total:
            print()  # New line when complete
