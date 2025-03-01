"""Email processor module.

This module handles the main processing logic for Gmail to Bear integration.
"""

import functools
import logging
import random
import signal
import socket
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar, Union

import html2text
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError  # type: ignore

from gmail2bear.auth import get_credentials
from gmail2bear.bear import BearClient
from gmail2bear.config import Config
from gmail2bear.gmail_client import GmailClient
from gmail2bear.notifications import NotificationManager
from gmail2bear.state import StateManager

logger = logging.getLogger(__name__)

# Type variable for the return type of the decorated function
T = TypeVar("T")
# Type for exceptions that can be caught
ExceptionType = Union[Type[Exception], Tuple[Type[Exception], ...]]


def retry_on_failure(
    max_retries: int = 3,
    initial_backoff: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: float = 0.1,
    retry_exceptions: ExceptionType = (HttpError, ConnectionError, TimeoutError),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry a function on failure with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds
        backoff_factor: Factor to increase backoff time with each retry
        jitter: Random jitter factor to add to backoff time (0-1)
        retry_exceptions: Tuple of exceptions to retry on

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as e:
                    last_exception = e

                    # Don't retry if this was the last attempt
                    if attempt >= max_retries:
                        logger.error(
                            f"Failed after {max_retries} retries: {func.__name__}"
                        )
                        break

                    # Calculate backoff time with jitter
                    backoff_time = initial_backoff * (backoff_factor**attempt)
                    jitter_amount = backoff_time * jitter * random.uniform(-1, 1)
                    sleep_time = backoff_time + jitter_amount

                    # Log retry attempt
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {func.__name__} "
                        f"after {sleep_time:.2f}s due to: {str(e)}"
                    )

                    # Sleep before retry
                    time.sleep(max(0.1, sleep_time))

            # Re-raise the last exception
            if last_exception:
                raise last_exception

            # This should never happen, but needed for type checking
            raise RuntimeError(
                f"Unexpected error in retry_on_failure for {func.__name__}"
            )

        return wrapper

    return decorator


class EmailProcessor:
    """Main processor for Gmail to Bear integration."""

    def __init__(
        self,
        config_path: str,
        credentials_path: str,
        state_path: str,
        token_path: Optional[str] = None,
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
        self.notification_manager = NotificationManager(config=self.config)

        # Initialize HTML converter
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.body_width = 0  # No wrapping
        self.html_converter.protect_links = True
        self.html_converter.mark_code = True
        self.html_converter.default_image_alt = "Image"

        # Service state
        self.running = False
        self.paused = False
        self.credentials: Optional[Credentials] = None
        self.gmail_client: Optional[GmailClient] = None
        self.network_available = True
        self.last_network_check: float = 0.0
        self.network_check_interval: float = 60.0  # seconds
        self.last_config_check: float = 0.0
        self.config_check_interval: float = 30.0  # seconds

        # Error tracking
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        self.error_backoff_time = 30  # seconds
        self.last_error_time: float = 0.0
        self.network_failure_count = 0
        self.auth_failure_count = 0

    @retry_on_failure(max_retries=3, initial_backoff=2.0)
    def authenticate(self, force_refresh: bool = False) -> bool:
        """Authenticate with the Gmail API.

        Args:
            force_refresh: Force reauthentication even if token exists

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if Keychain should be used
            use_keychain = False
            keychain_service_name = "Gmail to Bear"

            if hasattr(self.config, "get_keychain_enabled"):
                use_keychain = self.config.get_keychain_enabled()

            if hasattr(self.config, "get_keychain_service_name"):
                keychain_service_name = self.config.get_keychain_service_name()

            # Get credentials
            self.credentials = get_credentials(
                self.credentials_path,
                self.token_path,
                force_refresh,
                use_keychain,
                keychain_service_name,
            )

            # Initialize Gmail client
            self.gmail_client = GmailClient(self.credentials)
            logger.info("Successfully authenticated with Gmail API")
            self.auth_failure_count = 0  # Reset failure counter on success
            return True
        except Exception as e:
            self.auth_failure_count += 1
            logger.error(
                f"Authentication failed (attempt {self.auth_failure_count}): {e}"
            )
            if self.auth_failure_count >= 3:
                logger.critical(
                    f"Multiple authentication failures ({self.auth_failure_count}). "
                    f"Check credentials and network connectivity."
                )
                self.notification_manager.notify_error(
                    f"Authentication failed after {self.auth_failure_count} attempts. "
                    f"Check credentials and network connectivity."
                )
            return False

    def process_emails(self, once: bool = True, send_notification: bool = True) -> int:
        """Process emails from the configured sender.

        Args:
            once: Process emails once and exit (default: True)
            send_notification: Whether to send a notification (default: True)

        Returns:
            Number of emails processed
        """
        if not self.config.loaded:
            error_msg = "Configuration not loaded, cannot process emails"
            logger.error(error_msg)
            self.notification_manager.notify_error(error_msg)
            return 0

        if not self.gmail_client:
            error_msg = "Gmail client not initialized, please authenticate first"
            logger.error(error_msg)
            self.notification_manager.notify_error(error_msg)
            return 0

        sender_email = self.config.get_sender_email()
        if not sender_email:
            error_msg = "Sender email not configured"
            logger.error(error_msg)
            self.notification_manager.notify_error(error_msg)
            return 0

        poll_interval = self.config.get_poll_interval()
        processed_count = 0

        try:
            while True:
                logger.info(f"Checking for emails from {sender_email}")

                # Get processed email IDs
                processed_ids = self.state_manager.get_processed_ids()

                try:
                    # Get emails from sender with retry mechanism
                    emails = self._get_emails_with_retry(
                        sender_email=sender_email,
                        max_results=10,
                        only_unread=True,
                        processed_ids=processed_ids,
                    )

                    if not emails:
                        logger.info("No new emails to process")
                    else:
                        logger.info(f"Found {len(emails)} new emails to process")

                        # Process each email
                        for email in emails:
                            if self._process_single_email(email):
                                processed_count += 1

                    # Reset consecutive errors on success
                    self.consecutive_errors = 0

                except Exception as e:
                    self.consecutive_errors += 1
                    error_msg = f"Error processing emails (attempt {self.consecutive_errors}): {e}"
                    logger.error(error_msg)

                    if self.consecutive_errors >= self.max_consecutive_errors:
                        critical_msg = (
                            f"Multiple consecutive errors ({self.consecutive_errors}). "
                            f"Pausing email processing for {self.error_backoff_time} seconds."
                        )
                        logger.critical(critical_msg)
                        self.notification_manager.notify_error(critical_msg)
                        self.last_error_time = time.time()

                        # Sleep for backoff time
                        if once:
                            break
                        time.sleep(self.error_backoff_time)
                        continue

                # Send notification if emails were processed and notifications are enabled
                if processed_count > 0 and send_notification:
                    self.notification_manager.notify_new_emails(processed_count)

                if once:
                    break

                logger.info(f"Waiting {poll_interval} seconds before next check")
                time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("Process interrupted by user")
        except Exception as e:
            error_msg = f"Error processing emails: {e}"
            logger.error(error_msg)
            self.notification_manager.notify_error(error_msg)

        return processed_count

    @retry_on_failure(max_retries=3, initial_backoff=1.0)
    def _get_emails_with_retry(self, **kwargs: Any) -> List[Dict]:
        """Get emails with retry mechanism.

        Args:
            **kwargs: Arguments to pass to get_emails_from_sender

        Returns:
            List of email dictionaries
        """
        if not self.gmail_client:
            raise ValueError("Gmail client not initialized")

        return self.gmail_client.get_emails_from_sender(**kwargs)

    def run_service(self) -> None:
        """Run the processor as a continuous service."""
        logger.info("Starting Gmail to Bear service")
        self.notification_manager.notify_service_status("Service started")

        # Set up signal handlers
        self._setup_signal_handlers()

        # Enable configuration file watcher
        self.config.enable_file_watcher(callback=self._on_config_changed)

        # Main service loop
        self.running = True
        while self.running:
            try:
                # Check for configuration changes
                self._check_config()

                # Check network status if enabled
                if self.config.should_monitor_network():
                    self._check_network()

                # Skip processing if paused
                if self.paused:
                    logger.debug("Service is paused, skipping processing")
                    self._interruptible_sleep(5)
                    continue

                # Skip processing if network is unavailable
                if not self.network_available:
                    logger.debug("Network is unavailable, skipping processing")
                    self._interruptible_sleep(30)  # Longer sleep when network is down
                    continue

                # Skip processing if in error backoff period
                if (
                    (time.time() - self.last_error_time) < self.error_backoff_time
                    and self.consecutive_errors >= self.max_consecutive_errors
                ):
                    remaining = int(
                        self.error_backoff_time - (time.time() - self.last_error_time)
                    )
                    logger.debug(f"In error backoff period, {remaining}s remaining")
                    self._interruptible_sleep(min(remaining, 5))
                    continue

                # Process emails
                try:
                    count = self.process_emails(once=False, send_notification=False)
                    if count > 0:
                        self.notification_manager.notify_new_emails(count)
                except Exception as e:
                    self.consecutive_errors += 1
                    logger.error(
                        f"Error processing emails (attempt {self.consecutive_errors}): {e}"
                    )
                    self.notification_manager.notify_error(
                        f"Error processing emails: {e}"
                    )

                    # If too many consecutive errors, enter backoff period
                    if self.consecutive_errors >= self.max_consecutive_errors:
                        critical_msg = (
                            f"Multiple consecutive errors ({self.consecutive_errors}). "
                            f"Entering error backoff period for {self.error_backoff_time} seconds."
                        )
                        logger.critical(critical_msg)
                        self.notification_manager.notify_error(critical_msg)
                        self.last_error_time = time.time()
                        self._interruptible_sleep(min(self.error_backoff_time, 30))
                        continue

                # Sleep for the configured interval
                poll_interval = self.config.get_poll_interval()
                self._interruptible_sleep(poll_interval)

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down")
                self.running = False
            except Exception as e:
                logger.error(f"Unexpected error in service loop: {e}")
                self.notification_manager.notify_error(f"Service error: {e}")
                # Sleep briefly to avoid tight loop on persistent errors
                self._interruptible_sleep(30)

        # Clean up
        logger.info("Gmail to Bear service stopped")
        self.notification_manager.notify_service_status("Service stopped")

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for the service."""
        # Handle termination signals
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._handle_shutdown_signal)

        # Handle pause/resume signals
        signal.signal(signal.SIGUSR1, self._handle_pause_signal)
        signal.signal(signal.SIGUSR2, self._handle_resume_signal)

        # Handle configuration reload signal
        signal.signal(signal.SIGHUP, self._handle_reload_signal)

        # Handle system sleep/wake signals if supported
        if hasattr(signal, "SIGPWR"):  # Linux
            signal.signal(signal.SIGPWR, self._handle_power_signal)
        if hasattr(signal, "SIGINFO"):  # macOS
            signal.signal(signal.SIGINFO, self._handle_info_signal)

    def _handle_shutdown_signal(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        sig_name = signal.Signals(signum).name
        logger.info(f"Received signal {sig_name}, shutting down")
        self.running = False

    def _handle_pause_signal(self, signum: int, frame: Any) -> None:
        """Handle pause signal.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info("Received pause signal, pausing service")
        self.paused = True
        self.notification_manager.notify_service_status("Service paused")

    def _handle_resume_signal(self, signum: int, frame: Any) -> None:
        """Handle resume signal.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info("Received resume signal, resuming service")
        self.paused = False
        self.notification_manager.notify_service_status("Service resumed")

    def _handle_reload_signal(self, signum: int, frame: Any) -> None:
        """Handle configuration reload signal.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info("Received reload signal, reloading configuration")
        self._reload_config()

    def _handle_power_signal(self, signum: int, frame: Any) -> None:
        """Handle power-related signals (sleep/wake).

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info("Received power signal, system may be sleeping or waking")
        # We'll handle the actual sleep/wake detection in the main loop
        # through network connectivity checks

    def _handle_info_signal(self, signum: int, frame: Any) -> None:
        """Handle info signal (macOS).

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info("Received info signal, printing status")
        status = {
            "running": self.running,
            "paused": self.paused,
            "network_available": self.network_available,
            "authenticated": self.credentials is not None,
            "consecutive_errors": self.consecutive_errors,
            "network_failure_count": self.network_failure_count,
            "auth_failure_count": self.auth_failure_count,
        }
        logger.info(f"Service status: {status}")

    def _interruptible_sleep(self, seconds: int) -> None:
        """Sleep for the specified time, but allow interruption.

        Args:
            seconds: Number of seconds to sleep
        """
        # Sleep in small increments to allow for interruption
        increment = 1
        for _ in range(0, seconds, increment):
            if not self.running:
                break
            time.sleep(increment)

    def _check_config(self) -> None:
        """Check for configuration changes and reload if necessary."""
        current_time = time.time()
        if current_time - self.last_config_check >= self.config_check_interval:
            self.last_config_check = current_time
            self.config.check_for_changes()

    def _check_network(self) -> None:
        """Check network connectivity and handle changes."""
        current_time = time.time()
        if current_time - self.last_network_check >= self.network_check_interval:
            self.last_network_check = current_time

            # Check if network is available
            was_available = self.network_available
            self.network_available = self._is_network_available()

            # Handle network status changes
            if was_available and not self.network_available:
                self.network_failure_count += 1
                logger.warning(
                    f"Network connection lost (failure #{self.network_failure_count})"
                )
                self.notification_manager.notify_network_status(False)
            elif not was_available and self.network_available:
                logger.info(
                    f"Network connection restored after {self.network_failure_count} failures"
                )
                self.notification_manager.notify_network_status(True)
                self.network_failure_count = 0
                # Re-authenticate when network is restored
                self.authenticate()

    def _is_network_available(self) -> bool:
        """Check if network is available.

        Returns:
            True if network is available, False otherwise
        """
        # Try multiple DNS servers in case one is down
        dns_servers = [
            ("8.8.8.8", 53),  # Google DNS
            ("1.1.1.1", 53),  # Cloudflare DNS
            ("9.9.9.9", 53),  # Quad9 DNS
        ]

        for dns_server in dns_servers:
            try:
                # Try to connect to DNS server
                socket.create_connection(dns_server, timeout=3)
                return True
            except OSError:
                # Try the next server
                continue

        # All connection attempts failed
        return False

    def _reload_config(self) -> None:
        """Reload configuration."""
        logger.info("Reloading configuration")

        # Reload configuration
        self.config = Config(self.config_path)

        # Update notification manager
        self.notification_manager = NotificationManager(config=self.config)

        # Notify about reload
        self.notification_manager.notify_service_status("Configuration reloaded")

    def _on_config_changed(self) -> None:
        """Handle configuration file changes."""
        logger.info("Configuration file changed, reloading")
        self._reload_config()

    @retry_on_failure(max_retries=2, initial_backoff=1.0)
    def _process_single_email(self, email: Dict[str, Any]) -> bool:
        """Process a single email.

        Args:
            email: Email data dictionary

        Returns:
            True if successful, False otherwise
        """
        email_id = email["id"]

        # Skip if already processed
        if self.state_manager.is_processed(email_id):
            logger.debug(f"Email {email_id} already processed, skipping")
            return False

        try:
            # Convert HTML to Markdown if needed
            if email.get("is_html", False):
                logger.debug(f"Converting HTML to Markdown for email {email_id}")
                email["body"] = self._convert_html_to_markdown(email["body"])

            # Format note title and body using templates
            note_title = self._format_note_title(email)
            note_body = self._format_note_body(email)

            # Get tags from config
            tags = self.config.get_tags()

            # Create note in Bear
            logger.info(f"Creating Bear note for email: {email['subject']}")
            success = self.bear_client.create_note(
                title=note_title, body=note_body, tags=tags, id_suffix=email_id
            )

            if success and self.gmail_client:
                # Mark email as read in Gmail
                self.gmail_client.mark_as_read(email_id)

                # Archive email if configured
                if self.config.should_archive_emails():
                    logger.debug(f"Archiving email {email_id}")
                    self.gmail_client.archive_message(email_id)

                # Mark as processed in state manager
                self.state_manager.mark_as_processed(email_id)

                logger.info(f"Successfully processed email: {email['subject']}")
                return True
            else:
                error_msg = f"Failed to create Bear note for email: {email['subject']}"
                logger.error(error_msg)
                self.notification_manager.notify_error(error_msg)
                return False

        except Exception as e:
            error_msg = f"Error processing email {email_id}: {e}"
            logger.error(error_msg)
            self.notification_manager.notify_error(error_msg)
            return False

    def _convert_html_to_markdown(self, html_content: str) -> str:
        """Convert HTML content to Markdown.

        Args:
            html_content: HTML content to convert

        Returns:
            Markdown formatted content
        """
        try:
            return self.html_converter.handle(html_content)
        except Exception as e:
            logger.error(f"Error converting HTML to Markdown: {e}")
            error_msg = f"Error converting HTML content: {str(e)}\n\n"
            return f"{error_msg}Original content:\n{html_content}"

    def _format_note_title(self, email: Dict[str, Any]) -> str:
        """Format the note title using the template from config.

        Args:
            email: Email data dictionary

        Returns:
            Formatted note title
        """
        template = self.config.get_note_title_template()

        # Parse date string to datetime object if it's a string
        date_value = email["date"]
        if isinstance(date_value, str):
            try:
                # Try to parse the date string to a datetime object
                from datetime import datetime

                date_value = datetime.strptime(date_value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # If parsing fails, keep the original string
                logger.warning(f"Could not parse date string: {date_value}")

        # Simple string formatting
        return template.format(
            subject=email["subject"],
            date=date_value,
            sender=email["sender"],
            id=email["id"],
        )

    def _format_note_body(self, email: Dict[str, Any]) -> str:
        """Format the note body using the template from config.

        Args:
            email: Email data dictionary

        Returns:
            Formatted note body
        """
        template = self.config.get_note_body_template()

        # Parse date string to datetime object if it's a string
        date_value = email["date"]
        if isinstance(date_value, str):
            try:
                # Try to parse the date string to a datetime object
                from datetime import datetime

                date_value = datetime.strptime(date_value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # If parsing fails, keep the original string
                logger.warning(f"Could not parse date string: {date_value}")

        # Simple string formatting
        return template.format(
            subject=email["subject"],
            body=email["body"],
            date=date_value,
            sender=email["sender"],
            id=email["id"],
        )
