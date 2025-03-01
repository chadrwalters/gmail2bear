"""Tests for the processor module."""

from unittest import mock

import pytest
from gmail2bear.processor import EmailProcessor


@pytest.fixture
def mock_config_path(tmp_path):
    """Create a mock config path."""
    config_file = tmp_path / "config.ini"
    config_content = """[gmail]
sender_email = test@example.com
poll_interval = 60

[bear]
note_title_template = Test: {subject}
note_body_template = '''# {subject}

{body}

---
From: {sender}'''
tags = test,email

[logging]
level = DEBUG
"""
    config_file.write_text(config_content)
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
def mock_token_path(tmp_path):
    """Create a mock token path."""
    token_file = tmp_path / "token.pickle"
    return str(token_file)


@pytest.fixture
def processor(
    mock_config_path, mock_credentials_path, mock_state_path, mock_token_path
):
    """Create a processor with mock paths."""
    with mock.patch("gmail2bear.processor.BearClient") as mock_bear_client_class:
        # Set up the mock BearClient instance
        mock_bear_client = mock.MagicMock()
        mock_bear_client_class.return_value = mock_bear_client

        processor = EmailProcessor(
            config_path=mock_config_path,
            credentials_path=mock_credentials_path,
            state_path=mock_state_path,
            token_path=mock_token_path,
        )

        # Return the processor with the mocked BearClient
        return processor


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
        "labels": ["INBOX", "UNREAD"],
    }


def test_processor_init(
    processor, mock_config_path, mock_credentials_path, mock_state_path, mock_token_path
):
    """Test that EmailProcessor initializes correctly."""
    assert processor.config_path == mock_config_path
    assert processor.credentials_path == mock_credentials_path
    assert processor.state_path == mock_state_path
    assert processor.token_path == mock_token_path
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
        processor.credentials_path, processor.token_path, False, False, "Gmail to Bear"
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
    # Mock the loaded property
    with mock.patch.object(processor.config, "loaded", False, create=True):
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

    # Mock the loaded property
    with mock.patch.object(processor.config, "loaded", True, create=True):
        with mock.patch.object(
            processor, "_process_single_email", return_value=True
        ) as mock_process:
            with mock.patch.object(
                processor.config, "get_sender_email", return_value="test@example.com"
            ):
                result = processor.process_emails(once=True)

    assert result == 1
    mock_process.assert_called_once_with(mock_email)


def test_process_emails_no_emails(processor):
    """Test that process_emails handles no emails."""
    # Set up mocks
    processor.gmail_client = mock.Mock()
    processor.gmail_client.get_emails_from_sender.return_value = []

    # Mock the loaded property
    with mock.patch.object(processor.config, "loaded", True, create=True):
        with mock.patch.object(
            processor.config, "get_sender_email", return_value="test@example.com"
        ):
            with mock.patch("gmail2bear.processor.logger") as mock_logger:
                result = processor.process_emails(once=True)

    assert result == 0
    mock_logger.info.assert_any_call("No new emails to process")


def test_process_single_email_success(processor, mock_email):
    """Test that _process_single_email successfully processes an email."""
    # Set up mocks
    processor.gmail_client = mock.Mock()
    processor.bear_client.create_note.return_value = True

    with mock.patch.object(
        processor, "_format_note_title", return_value="Test Title"
    ) as mock_title:
        with mock.patch.object(
            processor, "_format_note_body", return_value="Test Body"
        ) as mock_body:
            with mock.patch.object(
                processor.config, "get_tags", return_value=["test", "email"]
            ):
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
        with mock.patch.object(
            processor, "_format_note_title", return_value="Test Title"
        ):
            with mock.patch.object(
                processor, "_format_note_body", return_value="Test Body"
            ):
                with mock.patch.object(
                    processor.config, "get_tags", return_value=["test", "email"]
                ):
                    result = processor._process_single_email(mock_email)

    assert result is False
    mock_logger.error.assert_called_once_with(mock.ANY)
    assert not processor.state_manager.is_processed(mock_email["id"])


def test_format_note_title(processor, mock_email):
    """Test that _format_note_title correctly formats the note title."""
    # Test with simple template
    with mock.patch.object(
        processor.config,
        "get_note_title_template",
        return_value="Email: {subject} from {sender}",
    ):
        title = processor._format_note_title(mock_email)

    assert title == "Email: Test Subject from sender@example.com"

    # Test with date formatting
    with mock.patch.object(
        processor.config,
        "get_note_title_template",
        return_value="Email: {subject} on {date:%Y-%m-%d}",
    ):
        title = processor._format_note_title(mock_email)

    assert "Email: Test Subject on 2023-01-01" in title


def test_format_note_body(processor, mock_email):
    """Test that _format_note_body correctly formats the note body."""
    # Test with simple template
    template = "# {subject}\n\nFrom: {sender}\nDate: {date}\n\n{body}\n\nID: {id}"

    with mock.patch.object(
        processor.config, "get_note_body_template", return_value=template
    ):
        body = processor._format_note_body(mock_email)

    assert "# Test Subject" in body
    assert "From: sender@example.com" in body
    assert "Date: 2023-01-01 12:00:00" in body or "Date: 2023-01-01" in body
    assert "Test body" in body
    assert "ID: 12345" in body

    # Test with date formatting
    template = (
        "# {subject}\n\nFrom: {sender}\nDate: {date:%Y-%m-%d}\n\n{body}\n\nID: {id}"
    )

    with mock.patch.object(
        processor.config, "get_note_body_template", return_value=template
    ):
        body = processor._format_note_body(mock_email)

    assert "# Test Subject" in body
    assert "From: sender@example.com" in body
    assert "Date: 2023-01-01" in body
    assert "Test body" in body
    assert "ID: 12345" in body
