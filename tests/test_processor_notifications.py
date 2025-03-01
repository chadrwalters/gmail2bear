"""Tests for the processor module's notification behavior."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from gmail2bear.processor import EmailProcessor


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = MagicMock()
    config.loaded = True
    config.get_sender_email.return_value = "test@example.com"
    config.get_poll_interval.return_value = 1
    config.should_show_notifications.return_value = True
    config.get_notification_sound.return_value = "default"
    config.should_monitor_network.return_value = False
    config.should_archive_emails.return_value = False
    config.get_tags.return_value = ["test"]
    config.get_note_title_template.return_value = "{subject}"
    config.get_note_body_template.return_value = "{body}"
    return config


@pytest.fixture
def mock_state_manager():
    """Create a mock state manager."""
    state_manager = MagicMock()
    state_manager.get_processed_ids.return_value = []
    state_manager.is_processed.return_value = False
    return state_manager


@pytest.fixture
def mock_bear_client():
    """Create a mock Bear client."""
    bear_client = MagicMock()
    bear_client.create_note.return_value = True
    return bear_client


@pytest.fixture
def mock_gmail_client():
    """Create a mock Gmail client."""
    gmail_client = MagicMock()
    gmail_client.get_emails_from_sender.return_value = [
        {
            "id": "test_id",
            "subject": "Test Subject",
            "body": "Test Body",
            "date": "2023-01-01 12:00:00",
            "sender": "test@example.com",
            "is_html": False,
        }
    ]
    return gmail_client


@pytest.fixture
def processor(mock_config, mock_state_manager, mock_bear_client, mock_gmail_client):
    """Create a processor with mocked dependencies."""
    # Create temporary files
    with tempfile.NamedTemporaryFile(
        delete=False
    ) as config_file, tempfile.NamedTemporaryFile(
        delete=False
    ) as credentials_file, tempfile.NamedTemporaryFile(
        delete=False
    ) as state_file, tempfile.NamedTemporaryFile(
        delete=False
    ) as token_file:
        config_path = config_file.name
        credentials_path = credentials_file.name
        state_path = state_file.name
        token_path = token_file.name

    # Create processor
    processor = EmailProcessor(
        config_path=config_path,
        credentials_path=credentials_path,
        state_path=state_path,
        token_path=token_path,
    )

    # Replace components with mocks
    processor.config = mock_config
    processor.state_manager = mock_state_manager
    processor.bear_client = mock_bear_client
    processor.gmail_client = mock_gmail_client
    processor.notification_manager = MagicMock()
    processor.credentials = MagicMock()

    yield processor

    # Clean up temporary files
    for path in [config_path, credentials_path, state_path, token_path]:
        if os.path.exists(path):
            os.unlink(path)


def test_process_emails_with_notification(processor):
    """Test that process_emails sends a notification when send_notification is True."""
    # Process emails with send_notification=True
    count = processor.process_emails(once=True, send_notification=True)

    # Verify that notification was sent
    assert count == 1
    processor.notification_manager.notify_new_emails.assert_called_once_with(1)


def test_process_emails_without_notification(processor):
    """Test that process_emails does not send a notification when send_notification is False."""
    # Process emails with send_notification=False
    count = processor.process_emails(once=True, send_notification=False)

    # Verify that notification was not sent
    assert count == 1
    processor.notification_manager.notify_new_emails.assert_not_called()


@patch("time.sleep", return_value=None)  # Patch sleep to avoid waiting
def test_run_service_notification(mock_sleep, processor):
    """Test that run_service sends only one notification per batch of emails."""
    # Set up the processor to exit after one iteration
    processor.running = True

    def set_running_false(*args, **kwargs):
        processor.running = False
        return 1  # Return 1 email processed

    # Mock process_emails to exit the loop after one iteration
    processor.process_emails = MagicMock(side_effect=set_running_false)

    # Run the service
    processor.run_service()

    # Verify that process_emails was called with send_notification=False
    processor.process_emails.assert_called_once_with(
        once=False, send_notification=False
    )

    # Verify that notification was sent exactly once from run_service
    processor.notification_manager.notify_new_emails.assert_called_once_with(1)
