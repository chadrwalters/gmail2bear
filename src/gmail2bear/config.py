"""Configuration module.

This module handles loading and parsing the configuration file.
"""

import configparser
import logging
import os
from typing import Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class Config:
    """Configuration handler for Gmail to Bear."""

    def __init__(self, config_path: str):
        """Initialize the configuration handler.

        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.config = configparser.ConfigParser(interpolation=None)
        self.loaded = self._load_config()
        self.last_modified_time = self._get_file_modified_time()
        self._file_watcher_enabled = False

    def _load_config(self) -> bool:
        """Load the configuration file.

        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(self.config_path):
            logger.error(f"Configuration file not found: {self.config_path}")
            return False

        try:
            self.config.read(self.config_path)
            logger.debug(f"Loaded configuration from {self.config_path}")
            return True
        except configparser.Error as e:
            logger.error(f"Error parsing configuration file: {e}")
            return False

    def _get_file_modified_time(self) -> float:
        """Get the last modified time of the configuration file.

        Returns:
            Last modified time as a float (timestamp)
        """
        if os.path.exists(self.config_path):
            return os.path.getmtime(self.config_path)
        return 0

    def has_changed(self) -> bool:
        """Check if the configuration file has changed since last load.

        Returns:
            True if the file has changed, False otherwise
        """
        current_mtime = self._get_file_modified_time()
        if current_mtime > self.last_modified_time:
            logger.debug(f"Configuration file has changed: {self.config_path}")
            return True
        return False

    def reload_if_changed(self) -> bool:
        """Reload the configuration if the file has changed.

        Returns:
            True if reloaded, False otherwise
        """
        if self.has_changed():
            logger.info(f"Reloading configuration from {self.config_path}")
            self.loaded = self._load_config()
            self.last_modified_time = self._get_file_modified_time()
            return self.loaded
        return False

    def enable_file_watcher(
        self, callback: Optional[Callable[[], None]] = None
    ) -> None:
        """Enable watching for configuration file changes.

        Args:
            callback: Function to call when configuration changes (optional)
        """
        self._file_watcher_enabled = True
        self._file_watcher_callback = callback
        logger.info(f"Enabled configuration file watcher for {self.config_path}")

    def disable_file_watcher(self) -> None:
        """Disable watching for configuration file changes."""
        self._file_watcher_enabled = False
        logger.info(f"Disabled configuration file watcher for {self.config_path}")

    def check_for_changes(self) -> bool:
        """Check for configuration changes and reload if necessary.

        Returns:
            True if configuration was reloaded, False otherwise
        """
        if not self._file_watcher_enabled:
            return False

        if self.reload_if_changed():
            if hasattr(self, "_file_watcher_callback") and self._file_watcher_callback:
                self._file_watcher_callback()
            return True
        return False

    def get_sender_email(self) -> Union[str, List[str], None]:
        """Get the sender email(s) to monitor.

        Returns:
            Sender email address(es) or None if not configured
        """
        try:
            sender_email = self.config.get("gmail", "sender_email")

            # Check if it's a comma-separated list
            if "," in sender_email:
                # Split by comma and strip whitespace
                return [
                    email.strip() for email in sender_email.split(",") if email.strip()
                ]

            return sender_email
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            logger.error(f"Error getting sender email from config: {e}")
            return None

    def get_poll_interval(self) -> int:
        """Get the polling interval in seconds.

        Returns:
            Polling interval in seconds (default: 300)
        """
        try:
            return self.config.getint("gmail", "poll_interval", fallback=300)
        except (configparser.NoSectionError, ValueError) as e:
            logger.warning(f"Error getting poll interval from config: {e}")
            return 300

    def should_archive_emails(self) -> bool:
        """Check if emails should be archived after processing.

        Returns:
            True if emails should be archived, False otherwise
        """
        try:
            return self.config.getboolean("gmail", "archive_emails", fallback=False)
        except (configparser.NoSectionError, ValueError) as e:
            logger.warning(f"Error getting archive_emails from config: {e}")
            return False

    def get_note_title_template(self) -> str:
        """Get the Bear note title template.

        Returns:
            Note title template (default: "Email: {subject}")
        """
        try:
            return self.config.get(
                "bear", "note_title_template", fallback="Email: {subject}"
            )
        except configparser.NoSectionError as e:
            logger.warning(f"Error getting note title template from config: {e}")
            return "Email: {subject}"

    def get_note_body_template(self) -> str:
        """Get the Bear note body template.

        Returns:
            Note body template (default: simple format)
        """
        default_template = (
            "# {subject}\n\n"
            "From: {sender}\n"
            "Date: {date}\n\n"
            "{body}\n\n"
            "---\n"
            "Source: Gmail ID {id}"
        )

        try:
            template = self.config.get(
                "bear", "note_body_template", fallback=default_template
            )
            # Remove triple quotes if present (from multiline string)
            if template.startswith("'''") and template.endswith("'''"):
                template = template[3:-3]
            return template
        except configparser.NoSectionError as e:
            logger.warning(f"Error getting note body template from config: {e}")
            return default_template

    def get_tags(self) -> List[str]:
        """Get the tags to add to Bear notes.

        Returns:
            List of tags (default: ["email", "gmail"])
        """
        try:
            tags_str = self.config.get("bear", "tags", fallback="email,gmail")
            return [tag.strip() for tag in tags_str.split(",") if tag.strip()]
        except configparser.NoSectionError as e:
            logger.warning(f"Error getting tags from config: {e}")
            return ["email", "gmail"]

    def get_logging_level(self) -> str:
        """Get the logging level.

        Returns:
            Logging level (default: "INFO")
        """
        try:
            return self.config.get("logging", "level", fallback="INFO").upper()
        except configparser.NoSectionError as e:
            logger.warning(f"Error getting logging level from config: {e}")
            return "INFO"

    def get_log_file(self) -> Optional[str]:
        """Get the log file path.

        Returns:
            Log file path or None if not configured
        """
        try:
            log_file = self.config.get("logging", "file", fallback=None)
            if log_file:
                # Expand user directory if path starts with ~
                log_file = os.path.expanduser(log_file)
                # Create directory if it doesn't exist
                log_dir = os.path.dirname(log_file)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
            return log_file
        except configparser.NoSectionError as e:
            logger.warning(f"Error getting log file from config: {e}")
            return None

    def get_max_log_size(self) -> int:
        """Get the maximum log file size in bytes.

        Returns:
            Maximum log file size in bytes (default: 1MB)
        """
        try:
            # Size in KB, convert to bytes
            return self.config.getint("logging", "max_log_size", fallback=1024) * 1024
        except (configparser.NoSectionError, ValueError) as e:
            logger.warning(f"Error getting max log size from config: {e}")
            return 1024 * 1024  # 1MB default

    def get_log_backup_count(self) -> int:
        """Get the number of log backup files to keep.

        Returns:
            Number of log backup files (default: 3)
        """
        try:
            return self.config.getint("logging", "backup_count", fallback=3)
        except (configparser.NoSectionError, ValueError) as e:
            logger.warning(f"Error getting log backup count from config: {e}")
            return 3

    def should_show_notifications(self) -> bool:
        """Check if system notifications should be shown.

        Returns:
            True if notifications should be shown, False otherwise
        """
        try:
            return self.config.getboolean(
                "service", "show_notifications", fallback=True
            )
        except (configparser.NoSectionError, ValueError) as e:
            logger.warning(f"Error getting show_notifications from config: {e}")
            return True

    def should_start_at_login(self) -> bool:
        """Check if the service should start at login.

        Returns:
            True if the service should start at login, False otherwise
        """
        try:
            return self.config.getboolean("service", "start_at_login", fallback=True)
        except (configparser.NoSectionError, ValueError) as e:
            logger.warning(f"Error getting start_at_login from config: {e}")
            return True

    def get_notification_sound(self) -> str:
        """Get the notification sound name.

        Returns:
            Notification sound name (default: "default")
        """
        try:
            return self.config.get("service", "notification_sound", fallback="default")
        except configparser.NoSectionError as e:
            logger.warning(f"Error getting notification sound from config: {e}")
            return "default"

    def get_notification_timeout(self) -> int:
        """Get the notification timeout in seconds.

        Returns:
            Notification timeout in seconds (default: 5)
        """
        try:
            if self.config.has_option("service", "notification_timeout"):
                return self.config.getint("service", "notification_timeout")
        except (configparser.Error, ValueError) as e:
            logger.warning(f"Error getting notification timeout: {e}")
        return 5

    def should_monitor_network(self) -> bool:
        """Check if network monitoring is enabled.

        Returns:
            True if enabled, False otherwise
        """
        try:
            if self.config.has_option("service", "monitor_network"):
                return self.config.getboolean("service", "monitor_network")
        except (configparser.Error, ValueError) as e:
            logger.warning(f"Error getting monitor_network setting: {e}")
        return True

    def should_handle_system_events(self) -> bool:
        """Check if system event handling is enabled.

        Returns:
            True if enabled, False otherwise
        """
        try:
            if self.config.has_option("service", "handle_system_events"):
                return self.config.getboolean("service", "handle_system_events")
        except (configparser.Error, ValueError) as e:
            logger.warning(f"Error getting handle_system_events setting: {e}")
        return True

    def get_keychain_enabled(self) -> bool:
        """Check if macOS Keychain integration is enabled.

        Returns:
            True if enabled, False otherwise
        """
        try:
            if self.config.has_option("security", "use_keychain"):
                return self.config.getboolean("security", "use_keychain")
        except (configparser.Error, ValueError) as e:
            logger.warning(f"Error getting use_keychain setting: {e}")
        return False

    def get_keychain_service_name(self) -> str:
        """Get the Keychain service name for storing credentials.

        Returns:
            Keychain service name (default: "Gmail to Bear")
        """
        try:
            if self.config.has_option("security", "keychain_service_name"):
                return self.config.get("security", "keychain_service_name")
        except configparser.Error as e:
            logger.warning(f"Error getting keychain_service_name: {e}")
        return "Gmail to Bear"

    def get_all_settings(self) -> Dict[str, Dict[str, str]]:
        """Get all configuration settings as a dictionary.

        Returns:
            Dictionary of all configuration settings
        """
        settings: Dict[str, Dict[str, str]] = {}
        for section in self.config.sections():
            settings[section] = {}
            for option in self.config.options(section):
                settings[section][option] = self.config.get(section, option)
        return settings

    def create_default_config(self) -> bool:
        """Create a default configuration file.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create a new configuration
            self.config = configparser.ConfigParser(interpolation=None)

            # Gmail settings
            self.config["gmail"] = {
                "sender_email": "example@gmail.com",
                "poll_interval": "300",  # 5 minutes
                "archive_emails": "true",
            }

            # Bear settings
            self.config["bear"] = {
                "note_title_template": "Email: {subject}",
                "note_body_template": "# {subject}\n\nFrom: {sender}\nDate: {date}\n\n{body}\n\n---\nSource: Gmail ID {id}",
                "tags": "email,gmail",
            }

            # Service settings
            self.config["service"] = {
                "show_notifications": "true",
                "start_at_login": "true",
                "notification_sound": "default",
                "notification_timeout": "5",
                "monitor_network": "true",
                "handle_system_events": "true",
            }

            # Security settings
            self.config["security"] = {
                "use_keychain": "false",
                "keychain_service_name": "Gmail to Bear",
            }

            # Logging settings
            self.config["logging"] = {
                "level": "INFO",
                "file": os.path.join(
                    os.path.dirname(self.config_path), "gmail2bear.log"
                ),
                "max_log_size": "1024",  # KB
                "backup_count": "3",
            }

            # Write the configuration to file
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w") as config_file:
                self.config.write(config_file)

            logger.info(f"Created default configuration at {self.config_path}")
            return True

        except Exception as e:
            logger.error(f"Error creating default configuration: {e}")
            return False
