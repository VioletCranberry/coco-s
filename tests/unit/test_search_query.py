"""Tests for search query graceful degradation behavior.

Tests hybrid search column detection and backward compatibility
for pre-v1.7 indexes that lack content_text column.
"""

import pytest
from unittest.mock import patch


class TestCheckColumnExists:
    """Tests for check_column_exists helper function."""

    def test_check_column_exists_detects_missing_column(self, mock_db_pool):
        """Test that check_column_exists returns False for missing columns."""
        # Mock cursor to return False (column not found)
        pool, cursor, conn = mock_db_pool(results=[(False,)])

        with patch("cocosearch.search.db.get_connection_pool", return_value=pool):
            from cocosearch.search.db import check_column_exists

            result = check_column_exists("test_table", "nonexistent_column")

        assert result is False
        cursor.assert_query_contains("information_schema.columns")

    def test_check_column_exists_detects_existing_column(self, mock_db_pool):
        """Test that check_column_exists returns True for existing columns."""
        pool, cursor, conn = mock_db_pool(results=[(True,)])

        with patch("cocosearch.search.db.get_connection_pool", return_value=pool):
            from cocosearch.search.db import check_column_exists

            result = check_column_exists("test_table", "existing_column")

        assert result is True
        cursor.assert_query_contains("information_schema.columns")

    def test_check_column_exists_passes_table_and_column_names(self, mock_db_pool):
        """Test that check_column_exists passes correct parameters to query."""
        pool, cursor, conn = mock_db_pool(results=[(True,)])

        with patch("cocosearch.search.db.get_connection_pool", return_value=pool):
            from cocosearch.search.db import check_column_exists

            check_column_exists("my_table", "my_column")

        # Verify the parameters were passed
        cursor.assert_called_with_param("my_table")
        cursor.assert_called_with_param("my_column")


class TestHybridSearchGracefulDegradation:
    """Tests for hybrid search column detection and graceful degradation."""

    def test_hybrid_warning_logged_when_content_text_missing(self, mock_db_pool):
        """Test that warning is logged when content_text column is missing."""
        import cocosearch.search.query as query_module

        # Reset module state for test isolation
        query_module._has_content_text_column = True
        query_module._hybrid_warning_emitted = False

        # Mock check_column_exists to return False (no content_text column)
        with patch.object(
            query_module, "check_column_exists", return_value=False
        ) as mock_check:
            with patch.object(query_module, "logger") as mock_logger:
                with patch.object(
                    query_module, "code_to_embedding"
                ) as mock_embedding:
                    mock_embedding.eval.return_value = [0.1] * 1024

                    # Setup mock pool for the search query
                    pool, cursor, conn = mock_db_pool(results=[])
                    with patch.object(
                        query_module, "get_connection_pool", return_value=pool
                    ):
                        with patch.object(
                            query_module,
                            "get_table_name",
                            return_value="test_table",
                        ):
                            # Execute search to trigger hybrid column check
                            query_module.search("test query", "test_index")

                # Verify check_column_exists was called
                mock_check.assert_called_once_with("test_table", "content_text")

                # Verify warning was logged
                mock_logger.warning.assert_called_once()
                warning_msg = mock_logger.warning.call_args[0][0]
                assert "hybrid search" in warning_msg.lower()
                assert "content_text" in warning_msg

        # Verify flag was set
        assert query_module._has_content_text_column is False
        assert query_module._hybrid_warning_emitted is True

    def test_hybrid_warning_logged_only_once(self, mock_db_pool):
        """Test that hybrid warning is logged only once per session."""
        import cocosearch.search.query as query_module

        # Start with warning already emitted
        query_module._has_content_text_column = False
        query_module._hybrid_warning_emitted = True

        with patch.object(
            query_module, "check_column_exists", return_value=False
        ) as mock_check:
            with patch.object(query_module, "logger") as mock_logger:
                with patch.object(
                    query_module, "code_to_embedding"
                ) as mock_embedding:
                    mock_embedding.eval.return_value = [0.1] * 1024

                    pool, cursor, conn = mock_db_pool(results=[])
                    with patch.object(
                        query_module, "get_connection_pool", return_value=pool
                    ):
                        with patch.object(
                            query_module,
                            "get_table_name",
                            return_value="test_table",
                        ):
                            # Execute search multiple times
                            query_module.search("test query", "test_index")
                            query_module.search("another query", "test_index")

                # check_column_exists should not be called when flag already set
                mock_check.assert_not_called()

                # Warning should not be logged again
                mock_logger.warning.assert_not_called()

    def test_no_warning_when_content_text_exists(self, mock_db_pool):
        """Test that no warning is logged when content_text column exists."""
        import cocosearch.search.query as query_module

        # Reset module state
        query_module._has_content_text_column = True
        query_module._hybrid_warning_emitted = False

        # Mock check_column_exists to return True (column exists)
        with patch.object(
            query_module, "check_column_exists", return_value=True
        ) as mock_check:
            with patch.object(query_module, "logger") as mock_logger:
                with patch.object(
                    query_module, "code_to_embedding"
                ) as mock_embedding:
                    mock_embedding.eval.return_value = [0.1] * 1024

                    pool, cursor, conn = mock_db_pool(results=[])
                    with patch.object(
                        query_module, "get_connection_pool", return_value=pool
                    ):
                        with patch.object(
                            query_module,
                            "get_table_name",
                            return_value="test_table",
                        ):
                            query_module.search("test query", "test_index")

                # check_column_exists should be called
                mock_check.assert_called_once()

                # No warning should be logged
                mock_logger.warning.assert_not_called()

        # Flag should remain True
        assert query_module._has_content_text_column is True
        assert query_module._hybrid_warning_emitted is False

    def test_search_continues_when_hybrid_columns_missing(self, mock_db_pool):
        """Test that search works even when content_text column is missing."""
        import cocosearch.search.query as query_module

        # Reset module state
        query_module._has_content_text_column = True
        query_module._hybrid_warning_emitted = False

        # Sample search results (without content_text - pre-v1.7 schema)
        search_results = [
            ("/path/to/file.py", 0, 100, 0.95, "function", "main", "python"),
        ]

        pool, cursor, conn = mock_db_pool(results=search_results)

        with patch.object(query_module, "check_column_exists", return_value=False):
            with patch.object(query_module, "code_to_embedding") as mock_embedding:
                mock_embedding.eval.return_value = [0.1] * 1024
                with patch.object(
                    query_module, "get_connection_pool", return_value=pool
                ):
                    with patch.object(
                        query_module, "get_table_name", return_value="test_table"
                    ):
                        # Should complete without error
                        results = query_module.search("test query", "test_index")

        # Search should return results even though hybrid column is missing
        assert len(results) == 1
        assert results[0].filename == "/path/to/file.py"
        assert results[0].score == 0.95
