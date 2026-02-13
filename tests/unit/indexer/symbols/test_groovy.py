"""Tests for Groovy symbol extraction.

Note: tree-sitter-groovy uses a flat AST structure (generic command/unit/identifier
nodes) without distinct node types for class/method/interface declarations. This
means meaningful symbol extraction via .scm queries is not feasible with the current
grammar. These tests verify that Groovy gracefully returns NULL symbol metadata.
"""

from cocosearch.indexer.symbols import extract_symbol_metadata


class TestGroovySymbols:
    """Test Groovy symbol extraction (graceful NULL behavior)."""

    def test_class_returns_null(self):
        """Groovy class returns NULL fields (no .scm query available)."""
        code = "class MyService { }"
        result = extract_symbol_metadata(code, "groovy")

        assert result.symbol_type is None
        assert result.symbol_name is None
        assert result.symbol_signature is None

    def test_interface_returns_null(self):
        """Groovy interface returns NULL fields."""
        code = "interface Searchable { List search(String query) }"
        result = extract_symbol_metadata(code, "groovy")

        assert result.symbol_type is None

    def test_def_returns_null(self):
        """Groovy def returns NULL fields."""
        code = "def processData(List items) { return items }"
        result = extract_symbol_metadata(code, "groovy")

        assert result.symbol_type is None

    def test_empty_input(self):
        """Empty Groovy returns NULL fields."""
        result = extract_symbol_metadata("", "groovy")

        assert result.symbol_type is None

    def test_gradle_extension_mapped(self):
        """gradle extension maps to groovy language."""
        code = "apply plugin: 'java'"
        result = extract_symbol_metadata(code, "gradle")

        assert result.symbol_type is None
