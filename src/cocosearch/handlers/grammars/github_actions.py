"""Grammar handler for GitHub Actions workflow files.

Provides domain-specific chunking and metadata extraction for GitHub Actions
workflow YAML files found in .github/workflows/.

Matches: .github/workflows/*.yml, .github/workflows/*.yaml
Content markers: 'on:' and 'jobs:'
"""

import fnmatch
import re

import cocoindex


class GitHubActionsHandler:
    """Grammar handler for GitHub Actions workflow files."""

    GRAMMAR_NAME = "github-actions"
    BASE_LANGUAGE = "yaml"
    PATH_PATTERNS = [".github/workflows/*.yml", ".github/workflows/*.yaml"]

    SEPARATOR_SPEC = cocoindex.functions.CustomLanguageSpec(
        language_name="github-actions",
        separators_regex=[
            # Level 1: YAML document separator
            r"\n---",
            # Level 2: Top-level keys (name:, on:, jobs:, env:, permissions:)
            r"\n[a-zA-Z_][\w-]*:\s*\n",
            # Level 3: Job boundaries (2-space indented keys under jobs:)
            r"\n  [a-zA-Z_][\w-]*:",
            # Level 4: Job-level keys (4-space indented: runs-on:, steps:, env:)
            r"\n    [a-zA-Z_][\w-]*:",
            # Level 5: Step boundaries (- name: or - uses:)
            r"\n      - ",
            # Level 6: Blank lines
            r"\n\n+",
            # Level 7: Single newlines
            r"\n",
            # Level 8: Whitespace (last resort)
            r" ",
        ],
        aliases=[],
    )

    _COMMENT_LINE = re.compile(r"^\s*#.*$", re.MULTILINE)

    # Top-level key at start of line (with or without inline value)
    _TOP_KEY_RE = re.compile(r"^([a-zA-Z_][\w-]*):", re.MULTILINE)

    # Job/item definition (2-space indented key)
    _ITEM_RE = re.compile(r"^  ([a-zA-Z_][\w-]*):", re.MULTILINE)

    # Nested key (4+ space indented key, e.g., runs-on:, steps:, env:)
    _NESTED_KEY_RE = re.compile(r"^\s{4,}([a-zA-Z_][\w-]*):", re.MULTILINE)

    # Match step with 'name:' key
    _STEP_NAME_RE = re.compile(r"^\s*-\s+name:\s*(.+)$", re.MULTILINE)

    # Match step with 'uses:' key
    _STEP_USES_RE = re.compile(r"^\s*-?\s*uses:\s*(.+)$", re.MULTILINE)

    # YAML list item key (e.g., "- name: value", "  - path: ./src")
    _LIST_ITEM_KEY_RE = re.compile(r"^\s*-\s+([a-zA-Z_][\w-]*):", re.MULTILINE)

    # GitHub Actions top-level keywords (not job names)
    _TOP_LEVEL_KEYS = frozenset(
        {
            "name",
            "on",
            "jobs",
            "env",
            "permissions",
            "concurrency",
            "defaults",
            "run-name",
            "true",
            "false",
        }
    )

    def matches(self, filepath: str, content: str | None = None) -> bool:
        """Check if file is a GitHub Actions workflow.

        Checks if path ends with .github/workflows/*.yml (at any depth).

        Args:
            filepath: Relative file path within the project.
            content: Optional file content for deeper matching.

        Returns:
            True if this is a GitHub Actions workflow file.
        """
        for pattern in self.PATH_PATTERNS:
            if fnmatch.fnmatch(filepath, pattern) or fnmatch.fnmatch(
                filepath, f"*/{pattern}"
            ):
                if content is not None:
                    return "on:" in content and "jobs:" in content
                return True
        return False

    def extract_metadata(self, text: str) -> dict:
        """Extract metadata from GitHub Actions chunk.

        Identifies jobs, steps, top-level sections, nested keys,
        list items, and value continuations.

        Args:
            text: The chunk text content.

        Returns:
            Dict with block_type, hierarchy, language_id.

        Examples:
            Job chunk: block_type="job", hierarchy="job:build"
            Step chunk: block_type="step", hierarchy="step:Checkout code"
            Uses chunk: block_type="step", hierarchy="step:actions/checkout@v4"
            Nested key: block_type="nested-key", hierarchy="nested-key:runs-on"
            List item: block_type="list-item", hierarchy="list-item:path"
        """
        stripped = self._strip_comments(text)

        # Check for step (- name: or - uses:)
        step_name = self._STEP_NAME_RE.search(stripped)
        if step_name:
            name = step_name.group(1).strip().strip("'\"")
            return {
                "block_type": "step",
                "hierarchy": f"step:{name}",
                "language_id": self.GRAMMAR_NAME,
            }

        step_uses = self._STEP_USES_RE.search(stripped)
        if step_uses:
            uses = step_uses.group(1).strip().strip("'\"")
            return {
                "block_type": "step",
                "hierarchy": f"step:{uses}",
                "language_id": self.GRAMMAR_NAME,
            }

        # Check for job definition (2-space indented key)
        item_match = self._ITEM_RE.match(stripped)
        if item_match:
            job_name = item_match.group(1)
            return {
                "block_type": "job",
                "hierarchy": f"job:{job_name}",
                "language_id": self.GRAMMAR_NAME,
            }

        # Check for nested key (4+ space indented)
        nested_match = self._NESTED_KEY_RE.match(stripped)
        if nested_match:
            key = nested_match.group(1)
            return {
                "block_type": "nested-key",
                "hierarchy": f"nested-key:{key}",
                "language_id": self.GRAMMAR_NAME,
            }

        # Check for YAML list item key (e.g., "- path: value")
        list_match = self._LIST_ITEM_KEY_RE.match(stripped)
        if list_match:
            key = list_match.group(1)
            return {
                "block_type": "list-item",
                "hierarchy": f"list-item:{key}",
                "language_id": self.GRAMMAR_NAME,
            }

        # Check for top-level keys
        top_match = self._TOP_KEY_RE.match(stripped)
        if top_match:
            key = top_match.group(1)
            return {
                "block_type": key,
                "hierarchy": key,
                "language_id": self.GRAMMAR_NAME,
            }

        # YAML document separator (--- chunks)
        if "---" in text:
            return {
                "block_type": "document",
                "hierarchy": "document",
                "language_id": self.GRAMMAR_NAME,
            }

        # Value continuation (chunk has content but no recognizable key)
        if stripped:
            return {
                "block_type": "value",
                "hierarchy": "value",
                "language_id": self.GRAMMAR_NAME,
            }

        return {
            "block_type": "",
            "hierarchy": "",
            "language_id": self.GRAMMAR_NAME,
        }

    def _strip_comments(self, text: str) -> str:
        """Strip leading comments from chunk text, preserving indentation."""
        lines = text.lstrip("\n").split("\n")
        for i, line in enumerate(lines):
            if line.strip() and not self._COMMENT_LINE.match(line):
                return "\n".join(lines[i:])
        return ""
