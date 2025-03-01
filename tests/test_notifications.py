"""Tests for the notifications module."""

from unittest import mock

import pytest

from gmail2bear.notifications import NotificationManager  # type: ignore


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = mock.MagicMock()
    config.should_show_notifications.return_value = True
    config.get_notification_sound.return_value = "default"
    config.get_notification_timeout.return_value = 5
    return config


@pytest.fixture
def notification_manager(mock_config):
    """Create a notification manager with mock config."""
    with mock.patch("platform.system", return_value="Darwin"):
        with mock.patch("gmail2bear.notifications.pync", mock.MagicMock()):
            return NotificationManager(config=mock_config)


def test_init_with_config(mock_config):
    """Test initialization with configuration."""
    with mock.patch("platform.system", return_value="Darwin"):
        with mock.patch("gmail2bear.notifications.pync", mock.MagicMock()):
            manager = NotificationManager(config=mock_config)

            assert manager.app_name == "Gmail to Bear"
            assert manager.config == mock_config
            assert manager.enabled is True
            assert manager.show_notifications is True
            assert manager.notification_sound == "default"
            assert manager.notification_timeout == 5


def test_init_without_config():
    """Test initialization without configuration."""
    with mock.patch("platform.system", return_value="Darwin"):
        with mock.patch("gmail2bear.notifications.pync", mock.MagicMock()):
            manager = NotificationManager()

            assert manager.app_name == "Gmail to Bear"
            assert manager.config is None
            assert manager.enabled is True
            assert manager.show_notifications is True
            assert manager.notification_sound == "default"
            assert manager.notification_timeout == 5


def test_is_supported_macos():
    """Test platform detection on macOS."""
    with mock.patch("platform.system", return_value="Darwin"):
        with mock.patch("gmail2bear.notifications.pync", mock.MagicMock()):
            manager = NotificationManager()
            assert manager.enabled is True


def test_is_supported_non_macos():
    """Test platform detection on non-macOS."""
    with mock.patch("platform.system", return_value="Linux"):
        manager = NotificationManager()
        assert manager.enabled is False


def test_is_supported_macos_no_pync():
    """Test platform detection on macOS without pync."""
    with mock.patch("platform.system", return_value="Darwin"):
        with mock.patch("gmail2bear.notifications.pync", None):
            manager = NotificationManager()
            assert manager.enabled is False


def test_send_notification_success(notification_manager):
    """Test successful notification sending."""
    with mock.patch("gmail2bear.notifications.pync.notify") as mock_notify:
        # Send notification
        result = notification_manager.send_notification(
            title="Test Title",
            message="Test Message",
            subtitle="Test Subtitle",
            sound="Ping",
        )

        # Verify result
        assert result is True
        mock_notify.assert_called_once_with(
            "Test Message",
            title="Test Title",
            subtitle="Test Subtitle",
            sound="Ping",
        )


def test_send_notification_disabled(notification_manager):
    """Test notification sending when disabled."""
    # Disable notifications
    notification_manager.show_notifications = False

    with mock.patch("gmail2bear.notifications.pync.notify") as mock_notify:
        # Send notification
        result = notification_manager.send_notification(
            title="Test Title", message="Test Message"
        )

        # Verify result
        assert result is False
        mock_notify.assert_not_called()


def test_send_notification_not_supported(mock_config):
    """Test notification sending on unsupported platform."""
    with mock.patch("platform.system", return_value="Linux"):
        manager = NotificationManager(config=mock_config)

        with mock.patch("gmail2bear.notifications.pync.notify") as mock_notify:
            # Send notification
            result = manager.send_notification(
                title="Test Title", message="Test Message"
            )

            # Verify result
            assert result is False
            mock_notify.assert_not_called()


def test_send_notification_error(notification_manager):
    """Test notification sending with error."""
    with mock.patch("gmail2bear.notifications.pync.notify") as mock_notify:
        # Mock pync error
        mock_notify.side_effect = Exception("Test error")

        # Send notification
        result = notification_manager.send_notification(
            title="Test Title", message="Test Message"
        )

        # Verify result
        assert result is False
        mock_notify.assert_called_once()


def test_send_notification_invalid_sound(notification_manager):
    """Test notification sending with invalid sound."""
    with mock.patch("gmail2bear.notifications.pync.notify") as mock_notify:
        # Send notification with invalid sound
        result = notification_manager.send_notification(
            title="Test Title", message="Test Message", sound="InvalidSound"
        )

        # Verify result
        assert result is True
        mock_notify.assert_called_once()

        # Verify the sound was changed to default
        args, kwargs = mock_notify.call_args
        assert kwargs["sound"] == "default"


def test_notify_new_emails(notification_manager):
    """Test notification for new emails."""
    with mock.patch.object(notification_manager, "send_notification") as mock_send:
        # Mock successful notification
        mock_send.return_value = True

        # Send notification for 1 email
        result = notification_manager.notify_new_emails(1)

        # Verify result
        assert result is True
        mock_send.assert_called_once()

        # Verify arguments - use positional args
        args = mock_send.call_args[0]
        assert args[0] == "Gmail to Bear"  # title
        assert args[1] == "1 new email processed"  # message
        assert args[2] == "New notes created in Bear"  # subtitle


def test_notify_new_emails_multiple(notification_manager):
    """Test notification for multiple new emails."""
    with mock.patch.object(notification_manager, "send_notification") as mock_send:
        # Mock successful notification
        mock_send.return_value = True

        # Send notification for 3 emails
        result = notification_manager.notify_new_emails(3)

        # Verify result
        assert result is True
        mock_send.assert_called_once()

        # Verify arguments - use positional args
        args = mock_send.call_args[0]
        assert args[0] == "Gmail to Bear"  # title
        assert args[1] == "3 new emails processed"  # message
        assert args[2] == "New notes created in Bear"  # subtitle


def test_notify_new_emails_zero(notification_manager):
    """Test notification for zero new emails."""
    with mock.patch.object(notification_manager, "send_notification") as mock_send:
        # Send notification for 0 emails
        result = notification_manager.notify_new_emails(0)

        # Verify result
        assert result is False
        mock_send.assert_not_called()


def test_notify_error(notification_manager):
    """Test error notification."""
    with mock.patch.object(notification_manager, "send_notification") as mock_send:
        # Mock successful notification
        mock_send.return_value = True

        # Send error notification
        result = notification_manager.notify_error("Test error message")

        # Verify result
        assert result is True
        mock_send.assert_called_once()

        # Verify arguments - use positional args
        args = mock_send.call_args[0]
        assert args[0] == "Gmail to Bear - Error"  # title
        assert "Test error message" in args[1]  # message


def test_notify_service_status(notification_manager):
    """Test service status notification."""
    with mock.patch.object(notification_manager, "send_notification") as mock_send:
        # Mock successful notification
        mock_send.return_value = True

        # Send service status notification
        result = notification_manager.notify_service_status("Service started")

        # Verify result
        assert result is True
        mock_send.assert_called_once()

        # Verify arguments - use positional args
        args = mock_send.call_args[0]
        assert args[0] == "Gmail to Bear - Service"  # title
        assert "Service started" in args[1]  # message


def test_notify_network_status_connected(notification_manager):
    """Test network connected notification."""
    with mock.patch.object(notification_manager, "send_notification") as mock_send:
        # Mock successful notification
        mock_send.return_value = True

        # Send network connected notification
        result = notification_manager.notify_network_status(True)

        # Verify result
        assert result is True
        mock_send.assert_called_once()

        # Verify arguments - use positional args
        args = mock_send.call_args[0]
        assert args[0] == "Gmail to Bear - Network"  # title
        assert "connection restored" in args[1].lower()  # message


def test_notify_network_status_disconnected(notification_manager):
    """Test network disconnected notification."""
    with mock.patch.object(notification_manager, "send_notification") as mock_send:
        # Mock successful notification
        mock_send.return_value = True

        # Send network disconnected notification
        result = notification_manager.notify_network_status(False)

        # Verify result
        assert result is True
        mock_send.assert_called_once()

        # Verify arguments - use positional args
        args = mock_send.call_args[0]
        assert args[0] == "Gmail to Bear - Network"  # title
        assert "connection lost" in args[1].lower()  # message


def test_notify_system_event_sleep(notification_manager):
    """Test system sleep event notification."""
    with mock.patch.object(notification_manager, "send_notification") as mock_send:
        # Mock successful notification
        mock_send.return_value = True

        # Send sleep event notification
        result = notification_manager.notify_system_event("sleep")

        # Verify result
        assert result is True
        mock_send.assert_called_once()

        # Verify arguments - use positional args
        args = mock_send.call_args[0]
        assert args[0] == "Gmail to Bear - System"  # title
        assert "sleep" in args[1].lower()  # message


def test_notify_system_event_wake(notification_manager):
    """Test system wake event notification."""
    with mock.patch.object(notification_manager, "send_notification") as mock_send:
        # Mock successful notification
        mock_send.return_value = True

        # Send wake event notification
        result = notification_manager.notify_system_event("wake")

        # Verify result
        assert result is True
        mock_send.assert_called_once()

        # Verify arguments - use positional args
        args = mock_send.call_args[0]
        assert args[0] == "Gmail to Bear - System"  # title
        assert "waking up" in args[1].lower()  # message


def test_notify_system_event_other(notification_manager):
    """Test other system event notification."""
    with mock.patch.object(notification_manager, "send_notification") as mock_send:
        # Mock successful notification
        mock_send.return_value = True

        # Send other event notification
        result = notification_manager.notify_system_event("other", "details")

        # Verify result
        assert result is True
        mock_send.assert_called_once()

        # Verify arguments - use positional args
        args = mock_send.call_args[0]
        assert args[0] == "Gmail to Bear - System"  # title
        assert "other" in args[1].lower()  # message
        assert "details" in args[1].lower()  # message


# Edge Case Tests


def test_send_notification_long_title(notification_manager):
    """Test notification with extremely long title."""
    with mock.patch("gmail2bear.notifications.pync.notify") as mock_notify:
        # Create a very long title (5000 characters)
        long_title = "A" * 5000

        # Send notification
        result = notification_manager.send_notification(
            title=long_title,
            message="Test Message",
        )

        # Verify result
        assert result is True
        mock_notify.assert_called_once()

        # Verify the title was passed as is (pync should handle truncation if needed)
        args, kwargs = mock_notify.call_args
        assert kwargs["title"] == long_title


def test_send_notification_long_message(notification_manager):
    """Test notification with extremely long message."""
    with mock.patch("gmail2bear.notifications.pync.notify") as mock_notify:
        # Create a very long message (10000 characters)
        long_message = "B" * 10000

        # Send notification
        result = notification_manager.send_notification(
            title="Test Title",
            message=long_message,
        )

        # Verify result
        assert result is True
        mock_notify.assert_called_once()

        # Verify the message was passed as is
        args, kwargs = mock_notify.call_args
        assert args[0] == long_message


def test_send_notification_long_subtitle(notification_manager):
    """Test notification with extremely long subtitle."""
    with mock.patch("gmail2bear.notifications.pync.notify") as mock_notify:
        # Create a very long subtitle (3000 characters)
        long_subtitle = "C" * 3000

        # Send notification
        result = notification_manager.send_notification(
            title="Test Title",
            message="Test Message",
            subtitle=long_subtitle,
        )

        # Verify result
        assert result is True
        mock_notify.assert_called_once()

        # Verify the subtitle was passed as is
        args, kwargs = mock_notify.call_args
        assert kwargs["subtitle"] == long_subtitle


def test_send_notification_special_characters(notification_manager):
    """Test notification with special characters."""
    with mock.patch("gmail2bear.notifications.pync.notify") as mock_notify:
        # Create strings with special characters
        title = "Test 🔔 Title with Emoji 🚀"
        message = "Test Message with symbols: !@#$%^&*()_+{}|:<>?~`-=[]\\;',./€£¥"
        subtitle = "Subtitle with Unicode: 你好, こんにちは, 안녕하세요"

        # Send notification
        result = notification_manager.send_notification(
            title=title,
            message=message,
            subtitle=subtitle,
        )

        # Verify result
        assert result is True
        mock_notify.assert_called_once()

        # Verify the strings were passed correctly
        args, kwargs = mock_notify.call_args
        assert kwargs["title"] == title
        assert args[0] == message
        assert kwargs["subtitle"] == subtitle


def test_send_notification_empty_title(notification_manager):
    """Test notification with empty title."""
    with mock.patch("gmail2bear.notifications.pync.notify") as mock_notify:
        # Send notification with empty title
        result = notification_manager.send_notification(
            title="",
            message="Test Message",
        )

        # Verify result
        assert result is True
        mock_notify.assert_called_once()

        # Verify the empty title was passed
        args, kwargs = mock_notify.call_args
        assert kwargs["title"] == ""


def test_send_notification_empty_message(notification_manager):
    """Test notification with empty message."""
    with mock.patch("gmail2bear.notifications.pync.notify") as mock_notify:
        # Send notification with empty message
        result = notification_manager.send_notification(
            title="Test Title",
            message="",
        )

        # Verify result
        assert result is True
        mock_notify.assert_called_once()

        # Verify the empty message was passed
        args, kwargs = mock_notify.call_args
        assert args[0] == ""


def test_notify_new_emails_large_count(notification_manager):
    """Test notification for a very large number of emails."""
    with mock.patch.object(notification_manager, "send_notification") as mock_send:
        # Mock successful notification
        mock_send.return_value = True

        # Send notification for 10000 emails
        result = notification_manager.notify_new_emails(10000)

        # Verify result
        assert result is True
        mock_send.assert_called_once()

        # Verify arguments
        args = mock_send.call_args[0]
        assert args[0] == "Gmail to Bear"  # title
        assert args[1] == "10000 new emails processed"  # message
        assert args[2] == "New notes created in Bear"  # subtitle


def test_config_change_at_runtime(notification_manager):
    """Test changing configuration at runtime."""
    # Initial state
    assert notification_manager.show_notifications is True
    assert notification_manager.notification_sound == "default"

    # Change configuration
    notification_manager.show_notifications = False
    notification_manager.notification_sound = "Ping"

    with mock.patch("gmail2bear.notifications.pync.notify") as mock_notify:
        # Send notification
        result = notification_manager.send_notification(
            title="Test Title",
            message="Test Message",
        )

        # Verify notification was not sent due to disabled notifications
        assert result is False
        mock_notify.assert_not_called()

        # Re-enable notifications
        notification_manager.show_notifications = True

        # Send notification again
        result = notification_manager.send_notification(
            title="Test Title",
            message="Test Message",
        )

        # Verify notification was sent with new sound
        assert result is True
        mock_notify.assert_called_once()

        # Verify the new sound was used
        args, kwargs = mock_notify.call_args
        assert kwargs["sound"] == "Ping"


def test_missing_config_values():
    """Test handling of missing configuration values."""
    # Create a mock config with missing values
    config = mock.MagicMock()

    # should_show_notifications returns None
    config.should_show_notifications.return_value = None

    # get_notification_sound returns None
    config.get_notification_sound.return_value = None

    # get_notification_timeout is not implemented
    del config.get_notification_timeout

    # Initialize notification manager with this config
    with mock.patch("platform.system", return_value="Darwin"):
        with mock.patch("gmail2bear.notifications.pync", mock.MagicMock()):
            manager = NotificationManager(config=config)

            # Verify default values are used
            assert manager.show_notifications is True  # Default to True if None
            assert manager.notification_sound == "default"  # Default sound
            assert manager.notification_timeout == 5  # Default timeout


def test_invalid_config_values():
    """Test handling of invalid configuration values."""
    # Create a mock config with invalid values
    config = mock.MagicMock()

    # should_show_notifications returns a non-boolean value
    config.should_show_notifications.return_value = "yes"  # Not a boolean

    # get_notification_sound returns an invalid sound
    config.get_notification_sound.return_value = "InvalidSound"

    # get_notification_timeout returns a non-integer
    config.get_notification_timeout.return_value = "5"  # String instead of int

    # Initialize notification manager with this config
    with mock.patch("platform.system", return_value="Darwin"):
        with mock.patch("gmail2bear.notifications.pync", mock.MagicMock()):
            manager = NotificationManager(config=config)

            # Verify values are handled correctly
            assert manager.show_notifications is True  # Non-boolean treated as True

            # Test that invalid sound is corrected when sending notification
            with mock.patch("gmail2bear.notifications.pync.notify") as mock_notify:
                manager.send_notification(
                    title="Test Title",
                    message="Test Message",
                )

                # Verify the default sound was used instead of the invalid one
                args, kwargs = mock_notify.call_args
                assert kwargs["sound"] == "default"

            # Verify timeout is still the default since conversion failed
            assert manager.notification_timeout == 5


def test_rapid_notifications(notification_manager):
    """Test sending many notifications in rapid succession."""
    with mock.patch("gmail2bear.notifications.pync.notify") as mock_notify:
        # Send 100 notifications in a loop
        for i in range(100):
            result = notification_manager.send_notification(
                title=f"Test Title {i}",
                message=f"Test Message {i}",
            )
            assert result is True

        # Verify all notifications were sent
        assert mock_notify.call_count == 100


def test_actual_pync_notification():
    """Test sending a real notification with pync (non-mocked).

    Note: This test will actually display a notification on macOS.
    It should be skipped in CI environments.
    """
    import platform

    import pytest

    # Skip if not on macOS or if pync is not installed
    if platform.system() != "Darwin":
        pytest.skip("Test requires macOS")

    try:
        import pync  # type: ignore
    except ImportError:
        pytest.skip("Test requires pync to be installed")

    # Create a real notification manager
    from gmail2bear.notifications import NotificationManager

    manager = NotificationManager()

    # Send a real notification
    result = manager.send_notification(
        title="Test Notification",
        message="This is a test notification from pytest",
        sound="Ping",
    )

    # Verify the notification was sent successfully
    assert result is True
