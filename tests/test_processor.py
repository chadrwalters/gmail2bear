"""Tests for the processor module."""

import os
from unittest import mock

import pytest

from gmail2bear.processor import EmailProcessor


@pytest.fixture
def mock_config_path(tmp_path):
    """Create a mock config path."""
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "[gmail]\n"
        "sender_email = test@example.com\n"
        "poll_interval = 60\n"
        "\n"
        "[bear]\n"
        "note_title = Test: {subject}\n"
        "note_body = # {subject}\n\n{body}\n\n---\nFrom: {sender}\n"
        "tags = test,email\n"
    )
    return str(config_file)


@pytest.fixture
def mock_credentials_path(tmp_path):
    """Create a mock credentials path."""
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text('{"installed": {"client_id": "test"}}')
    return str(credentials_file)


@pytest.fixture
def mock_state_path(tmp_path):
    """Create a mock state path."""
    state_file = tmp_path / "state.json"
    return str(state_file)


@pytest.fixture
def processor(mock_config_path, mock_credentials_path, mock_state_path):
    """Create a processor with mock paths."""
    return EmailProcessor(
        config_path=mock_config_path,
        credentials_path=mock_credentials_path,
        state_path=mock_state_path
    )


@pytest.fixture
def mock_email():
    """Create a mock email dictionary."""
    return {
        "id": "12345",
        "subject": "Test Subject",
        "sender": "sender@example.com",
        "date": "2023-01-01 12:00:00",
        "body": "Test body",
        "is_html": False,
        "labels": ["INBOX", "UNREAD"]
    }


def test_processor_init(processor, mock_config_path, mock_credentials_path, mock_state_path):
    """Test that EmailProcessor initializes correctly."""
    assert processor.config_path == mock_config_path
    assert processor.credentials_path == mock_credentials_path
    assert processor.state_path == mock_state_path
    assert processor.config is not None
    assert processor.state_manager is not None
    assert processor.bear_client is not None
    assert processor.gmail_client is None


def test_authenticate_success(processor):
    """Test that authenticate successfully authenticates with Gmail API."""
    with mock.patch("gmail2bear.processor.get_credentials") as mock_get_credentials:
        mock_get_credentials.return_value = mock.Mock()

        with mock.patch("gmail2bear.processor.GmailClient") as mock_gmail_client:
            mock_gmail_client.return_value = mock.Mock()

            result = processor.authenticate()

    assert result is True
    assert processor.gmail_client is not None
    mock_get_credentials.assert_called_once_with(
        processor.credentials_path,
        processor.token_path,
        False
    )


def test_authenticate_failure(processor):
    """Test that authenticate handles authentication failures."""
    with mock.patch("gmail2bear.processor.get_credentials") as mock_get_credentials:
        mock_get_credentials.side_effect = Exception("Authentication failed")

        with mock.patch("gmail2bear.processor.logger") as mock_logger:
            result = processor.authenticate()

    assert result is False
    assert processor.gmail_client is None
    mock_logger.error.assert_called_once_with(mock.ANY)


def test_process_emails_no_config(processor):
    """Test that process_emails handles missing configuration."""
    processor.config.loaded = False

    with mock.patch("gmail2bear.processor.logger") as mock_logger:
        result = processor.process_emails()

    assert result == 0
    mock_logger.error.assert_called_once_with(mock.ANY)


def test_process_emails_no_gmail_client(processor):
    """Test that process_emails handles missing Gmail client."""
    processor.gmail_client = None

    with mock.patch("gmail2bear.processor.logger") as mock_logger:
        result = processor.process_emails()

    assert result == 0
    mock_logger.error.assert_called_once_with(mock.ANY)


def test_process_emails_no_sender_email(processor):
    """Test that process_emails handles missing sender email."""
    processor.gmail_client = mock.Mock()

    with mock.patch("gmail2bear.processor.logger") as mock_logger:
        with mock.patch.object(processor.config, "get_sender_email", return_value=None):
            result = processor.process_emails()

    assert result == 0
    mock_logger.error.assert_called_once_with(mock.ANY)


def test_process_emails_success(processor, mock_email):
    """Test that process_emails successfully processes emails."""
    # Set up mocks
    processor.gmail_client = mock.Mock()
    processor.gmail_client.get_emails_from_sender.return_value = [mock_email]

    with mock.patch.object(processor, "_process_single_email", return_value=True) as mock_process:
        result = processor.process_emails(once=True)

    assert result == 1
    mock_process.assert_called_once_with(mock_email)


def test_process_emails_no_emails(processor):
    """Test that process_emails handles no emails."""
    # Set up mocks
    processor.gmail_client = mock.Mock()
    processor.gmail_client.get_emails_from_sender.return_value = []

    with mock.patch("gmail2bear.processor.logger") as mock_logger:
        result = processor.process_emails(once=True)

    assert result == 0
    mock_logger.info.assert_any_call("No new emails to process")


def test_process_single_email_success(processor, mock_email):
    """Test that _process_single_email successfully processes an email."""
    # Set up mocks
    processor.gmail_client = mock.Mock()
    processor.bear_client.create_note.return_value = True

    with mock.patch.object(processor, "_format_note_title", return_value="Test Title") as mock_title:
        with mock.patch.object(processor, "_format_note_body", return_value="Test Body") as mock_body:
            result = processor._process_single_email(mock_email)

    assert result is True
    mock_title.assert_called_once_with(mock_email)
    mock_body.assert_called_once_with(mock_email)
    processor.bear_client.create_note.assert_called_once()
    processor.gmail_client.mark_as_read.assert_called_once_with(mock_email["id"])
    assert processor.state_manager.is_processed(mock_email["id"])


def test_process_single_email_already_processed(processor, mock_email):
    """Test that _process_single_email skips already processed emails."""
    # Mark the email as already processed
    processor.state_manager.mark_as_processed(mock_email["id"])

    with mock.patch("gmail2bear.processor.logger") as mock_logger:
        result = processor._process_single_email(mock_email)

    assert result is False
    mock_logger.debug.assert_called_once_with(mock.ANY)


def test_process_single_email_bear_failure(processor, mock_email):
    """Test that _process_single_email handles Bear note creation failures."""
    # Set up mocks
    processor.bear_client.create_note.return_value = False

    with mock.patch("gmail2bear.processor.logger") as mock_logger:
        result = processor._process_single_email(mock_email)

    assert result is False
    mock_logger.error.assert_called_once_with(mock.ANY)
    assert not processor.state_manager.is_processed(mock_email["id"])


def test_format_note_title(processor, mock_email):
    """Test that _format_note_title correctly formats the note title."""
    with mock.patch.object(processor.config, "get_note_title_template", return_value="Email: {subject} from {sender}"):
        title = processor._format_note_title(mock_email)

    assert title == "Email: Test Subject from sender@example.com"


def test_format_note_body(processor, mock_email):
    """Test that _format_note_body correctly formats the note body."""
    template = "# {subject}\n\nFrom: {sender}\nDate: {date}\n\n{body}\n\nID: {email_id}"

    with mock.patch.object(processor.config, "get_note_body_template", return_value=template):
        body = processor._format_note_body(mock_email)

    assert "# Test Subject" in body
    assert "From: sender@example.com" in body
    assert "Date: 2023-01-01 12:00:00" in body
    assert "Test body" in body
    assert "ID: 12345" in body
