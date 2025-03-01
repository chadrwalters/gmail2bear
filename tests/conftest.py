"""Pytest configuration file."""

import platform


def pytest_ignore_collect(collection_path, config):
    """Skip macOS-specific test files on non-macOS platforms."""
    if platform.system() != "Darwin":
        # Skip macOS-specific test files on non-macOS platforms
        if "test_bear.py" in str(collection_path) or "test_processor.py" in str(
            collection_path
        ):
            return True
    return False
