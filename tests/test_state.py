"""Tests for the state module."""

import json
import os
from unittest import mock

import pytest
from gmail2bear.state import StateManager


@pytest.fixture
def state_file_path(tmp_path):
    """Create a path for a state file."""
    return str(tmp_path / "state.json")


@pytest.fixture
def existing_state_file(tmp_path):
    """Create an existing state file with some processed IDs."""
    state_file = tmp_path / "existing_state.json"
    state_data = {"processed_ids": ["id1", "id2", "id3"]}
    state_file.write_text(json.dumps(state_data))
    return str(state_file)


@pytest.fixture
def corrupt_state_file(tmp_path):
    """Create a corrupt state file."""
    state_file = tmp_path / "corrupt_state.json"
    state_file.write_text("not valid json")
    return str(state_file)


def test_state_manager_init_new(state_file_path):
    """Test that StateManager initializes with a new state file."""
    with mock.patch("gmail2bear.state.logger") as mock_logger:
        state_manager = StateManager(state_file_path)

    assert os.path.exists(state_file_path)
    assert state_manager.processed_ids == set()
    mock_logger.debug.assert_called()


def test_state_manager_init_existing(existing_state_file):
    """Test that StateManager loads an existing state file."""
    state_manager = StateManager(existing_state_file)

    assert state_manager.processed_ids == {"id1", "id2", "id3"}


def test_state_manager_init_corrupt(corrupt_state_file):
    """Test that StateManager handles a corrupt state file."""
    with mock.patch("gmail2bear.state.logger") as mock_logger:
        state_manager = StateManager(corrupt_state_file)

    assert state_manager.processed_ids == set()
    mock_logger.error.assert_called_once_with(mock.ANY)


def test_state_manager_is_processed(existing_state_file):
    """Test that StateManager correctly checks if an email is processed."""
    state_manager = StateManager(existing_state_file)

    assert state_manager.is_processed("id1") is True
    assert state_manager.is_processed("id2") is True
    assert state_manager.is_processed("unknown_id") is False


def test_state_manager_mark_as_processed(state_file_path):
    """Test that StateManager correctly marks an email as processed."""
    state_manager = StateManager(state_file_path)

    assert state_manager.is_processed("new_id") is False

    state_manager.mark_as_processed("new_id")

    assert state_manager.is_processed("new_id") is True

    # Check that the state was saved to the file
    with open(state_file_path) as f:
        state_data = json.load(f)
        assert "new_id" in state_data["processed_ids"]


def test_state_manager_get_processed_ids(existing_state_file):
    """Test that StateManager returns the correct list of processed IDs."""
    state_manager = StateManager(existing_state_file)

    processed_ids = state_manager.get_processed_ids()

    assert isinstance(processed_ids, list)
    assert set(processed_ids) == {"id1", "id2", "id3"}


def test_state_manager_clear_state(existing_state_file):
    """Test that StateManager correctly clears the state."""
    state_manager = StateManager(existing_state_file)

    assert len(state_manager.processed_ids) > 0

    state_manager.clear_state()

    assert len(state_manager.processed_ids) == 0

    # Check that the state was saved to the file
    with open(existing_state_file) as f:
        state_data = json.load(f)
        assert state_data["processed_ids"] == []
