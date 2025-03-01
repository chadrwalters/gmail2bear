"""Tests for the Bear module."""

import platform
import urllib.parse
from unittest import mock

import pytest

from gmail2bear.bear import BearClient

# Skip all tests in this module on non-macOS platforms
pytestmark = pytest.mark.skipif(
    platform.system() != "Darwin", reason="Bear tests only run on macOS"
)


def test_bear_client_init():
    """Test that BearClient initializes correctly."""
    client = BearClient()
    assert client.base_url == "bear://x-callback-url"


def test_build_url():
    """Test that _build_url correctly builds a Bear URL."""
    client = BearClient()

    params = {"title": "Test Note", "text": "This is a test note", "tags": "test tag"}

    url = client._build_url("create", params)

    assert url.startswith("bear://x-callback-url/create?")
    assert "title=Test%20Note" in url
    assert "text=This%20is%20a%20test%20note" in url
    assert "tags=test%20tag" in url


def test_create_note_success():
    """Test that create_note successfully creates a note."""
    client = BearClient()

    with mock.patch("subprocess.run") as mock_run:
        # Mock successful subprocess run
        mock_run.return_value = mock.Mock(returncode=0)

        result = client.create_note(
            title="Test Note",
            body="This is a test note",
            tags=["test", "note"],
            id_suffix="123",
        )

    assert result is True
    mock_run.assert_called_once()

    # Check that the URL was correctly constructed
    call_args = mock_run.call_args[0][0]
    assert call_args[0] == "open"
    url = call_args[1]

    assert "bear://x-callback-url/create?" in url
    assert "title=Test%20Note" in url

    # Check that tags were added to the body
    decoded_text = urllib.parse.unquote(url.split("text=")[1].split("&")[0])
    assert "#test #note" in decoded_text
    assert "ID: 123" in decoded_text


def test_create_note_no_tags():
    """Test that create_note works without tags."""
    client = BearClient()

    with mock.patch("subprocess.run") as mock_run:
        # Mock successful subprocess run
        mock_run.return_value = mock.Mock(returncode=0)

        result = client.create_note(title="Test Note", body="This is a test note")

    assert result is True
    mock_run.assert_called_once()


def test_create_note_subprocess_error():
    """Test that create_note handles subprocess errors."""
    client = BearClient()

    with mock.patch("subprocess.run") as mock_run:
        # Mock subprocess error
        mock_run.side_effect = Exception("Subprocess error")

        with mock.patch("gmail2bear.bear.logger") as mock_logger:
            result = client.create_note(title="Test Note", body="This is a test note")

    assert result is False
    mock_logger.error.assert_called_once_with(mock.ANY)


def test_create_note_nonzero_return_code():
    """Test that create_note handles non-zero return codes."""
    client = BearClient()

    with mock.patch("subprocess.run") as mock_run:
        # Mock non-zero return code
        mock_run.return_value = mock.Mock(returncode=1, stderr="Error")

        with mock.patch("gmail2bear.bear.logger") as mock_logger:
            result = client.create_note(title="Test Note", body="This is a test note")

    assert result is False
    mock_logger.error.assert_called_once_with(mock.ANY)
