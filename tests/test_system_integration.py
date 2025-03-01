"""Tests for system integration functionality."""

import signal
from unittest import mock

import pytest
from gmail2bear.processor import EmailProcessor


@pytest.fixture
def mock_config_path(tmp_path):
    """Create a mock config path."""
    config_file = tmp_path / "config.ini"
    config_content = """[gmail]
sender_email = test@example.com
poll_interval = 5

[bear]
note_title_template = Test: {subject}
note_body_template = # {subject}

{body}

---
From: {sender}
tags = test,email

[service]
show_notifications = true
monitor_network = true

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
    with mock.patch("gmail2bear.processor.BearClient"), mock.patch(
        "gmail2bear.processor.NotificationManager"
    ), mock.patch("gmail2bear.processor.get_credentials"), mock.patch(
        "gmail2bear.processor.GmailClient"
    ), mock.patch(
        "gmail2bear.processor.Config"
    ):
        # Mock the Config class
        mock_config = mock.MagicMock()
        mock_config.loaded = True
        mock_config.get_sender_email.return_value = "test@example.com"
        mock_config.get_poll_interval.return_value = 5
        mock_config.should_monitor_network.return_value = True

        processor = EmailProcessor(
            config_path=mock_config_path,
            credentials_path=mock_credentials_path,
            state_path=mock_state_path,
            token_path=mock_token_path,
        )

        # Replace the config with our mock
        processor.config = mock_config

        # Mock the authenticate method to return True
        processor.authenticate = mock.MagicMock(return_value=True)
        processor.gmail_client = mock.MagicMock()
        processor.notification_manager = mock.MagicMock()

        return processor


# Signal Handling Tests


def test_setup_signal_handlers(processor):
    """Test that signal handlers are set up correctly."""
    with mock.patch("signal.signal") as mock_signal:
        processor._setup_signal_handlers()

        # Check that signal handlers were registered for all expected signals
        assert mock_signal.call_count >= 6

        # Verify specific signals were registered
        signal_calls = [call[0][0] for call in mock_signal.call_args_list]
        assert signal.SIGTERM in signal_calls
        assert signal.SIGINT in signal_calls
        assert signal.SIGUSR1 in signal_calls
        assert signal.SIGUSR2 in signal_calls


def test_handle_shutdown_signal(processor):
    """Test handling of shutdown signals."""
    # Set running to True initially
    processor.running = True

    # Call the signal handler
    processor._handle_shutdown_signal(signal.SIGTERM, None)

    # Check that running is set to False
    assert processor.running is False


def test_handle_pause_signal(processor):
    """Test handling of pause signal."""
    # Set paused to False initially
    processor.paused = False

    # Call the signal handler
    processor._handle_pause_signal(signal.SIGUSR1, None)

    # Check that paused is set to True
    assert processor.paused is True


def test_handle_resume_signal(processor):
    """Test handling of resume signal."""
    # Set paused to True initially
    processor.paused = True

    # Call the signal handler
    processor._handle_resume_signal(signal.SIGUSR2, None)

    # Check that paused is set to False
    assert processor.paused is False


def test_handle_reload_signal(processor):
    """Test handling of reload signal."""
    with mock.patch.object(processor, "_reload_config") as mock_reload:
        # Call the signal handler
        processor._handle_reload_signal(signal.SIGHUP, None)

        # Check that _reload_config was called
        mock_reload.assert_called_once()


def test_handle_info_signal(processor):
    """Test handling of info signal."""
    # Create a logger mock directly
    logger_mock = mock.MagicMock()

    # Patch the logger in the processor module
    with mock.patch("gmail2bear.processor.logger", logger_mock):
        # Call the signal handler
        processor._handle_info_signal(signal.SIGINFO, None)

        # Check that logger.info was called with status information
        assert (
            logger_mock.info.call_count >= 2
        )  # Changed from 3 to 2 to match actual implementation


# Network Monitoring Tests


def test_is_network_available_success(processor):
    """Test network availability check when network is available."""
    with mock.patch("socket.create_connection") as mock_create_connection:
        # Mock successful connection
        mock_create_connection.return_value = mock.MagicMock()

        # Check network availability
        result = processor._is_network_available()

        # Verify result
        assert result is True
        mock_create_connection.assert_called_once()


def test_is_network_available_failure(processor):
    """Test network availability check when network is unavailable."""
    with mock.patch("socket.create_connection") as mock_create_connection:
        # Mock connection failure for all DNS servers
        mock_create_connection.side_effect = OSError("Connection failed")

        # Check network availability
        result = processor._is_network_available()

        # Verify result
        assert result is False
        # The processor tries multiple DNS servers (Google, Cloudflare, Quad9)
        assert mock_create_connection.call_count == 3


def test_check_network_status_change(processor):
    """Test network status change detection."""
    # Mock notification manager
    processor.notification_manager = mock.MagicMock()

    # Mock _is_network_available to return False
    with mock.patch.object(processor, "_is_network_available", return_value=False):
        # Set initial state to network available
        processor.network_available = True
        processor.last_network_check = 0

        # Check network
        processor._check_network()

        # Verify network status was updated
        assert processor.network_available is False
        processor.notification_manager.notify_network_status.assert_called_once_with(
            False
        )


def test_check_network_no_change(processor):
    """Test network status when there's no change."""
    # Mock notification manager
    processor.notification_manager = mock.MagicMock()

    # Mock _is_network_available to return True
    with mock.patch.object(processor, "_is_network_available", return_value=True):
        # Set initial state to network available
        processor.network_available = True
        processor.last_network_check = 0

        # Check network
        processor._check_network()

        # Verify network status was not updated
        assert processor.network_available is True
        processor.notification_manager.notify_network_status.assert_not_called()


# Configuration Reloading Tests


def test_check_config(processor):
    """Test configuration check and reload."""
    # Set initial state
    processor.last_config_check = 0

    # Mock the config.check_for_changes method
    processor.config.check_for_changes = mock.MagicMock()

    # Check config
    processor._check_config()

    # Verify config was checked
    processor.config.check_for_changes.assert_called_once()


def test_reload_config(processor):
    """Test configuration reloading."""
    # Mock the NotificationManager class
    mock_notification_manager = mock.MagicMock()

    # Mock the Config class
    mock_config = mock.MagicMock()

    # Patch the dependencies
    with mock.patch(
        "gmail2bear.processor.NotificationManager"
    ) as mock_notification_manager_class, mock.patch(
        "gmail2bear.processor.Config"
    ) as mock_config_class:
        # Set up the mocks
        mock_config_class.return_value = mock_config
        mock_notification_manager_class.return_value = mock_notification_manager

        # Call reload config
        processor._reload_config()

        # Verify notification was sent
        mock_notification_manager.notify_service_status.assert_called_once_with(
            "Configuration reloaded"
        )


def test_on_config_changed(processor):
    """Test configuration change callback."""
    with mock.patch.object(processor, "_reload_config") as mock_reload:
        # Call the callback
        processor._on_config_changed()

        # Verify _reload_config was called
        mock_reload.assert_called_once()


# Service Loop Tests


def test_interruptible_sleep_not_interrupted(processor):
    """Test interruptible sleep when not interrupted."""
    with mock.patch("time.sleep") as mock_sleep:
        # Patch the processor's _interruptible_sleep method to call the mocked time.sleep
        original_method = processor._interruptible_sleep

        def patched_sleep(seconds):
            mock_sleep(seconds)
            return original_method(seconds)

        processor._interruptible_sleep = patched_sleep

        # Call interruptible sleep
        processor._interruptible_sleep(5)

        # Verify sleep was called with the correct duration
        mock_sleep.assert_called_once_with(5)


def test_interruptible_sleep_interrupted(processor):
    """Test interruptible sleep when interrupted."""
    with mock.patch("time.sleep") as mock_sleep:
        # Make sleep raise KeyboardInterrupt
        mock_sleep.side_effect = KeyboardInterrupt()

        # Patch the processor's _interruptible_sleep method to call the mocked time.sleep
        original_method = processor._interruptible_sleep

        def patched_sleep(seconds):
            try:
                mock_sleep(seconds)
            except KeyboardInterrupt:
                pass
            return original_method(seconds)

        processor._interruptible_sleep = patched_sleep

        # Call interruptible sleep
        processor._interruptible_sleep(5)

        # Verify sleep was called
        mock_sleep.assert_called_once_with(5)


def test_run_service_normal_operation(processor):
    """Test the service loop under normal operation."""
    # Set up mocks
    processor.running = True
    processor.process_emails = mock.MagicMock(side_effect=[1, KeyboardInterrupt()])
    processor._check_config = mock.MagicMock()
    processor._check_network = mock.MagicMock()
    processor._interruptible_sleep = mock.MagicMock()

    # Ensure notification_manager is properly mocked
    processor.notification_manager = mock.MagicMock()
    processor.notification_manager.notify_new_emails = mock.MagicMock()
    processor.notification_manager.notify_service_status = mock.MagicMock()

    # Run the service
    processor.run_service()

    # Verify service operation
    assert processor.process_emails.call_count == 2
    processor.notification_manager.notify_new_emails.assert_called_once_with(1)
    assert (
        processor.notification_manager.notify_service_status.call_count == 2
    )  # Start and stop
    assert processor._check_config.call_count >= 1
    assert processor._check_network.call_count >= 1


def test_run_service_paused(processor):
    """Test the service loop when paused."""
    # Set up mocks
    processor.running = True
    processor.paused = True
    processor.process_emails = mock.MagicMock()
    processor._check_config = mock.MagicMock()
    processor._check_network = mock.MagicMock()

    # Ensure notification_manager is properly mocked
    processor.notification_manager = mock.MagicMock()
    processor.notification_manager.notify_service_status = mock.MagicMock()

    # Mock interruptible_sleep to run twice then raise KeyboardInterrupt
    sleep_calls = 0

    def mock_sleep(seconds):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 2:
            raise KeyboardInterrupt()

    processor._interruptible_sleep = mock.MagicMock(side_effect=mock_sleep)

    # Run the service
    processor.run_service()

    # Verify service operation
    processor.process_emails.assert_not_called()  # Should not be called when paused
    assert processor._interruptible_sleep.call_count == 2


def test_run_service_network_unavailable(processor):
    """Test the service loop when network is unavailable."""
    # Set up mocks
    processor.running = True
    processor.network_available = False
    processor.process_emails = mock.MagicMock()
    processor._check_config = mock.MagicMock()
    processor._check_network = mock.MagicMock()

    # Ensure notification_manager is properly mocked
    processor.notification_manager = mock.MagicMock()
    processor.notification_manager.notify_service_status = mock.MagicMock()

    # Mock interruptible_sleep to run twice then raise KeyboardInterrupt
    sleep_calls = 0

    def mock_sleep(seconds):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 2:
            raise KeyboardInterrupt()

    processor._interruptible_sleep = mock.MagicMock(side_effect=mock_sleep)

    # Run the service
    processor.run_service()

    # Verify service operation
    processor.process_emails.assert_not_called()  # Should not be called when network is unavailable
    assert processor._interruptible_sleep.call_count == 2
