"""Configuration module.

This module handles loading and parsing the configuration file.
"""

import configparser
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Config:
    """Configuration handler for Gmail to Bear."""

    def __init__(self, config_path: str):
        """Initialize the configuration handler.

        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.loaded = self._load_config()

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

    def get_sender_email(self) -> Optional[str]:
        """Get the sender email to monitor.

        Returns:
            Sender email address or None if not configured
        """
        try:
            return self.config.get("gmail", "sender_email")
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

    def get_note_title_template(self) -> str:
        """Get the Bear note title template.

        Returns:
            Note title template (default: "Email: {subject}")
        """
        try:
            return self.config.get("bear", "note_title", fallback="Email: {subject}")
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
            "Source: Gmail ID {email_id}"
        )

        try:
            return self.config.get("bear", "note_body", fallback=default_template)
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

    def create_default_config(self) -> bool:
        """Create a default configuration file.

        Returns:
            True if successful, False otherwise
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

        # Create default config
        self.config["gmail"] = {
            "sender_email": "example@gmail.com",
            "poll_interval": "300"
        }

        self.config["bear"] = {
            "note_title": "Email: {subject}",
            "note_body": (
                "# {subject}\n\n"
                "From: {sender}\n"
                "Date: {date}\n\n"
                "{body}\n\n"
                "---\n"
                "Source: Gmail ID {email_id}"
            ),
            "tags": "email,gmail"
        }

        self.config["logging"] = {
            "level": "INFO"
        }

        try:
            with open(self.config_path, "w") as f:
                self.config.write(f)
            logger.info(f"Created default configuration at {self.config_path}")
            return True
        except IOError as e:
            logger.error(f"Error creating default configuration: {e}")
            return False
