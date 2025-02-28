"""Tests for the config module."""

import os
from unittest import mock

import pytest

from gmail2bear.config import Config


@pytest.fixture
def sample_config_file(tmp_path):
    """Create a sample configuration file."""
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "[gmail]\n"
        "sender_email = test@example.com\n"
        "poll_interval = 600\n"
        "\n"
        "[bear]\n"
        "note_title = Test: {subject}\n"
        "note_body = # {subject}\n\n{body}\n\n---\nFrom: {sender}\n"
        "tags = test,email\n"
        "\n"
        "[logging]\n"
        "level = DEBUG\n"
    )
    return str(config_file)


@pytest.fixture
def empty_config_file(tmp_path):
    """Create an empty configuration file."""
    config_file = tmp_path / "empty_config.ini"
    config_file.write_text("")
    return str(config_file)


def test_config_load_success(sample_config_file):
    """Test that Config loads a valid configuration file."""
    config = Config(sample_config_file)
    assert config.loaded is True


def test_config_load_nonexistent():
    """Test that Config handles nonexistent configuration file."""
    with mock.patch("gmail2bear.config.logger") as mock_logger:
        config = Config("nonexistent_file.ini")

    assert config.loaded is False
    mock_logger.error.assert_called_once_with(mock.ANY)


def test_config_get_sender_email(sample_config_file):
    """Test that Config returns the correct sender email."""
    config = Config(sample_config_file)
    assert config.get_sender_email() == "test@example.com"


def test_config_get_poll_interval(sample_config_file):
    """Test that Config returns the correct poll interval."""
    config = Config(sample_config_file)
    assert config.get_poll_interval() == 600


def test_config_get_note_title_template(sample_config_file):
    """Test that Config returns the correct note title template."""
    config = Config(sample_config_file)
    assert config.get_note_title_template() == "Test: {subject}"


def test_config_get_note_body_template(sample_config_file):
    """Test that Config returns the correct note body template."""
    config = Config(sample_config_file)
    expected = "# {subject}\n\n{body}\n\n---\nFrom: {sender}"
    assert config.get_note_body_template().startswith("# {subject}")


def test_config_get_tags(sample_config_file):
    """Test that Config returns the correct tags."""
    config = Config(sample_config_file)
    assert config.get_tags() == ["test", "email"]


def test_config_get_logging_level(sample_config_file):
    """Test that Config returns the correct logging level."""
    config = Config(sample_config_file)
    assert config.get_logging_level() == "DEBUG"


def test_config_missing_section(empty_config_file):
    """Test that Config handles missing sections."""
    config = Config(empty_config_file)

    with mock.patch("gmail2bear.config.logger") as mock_logger:
        assert config.get_sender_email() is None
        assert config.get_poll_interval() == 300
        assert config.get_note_title_template() == "Email: {subject}"
        assert "# {subject}" in config.get_note_body_template()
        assert config.get_tags() == ["email", "gmail"]
        assert config.get_logging_level() == "INFO"

    # Check that warnings were logged
    assert mock_logger.warning.called or mock_logger.error.called


def test_config_create_default(tmp_path):
    """Test that Config creates a default configuration file."""
    config_file = str(tmp_path / "new_config.ini")

    config = Config(config_file)
    assert config.loaded is False

    # Create default config
    assert config.create_default_config() is True

    # Check that file was created
    assert os.path.exists(config_file)

    # Load the new config
    new_config = Config(config_file)
    assert new_config.loaded is True

    # Check default values
    assert new_config.get_sender_email() == "example@gmail.com"
    assert new_config.get_poll_interval() == 300
    assert new_config.get_tags() == ["email", "gmail"]
