"""Verify pytest setup is working correctly."""


def test_pytest_works():
    """Simple test to verify pytest runs."""
    assert True


def test_tmp_codebase_fixture(tmp_codebase):
    """Verify tmp_codebase fixture works."""
    assert tmp_codebase.exists()
    assert (tmp_codebase / "main.py").exists()
