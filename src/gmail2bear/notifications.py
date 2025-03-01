"""Notifications module for Gmail to Bear.

This module provides functionality for sending system notifications.
"""

import logging
import platform
from typing import Any, Optional

try:
    import pync  # type: ignore
except ImportError:
    pync = None  # pync will be None if it's not installed

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manager for system notifications."""

    # Available notification sounds on macOS
    AVAILABLE_SOUNDS = [
        "default",
        "Basso",
        "Blow",
        "Bottle",
        "Frog",
        "Funk",
        "Glass",
        "Hero",
        "Morse",
        "Ping",
        "Pop",
        "Purr",
        "Sosumi",
        "Submarine",
        "Tink",
    ]

    def __init__(self, app_name: str = "Gmail to Bear", config: Any = None):
        """Initialize the notification manager.

        Args:
            app_name: Name of the application to show in notifications
            config: Configuration object (optional)
        """
        self.app_name = app_name
        self.config = config
        self.enabled = self._is_supported()

        # Default settings
        self.show_notifications = True
        self.notification_sound = "default"
        self.notification_timeout = 5  # seconds

        # Load settings from config if available
        if self.config:
            # Handle show_notifications - default to True if None or invalid type
            config_show = self.config.should_show_notifications()
            if isinstance(config_show, bool):
                self.show_notifications = config_show

            # Handle notification sound - default to "default" if None or invalid
            config_sound = self.config.get_notification_sound()
            if config_sound is not None:
                self.notification_sound = config_sound

            # Handle notification timeout - default to 5 if not available or invalid
            if hasattr(self.config, "get_notification_timeout"):
                try:
                    timeout = self.config.get_notification_timeout()
                    if isinstance(timeout, int) and timeout > 0:
                        self.notification_timeout = timeout
                except (TypeError, ValueError):
                    # Keep default if conversion fails
                    pass

    def _is_supported(self) -> bool:
        """Check if notifications are supported on this system.

        Returns:
            True if supported, False otherwise
        """
        # Currently only supports macOS and only if pync is installed
        return platform.system() == "Darwin" and pync is not None

    def send_notification(
        self,
        title: str,
        message: str,
        subtitle: Optional[str] = None,
        sound: Optional[str] = None,
        timeout: Optional[int] = None,  # timeout is not used with pync
    ) -> bool:
        """Send a system notification using pync.

        Args:
            title: Notification title
            message: Notification message
            subtitle: Notification subtitle (optional)
            sound: Notification sound (optional, overrides default)
            timeout: Not used for pync. It's here for API compatibility.

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.show_notifications:
            logger.debug(f"Notifications not shown: {title} - {message}")
            return False

        try:
            # Use provided sound or default
            notification_sound = sound if sound else self.notification_sound

            # Validate sound (pync doesn't validate, but we'll keep
            # the validation for consistency)
            if notification_sound not in self.AVAILABLE_SOUNDS:
                logger.warning(
                    f"Invalid notification sound: {notification_sound}, using default"
                )
                notification_sound = "default"

            pync.notify(
                message,
                title=title,
                subtitle=subtitle,
                sound=notification_sound,
            )
            logger.debug(f"Sent notification: {title} - {message}")
            return True
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False

    def notify_new_emails(self, count: int) -> bool:
        """Send a notification about new emails.

        Args:
            count: Number of new emails processed

        Returns:
            True if successful, False otherwise
        """
        if count <= 0:
            return False

        title = "Gmail to Bear"
        message = f"{count} new email{'s' if count > 1 else ''} processed"
        subtitle = "New notes created in Bear"

        return self.send_notification(title, message, subtitle)

    def notify_error(self, error_message: str) -> bool:
        """Send a notification about an error.

        Args:
            error_message: Error message

        Returns:
            True if successful, False otherwise
        """
        title = "Gmail to Bear - Error"
        message = error_message

        return self.send_notification(title, message, sound="Basso")

    def notify_service_status(self, status: str) -> bool:
        """Send a notification about service status.

        Args:
            status: Service status message

        Returns:
            True if successful, False otherwise
        """
        title = "Gmail to Bear - Service"
        message = status

        return self.send_notification(title, message)

    def notify_network_status(self, is_connected: bool) -> bool:
        """Send a notification about network status.

        Args:
            is_connected: Whether network is connected

        Returns:
            True if successful, False otherwise
        """
        title = "Gmail to Bear - Network"

        if is_connected:
            message = "Network connection restored"
            sound = "Ping"
        else:
            message = "Network connection lost"
            sound = "Basso"

        return self.send_notification(title, message, sound=sound)

    def notify_system_event(
        self, event_type: str, details: Optional[str] = None
    ) -> bool:
        """Send a notification about system events.

        Args:
            event_type: Type of system event (e.g., "sleep", "wake")
            details: Additional details (optional)

        Returns:
            True if successful, False otherwise
        """
        title = "Gmail to Bear - System"

        if event_type == "sleep":
            message = "System going to sleep, pausing service"
        elif event_type == "wake":
            message = "System waking up, resuming service"
        else:
            message = f"System event: {event_type}"

        if details:
            message += f" ({details})"

        return self.send_notification(title, message)
