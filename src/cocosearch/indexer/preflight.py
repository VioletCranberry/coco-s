"""Infrastructure preflight checks for indexing.

Verifies PostgreSQL and Ollama are reachable before starting
the indexing pipeline, providing clear error messages on failure.
"""

import json
import urllib.request
import urllib.error

import psycopg

DEFAULT_OLLAMA_URL = "http://localhost:11434"


def check_infrastructure(
    db_url: str, ollama_url: str | None, embedding_model: str = "nomic-embed-text"
) -> None:
    """Check PostgreSQL and Ollama are reachable. Raises ConnectionError if not."""
    check_postgres(db_url)
    resolved_url = ollama_url or DEFAULT_OLLAMA_URL
    check_ollama(resolved_url)
    check_ollama_model(resolved_url, embedding_model)


def check_postgres(db_url: str) -> None:
    try:
        with psycopg.connect(db_url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
    except psycopg.OperationalError as e:
        raise ConnectionError(
            f"PostgreSQL is not reachable at {db_url.split('@')[-1].split('/')[0]}. "
            f"Start it with: docker compose up -d\n"
            f"Details: {e}"
        ) from e


def check_ollama(ollama_url: str) -> None:
    try:
        urllib.request.urlopen(ollama_url, timeout=3)  # noqa: S310
    except (urllib.error.URLError, OSError) as e:
        raise ConnectionError(
            f"Ollama is not reachable at {ollama_url}. "
            f"Start it with: docker compose up -d\n"
            f"Details: {e}"
        ) from e


def check_ollama_model(ollama_url: str, model: str) -> None:
    """Check that the required embedding model is available in Ollama."""
    try:
        response = urllib.request.urlopen(  # noqa: S310
            f"{ollama_url}/api/tags", timeout=5
        )
        data = json.loads(response.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return  # Server reachability already checked; skip if tags endpoint fails

    available = [m["name"].split(":")[0] for m in data.get("models", [])]
    if model not in available:
        raise ConnectionError(
            f"Embedding model '{model}' is not available in Ollama.\n"
            f"Pull it with: ollama pull {model}\n"
            f"Available models: {', '.join(available) or 'none'}"
        )
