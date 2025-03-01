"""Pytest configuration file."""

import os
import platform
import sys

import pytest


def pytest_ignore_collect(collection_path, config):
    """Skip macOS-specific test files on non-macOS platforms."""
    # Print debug information
    print(f"Platform: {platform.system()}")
    print(f"Python version: {sys.version}")
    print(f"Checking path: {collection_path}")

    if platform.system() != "Darwin":
        # Skip macOS-specific test files on non-macOS platforms
        if "test_bear.py" in str(collection_path) or "test_processor.py" in str(
            collection_path
        ):
            print(f"Skipping macOS-specific test file: {collection_path}")
            return True
    return False


def pytest_configure(config):
    """Print environment information at the start of the test run."""
    print("\n=== Environment Information ===")
    print(f"Platform: {platform.system()}")
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    print("============================\n")


def pytest_collection_modifyitems(config, items):
    """Skip macOS-specific tests on non-macOS platforms."""
    if platform.system() != "Darwin":
        skip_macos = pytest.mark.skip(reason="Test requires macOS")
        for item in items:
            if "test_bear" in item.nodeid or "test_processor" in item.nodeid:
                item.add_marker(skip_macos)
                print(f"Adding skip marker to: {item.nodeid}")
