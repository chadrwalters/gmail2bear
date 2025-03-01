"""Gmail API client module.

This module handles interactions with the Gmail API.
"""

import base64
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore

logger = logging.getLogger(__name__)

# Type variable for the return type of the request function
T = TypeVar("T")


class GmailClient:
    """Gmail API client for retrieving emails."""

    # HTTP error codes that might be transient and worth retrying
    TRANSIENT_ERROR_CODES = [429, 500, 502, 503, 504]

    # Maximum number of retries for transient errors
    MAX_RETRIES = 3

    def __init__(self, credentials: Credentials):
        """Initialize the Gmail client.

        Args:
            credentials: Google OAuth2 credentials
        """
        self.service = build("gmail", "v1", credentials=credentials)
        self.user_id = "me"  # 'me' refers to the authenticated user

    def get_emails_from_sender(
        self,
        sender_email: Union[str, List[str]],
        max_results: int = 10,
        only_unread: bool = False,
        processed_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get emails from specific sender(s).

        Args:
            sender_email: Email address(es) of the sender(s)
            max_results: Maximum number of emails to retrieve
            only_unread: Only retrieve unread emails
            processed_ids: List of already processed email IDs to exclude

        Returns:
            List of email dictionaries with id, subject, body, date, and sender
        """
        # Handle multiple sender emails
        if isinstance(sender_email, list):
            # Create a query with multiple from: conditions
            query_parts = [f"from:{email}" for email in sender_email]
            query = " OR ".join(query_parts)
        else:
            query = f"from:{sender_email}"

        if only_unread:
            query += " is:unread"

        logger.debug(f"Searching for emails with query: {query}")

        try:
            # Get message IDs matching the query
            results = self._execute_with_retry(
                lambda: self.service.users()
                .messages()
                .list(userId=self.user_id, q=query, maxResults=max_results)
                .execute()
            )

            messages = results.get("messages", [])

            if not messages:
                if isinstance(sender_email, list):
                    logger.info("No emails found from any of the specified senders")
                else:
                    logger.info(f"No emails found from {sender_email}")
                return []

            # Filter out already processed emails
            if processed_ids:
                messages = [msg for msg in messages if msg["id"] not in processed_ids]

            if not messages:
                if isinstance(sender_email, list):
                    logger.info("No new emails found from any of the specified senders")
                else:
                    logger.info(f"No new emails found from {sender_email}")
                return []

            # Get full message details for each ID
            emails = []
            for message in messages:
                msg_id = message["id"]
                logger.debug(f"Retrieving email with ID: {msg_id}")

                try:
                    email_data = self._get_email_data(msg_id)
                    if email_data:
                        emails.append(email_data)
                except HttpError as error:
                    status_code = error.resp.status
                    logger.error(
                        f"Error retrieving email {msg_id}: HTTP {status_code} - {error}"
                    )

                    # If this is a rate limit error, pause briefly before continuing
                    if status_code == 429:
                        logger.warning("Rate limit exceeded, pausing before continuing")
                        time.sleep(2)
                    continue

            return emails

        except HttpError as error:
            status_code = error.resp.status
            logger.error(f"Error searching for emails: HTTP {status_code} - {error}")
            return []

    def _execute_with_retry(
        self, request_func: Callable[[], T], max_retries: Optional[int] = None
    ) -> T:
        """Execute a request with retry for transient errors.

        Args:
            request_func: Function that makes the API request
            max_retries: Maximum number of retries (defaults to self.MAX_RETRIES)

        Returns:
            API response

        Raises:
            HttpError: If the request fails after all retries
        """
        if max_retries is None:
            max_retries = self.MAX_RETRIES

        retry_count = 0
        last_error: Optional[HttpError] = None

        while retry_count <= max_retries:
            try:
                return request_func()
            except HttpError as error:
                last_error = error
                status_code = error.resp.status

                # Only retry for transient errors
                if (
                    status_code in self.TRANSIENT_ERROR_CODES
                    and retry_count < max_retries
                ):
                    retry_count += 1
                    wait_time = 2**retry_count  # Exponential backoff
                    logger.warning(
                        f"Transient error (HTTP {status_code}), "
                        f"retrying in {wait_time}s (attempt {retry_count}/{max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    # Non-transient error or max retries reached
                    raise

        # This should never happen, but just in case
        if last_error:
            raise last_error

        # This should also never happen
        raise RuntimeError("Unexpected error in _execute_with_retry")

    def _get_email_data(self, msg_id: str) -> Optional[Dict[str, Any]]:
        """Get email data for a specific message ID.

        Args:
            msg_id: Gmail message ID

        Returns:
            Dictionary with email data or None if retrieval fails
        """
        try:
            # Get the full message
            message = self._execute_with_retry(
                lambda: self.service.users()
                .messages()
                .get(userId=self.user_id, id=msg_id, format="full")
                .execute()
            )

            # Extract headers
            headers = {
                header["name"].lower(): header["value"]
                for header in message["payload"]["headers"]
            }

            # Get subject, from, and date
            subject = headers.get("subject", "(No Subject)")
            sender = headers.get("from", "")
            date_str = headers.get("date", "")

            # Parse date
            try:
                # Try to parse various date formats
                date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
            except ValueError:
                try:
                    date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
                except ValueError:
                    # Fallback to current date if parsing fails
                    date_obj = datetime.now()
                    logger.warning(
                        f"Could not parse date '{date_str}' for email {msg_id}, using current time"
                    )

            date = date_obj.strftime("%Y-%m-%d %H:%M:%S")

            # Extract body
            body, is_html = self._get_message_body(message)

            return {
                "id": msg_id,
                "subject": subject,
                "sender": sender,
                "date": date,
                "body": body,
                "is_html": is_html,
                "labels": message["labelIds"],
            }

        except HttpError as error:
            status_code = error.resp.status
            logger.error(
                f"Error retrieving email {msg_id}: HTTP {status_code} - {error}"
            )
            return None

    def _get_message_body(self, message: Dict[str, Any]) -> Tuple[str, bool]:
        """Extract the message body from the email.

        Args:
            message: Gmail message object

        Returns:
            Tuple of (body_text, is_html)
        """
        body = ""
        is_html = False

        try:
            if "parts" in message["payload"]:
                # Multipart message
                for part in message["payload"]["parts"]:
                    mime_type = part.get("mimeType", "")

                    # Look for text parts
                    if mime_type == "text/plain":
                        body = self._decode_body(part)
                        is_html = False
                        break
                    elif mime_type == "text/html" and not body:
                        # Use HTML if no plain text is found
                        body = self._decode_body(part)
                        is_html = True
            else:
                # Single part message
                mime_type = message["payload"].get("mimeType", "")
                if mime_type == "text/plain":
                    body = self._decode_body(message["payload"])
                    is_html = False
                elif mime_type == "text/html":
                    body = self._decode_body(message["payload"])
                    is_html = True
        except KeyError as e:
            logger.warning(f"Error extracting message body: {e}")
            body = "(Error extracting message body)"
            is_html = False

        return body, is_html

    def _decode_body(self, part: Dict[str, Any]) -> str:
        """Decode the message body from base64.

        Args:
            part: Message part containing the body

        Returns:
            Decoded body text
        """
        if "body" in part and "data" in part["body"]:
            data = part["body"]["data"]
            # Replace URL-safe characters and add padding
            padded_data = data.replace("-", "+").replace("_", "/")

            # Decode base64
            try:
                decoded_bytes = base64.b64decode(padded_data)
                return decoded_bytes.decode("utf-8")
            except Exception as e:
                logger.error(f"Error decoding message body: {e}")
                return "(Error decoding message)"

        return ""

    def mark_as_read(self, msg_id: str) -> bool:
        """Mark an email as read.

        Args:
            msg_id: Gmail message ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove UNREAD label
            self._execute_with_retry(
                lambda: self.service.users()
                .messages()
                .modify(
                    userId=self.user_id, id=msg_id, body={"removeLabelIds": ["UNREAD"]}
                )
                .execute()
            )
            logger.debug(f"Marked email {msg_id} as read")
            return True
        except HttpError as error:
            status_code = error.resp.status
            logger.error(
                f"Error marking email {msg_id} as read: HTTP {status_code} - {error}"
            )
            return False

    def archive_message(self, msg_id: str) -> bool:
        """Archive an email by removing the INBOX label.

        Args:
            msg_id: Gmail message ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove INBOX label to archive the message
            self._execute_with_retry(
                lambda: self.service.users()
                .messages()
                .modify(
                    userId=self.user_id, id=msg_id, body={"removeLabelIds": ["INBOX"]}
                )
                .execute()
            )
            logger.debug(f"Archived email {msg_id}")
            return True
        except HttpError as error:
            status_code = error.resp.status
            logger.error(
                f"Error archiving email {msg_id}: HTTP {status_code} - {error}"
            )
            return False
