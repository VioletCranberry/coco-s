"""Utility functions for search result processing.

Provides byte offset to line number conversion and chunk content
reading from source files for result formatting.
"""


def byte_to_line(filepath: str, byte_offset: int) -> int:
    """Convert byte offset to 1-based line number.

    Args:
        filepath: Path to the source file.
        byte_offset: Byte offset in the file.

    Returns:
        1-based line number, or 0 if file not accessible.
    """
    try:
        with open(filepath, "rb") as f:
            content = f.read(byte_offset)
            return content.count(b"\n") + 1
    except (FileNotFoundError, IOError):
        return 0  # File not accessible


def read_chunk_content(filepath: str, start_byte: int, end_byte: int) -> str:
    """Read chunk content from source file.

    Args:
        filepath: Path to the source file.
        start_byte: Start byte offset.
        end_byte: End byte offset.

    Returns:
        Chunk text content, or empty string if file not accessible.
    """
    try:
        with open(filepath, "rb") as f:
            f.seek(start_byte)
            content = f.read(end_byte - start_byte)
            return content.decode("utf-8", errors="replace")
    except (FileNotFoundError, IOError):
        return ""


def get_context_lines(
    filepath: str,
    start_line: int,
    end_line: int,
    context: int = 5,
) -> tuple[list[str], list[str]]:
    """Get lines before and after a code chunk.

    Args:
        filepath: Path to the source file.
        start_line: 1-based start line of chunk.
        end_line: 1-based end line of chunk.
        context: Number of context lines to include.

    Returns:
        Tuple of (lines_before, lines_after).
    """
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()

        # Calculate context ranges (0-indexed)
        before_start = max(0, start_line - 1 - context)
        before_end = start_line - 1
        after_start = end_line
        after_end = min(len(all_lines), end_line + context)

        lines_before = all_lines[before_start:before_end]
        lines_after = all_lines[after_start:after_end]

        return (
            [line.rstrip("\n\r") for line in lines_before],
            [line.rstrip("\n\r") for line in lines_after],
        )
    except (FileNotFoundError, IOError):
        return ([], [])
