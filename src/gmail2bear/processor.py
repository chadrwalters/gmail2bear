"""Email processor module.

This module handles the main processing logic for Gmail to Bear integration.
"""

import logging
import time
from string import Template
from typing import Dict, List, Optional

from gmail2bear.auth import get_credentials
from gmail2bear.bear import BearClient
from gmail2bear.config import Config
from gmail2bear.gmail_client import GmailClient
from gmail2bear.state import StateManager

logger = logging.getLogger(__name__)


class EmailProcessor:
    """Main processor for Gmail to Bear integration."""

    def __init__(
        self,
        config_path: str,
        credentials_path: str,
        state_path: str,
        token_path: Optional[str] = None
    ):
        """Initialize the email processor.

        Args:
            config_path: Path to the configuration file
            credentials_path: Path to the Google API credentials file
            state_path: Path to the state file
            token_path: Path to the token file (optional)
        """
        self.config_path = config_path
        self.credentials_path = credentials_path
        self.state_path = state_path
        self.token_path = token_path

        # Initialize components
        self.config = Config(config_path)
        self.state_manager = StateManager(state_path)
        self.bear_client = BearClient()

        # These will be initialized when needed
        self.gmail_client = None

    def authenticate(self, force_refresh: bool = False) -> bool:
        """Authenticate with the Gmail API.

        Args:
            force_refresh: Force reauthentication even if token exists

        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            credentials = get_credentials(
                self.credentials_path,
                self.token_path,
                force_refresh
            )
            self.gmail_client = GmailClient(credentials)
            logger.info("Successfully authenticated with Gmail API")
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def process_emails(self, once: bool = True) -> int:
        """Process emails from the configured sender.

        Args:
            once: Run once and exit (don't poll)

        Returns:
            Number of emails processed
        """
        if not self.config.loaded:
            logger.error("Configuration not loaded, cannot process emails")
            return 0

        if not self.gmail_client:
            logger.error("Gmail client not initialized, please authenticate first")
            return 0

        sender_email = self.config.get_sender_email()
        if not sender_email:
            logger.error("Sender email not configured")
            return 0

        poll_interval = self.config.get_poll_interval()
        processed_count = 0

        try:
            while True:
                logger.info(f"Checking for emails from {sender_email}")

                # Get processed email IDs
                processed_ids = self.state_manager.get_processed_ids()

                # Get emails from sender
                emails = self.gmail_client.get_emails_from_sender(
                    sender_email=sender_email,
                    max_results=10,
                    only_unread=True,
                    processed_ids=processed_ids
                )

                if not emails:
                    logger.info("No new emails to process")
                else:
                    logger.info(f"Found {len(emails)} new emails to process")

                    # Process each email
                    for email in emails:
                        if self._process_single_email(email):
                            processed_count += 1

                if once:
                    break

                logger.info(f"Waiting {poll_interval} seconds before next check")
                time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("Process interrupted by user")
        except Exception as e:
            logger.error(f"Error processing emails: {e}")

        return processed_count

    def _process_single_email(self, email: Dict) -> bool:
        """Process a single email.

        Args:
            email: Email data dictionary

        Returns:
            True if processing was successful, False otherwise
        """
        email_id = email["id"]

        # Skip if already processed
        if self.state_manager.is_processed(email_id):
            logger.debug(f"Email {email_id} already processed, skipping")
            return False

        try:
            # Format note title and body using templates
            note_title = self._format_note_title(email)
            note_body = self._format_note_body(email)

            # Get tags from config
            tags = self.config.get_tags()

            # Create note in Bear
            logger.info(f"Creating Bear note for email: {email['subject']}")
            success = self.bear_client.create_note(
                title=note_title,
                body=note_body,
                tags=tags,
                id_suffix=email_id
            )

            if success:
                # Mark email as read in Gmail
                self.gmail_client.mark_as_read(email_id)

                # Mark as processed in state manager
                self.state_manager.mark_as_processed(email_id)

                logger.info(f"Successfully processed email: {email['subject']}")
                return True
            else:
                logger.error(f"Failed to create Bear note for email: {email['subject']}")
                return False

        except Exception as e:
            logger.error(f"Error processing email {email_id}: {e}")
            return False

    def _format_note_title(self, email: Dict) -> str:
        """Format the note title using the template from config.

        Args:
            email: Email data dictionary

        Returns:
            Formatted note title
        """
        template = self.config.get_note_title_template()

        # Simple string formatting
        return template.format(
            subject=email["subject"],
            date=email["date"],
            sender=email["sender"],
            email_id=email["id"]
        )

    def _format_note_body(self, email: Dict) -> str:
        """Format the note body using the template from config.

        Args:
            email: Email data dictionary

        Returns:
            Formatted note body
        """
        template = self.config.get_note_body_template()

        # Simple string formatting
        return template.format(
            subject=email["subject"],
            body=email["body"],
            date=email["date"],
            sender=email["sender"],
            email_id=email["id"]
        )
