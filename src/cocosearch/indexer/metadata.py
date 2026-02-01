"""Backward-compatible re-exports from cocosearch.handlers.

DEPRECATED: Import directly from cocosearch.handlers instead.
This module is retained for backward compatibility only.
"""

import re
from dataclasses import dataclass

from cocosearch.handlers import extract_devops_metadata
from cocosearch.handlers.hcl import HclHandler
from cocosearch.handlers.dockerfile import DockerfileHandler
from cocosearch.handlers.bash import BashHandler


@dataclass
class DevOpsMetadata:
    """Backward-compatible metadata class."""

    block_type: str
    hierarchy: str
    language_id: str


# Re-export extraction functions
def extract_hcl_metadata(text: str) -> DevOpsMetadata:
    """Extract metadata from HCL chunk.

    DEPRECATED: Use HclHandler().extract_metadata() instead.
    """
    m = HclHandler().extract_metadata(text)
    return DevOpsMetadata(**m)


def extract_dockerfile_metadata(text: str) -> DevOpsMetadata:
    """Extract metadata from Dockerfile chunk.

    DEPRECATED: Use DockerfileHandler().extract_metadata() instead.
    """
    m = DockerfileHandler().extract_metadata(text)
    return DevOpsMetadata(**m)


def extract_bash_metadata(text: str) -> DevOpsMetadata:
    """Extract metadata from Bash chunk.

    DEPRECATED: Use BashHandler().extract_metadata() instead.
    """
    m = BashHandler().extract_metadata(text)
    return DevOpsMetadata(**m)


# Re-export internal patterns for tests (they import these)
_HCL_COMMENT_LINE = HclHandler._COMMENT_LINE
_DOCKERFILE_COMMENT_LINE = DockerfileHandler._COMMENT_LINE
_BASH_COMMENT_LINE = BashHandler._COMMENT_LINE

_LANGUAGE_DISPATCH = {
    "hcl": extract_hcl_metadata,
    "tf": extract_hcl_metadata,
    "tfvars": extract_hcl_metadata,
    "dockerfile": extract_dockerfile_metadata,
    "sh": extract_bash_metadata,
    "bash": extract_bash_metadata,
    "zsh": extract_bash_metadata,
    "shell": extract_bash_metadata,
}

_LANGUAGE_ID_MAP = {
    "hcl": "hcl",
    "tf": "hcl",
    "tfvars": "hcl",
    "dockerfile": "dockerfile",
    "sh": "bash",
    "bash": "bash",
    "zsh": "bash",
    "shell": "bash",
}

_EMPTY_METADATA = DevOpsMetadata(block_type="", hierarchy="", language_id="")


def _strip_leading_comments(text: str, pattern: re.Pattern) -> str:
    """Strip leading comment and blank lines from chunk text.

    DEPRECATED: This is an internal helper re-exported for test compatibility.

    Args:
        text: The chunk text content.
        pattern: A compiled regex matching comment lines for the language.

    Returns:
        The text from the first non-comment, non-blank line onward.
        Empty string if all lines are comments or blank.
    """
    lines = text.lstrip().split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not pattern.match(line):
            return "\n".join(lines[i:])
    return ""


__all__ = [
    "DevOpsMetadata",
    "extract_devops_metadata",
    "extract_hcl_metadata",
    "extract_dockerfile_metadata",
    "extract_bash_metadata",
]
