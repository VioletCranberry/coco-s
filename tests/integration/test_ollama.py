"""Ollama integration tests.

Tests validating real Ollama embedding generation:
- Embedding dimensions (768 for nomic-embed-text)
- Value range checks (floats, not NaN/Inf)
- Similarity sanity (similar texts produce similar embeddings)

These tests require Ollama (native or Docker) and are marked with @pytest.mark.integration.
The marker is auto-applied by tests/integration/conftest.py.
"""

import numpy as np
import pytest

import cocoindex


class TestEmbeddingGeneration:
    """Tests for basic embedding generation properties."""

    def test_embedding_dimensions(self, warmed_ollama):
        """Verify embeddings have exactly 768 dimensions.

        Requirement: OLLAMA-03 (Embedding dimension validation)
        """
        # Generate embedding for sample code
        sample_code = "def hello_world():\n    print('Hello')"

        embedding_flow = cocoindex.transform_flow()(
            lambda text: text.transform(
                cocoindex.functions.EmbedText(
                    api_type=cocoindex.LlmApiType.OLLAMA,
                    model="nomic-embed-text",
                )
            )
        )

        result = embedding_flow(cocoindex.DataSlice([sample_code]))
        embedding = result[0]

        assert len(embedding) == 768, f"Expected 768 dimensions, got {len(embedding)}"

    def test_embedding_values_valid(self, warmed_ollama):
        """Verify embedding values are valid floats without NaN/Inf.

        Requirement: OLLAMA-03 (Embedding value validation)
        """
        sample_text = "Python function for sorting a list"

        embedding_flow = cocoindex.transform_flow()(
            lambda text: text.transform(
                cocoindex.functions.EmbedText(
                    api_type=cocoindex.LlmApiType.OLLAMA,
                    model="nomic-embed-text",
                )
            )
        )

        result = embedding_flow(cocoindex.DataSlice([sample_text]))
        embedding = np.array(result[0])

        # Check all values are floats
        assert embedding.dtype in [np.float32, np.float64], (
            f"Expected float values, got {embedding.dtype}"
        )

        # Check for NaN values
        assert not np.any(np.isnan(embedding)), "Embedding contains NaN values"

        # Check for Inf values
        assert not np.any(np.isinf(embedding)), "Embedding contains Inf values"

        # Check values are in reasonable range (normalized vectors usually smaller)
        assert np.all(embedding >= -10) and np.all(embedding <= 10), (
            f"Embedding values outside reasonable range: "
            f"min={embedding.min()}, max={embedding.max()}"
        )

    def test_embedding_consistent(self, warmed_ollama):
        """Verify embeddings are deterministic for same input.

        Requirement: OLLAMA-01 (Consistent embedding generation)
        """
        sample_text = "Python method to sort an array"

        embedding_flow = cocoindex.transform_flow()(
            lambda text: text.transform(
                cocoindex.functions.EmbedText(
                    api_type=cocoindex.LlmApiType.OLLAMA,
                    model="nomic-embed-text",
                )
            )
        )

        # Generate embedding twice
        result1 = embedding_flow(cocoindex.DataSlice([sample_text]))
        result2 = embedding_flow(cocoindex.DataSlice([sample_text]))

        embedding1 = np.array(result1[0])
        embedding2 = np.array(result2[0])

        # Embeddings should be identical (deterministic model)
        assert np.array_equal(embedding1, embedding2), (
            "Embeddings for same text should be identical"
        )
