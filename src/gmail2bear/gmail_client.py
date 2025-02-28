"""Gmail API client module.

This module handles interactions with the Gmail API.
"""

import base64
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GmailClient:
    """Gmail API client for retrieving emails."""

    def __init__(self, credentials: Credentials):
        """Initialize the Gmail client.

        Args:
            credentials: Google OAuth2 credentials
        """
        self.service = build("gmail", "v1", credentials=credentials)
        self.user_id = "me"  # 'me' refers to the authenticated user

    def get_emails_from_sender(
        self,
        sender_email: str,
        max_results: int = 10,
        only_unread: bool = True,
        processed_ids: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Get emails from a specific sender.

        Args:
            sender_email: Email address of the sender
            max_results: Maximum number of emails to retrieve
            only_unread: Only retrieve unread emails
            processed_ids: List of already processed email IDs to exclude

        Returns:
            List of email dictionaries with id, subject, body, date, and sender
        """
        query = f"from:{sender_email}"
        if only_unread:
            query += " is:unread"

        logger.debug(f"Searching for emails with query: {query}")

        try:
            # Get message IDs matching the query
            results = (
                self.service.users()
                .messages()
                .list(userId=self.user_id, q=query, maxResults=max_results)
                .execute()
            )

            messages = results.get("messages", [])

            if not messages:
                logger.info(f"No emails found from {sender_email}")
                return []

            # Filter out already processed emails
            if processed_ids:
                messages = [msg for msg in messages if msg["id"] not in processed_ids]

            if not messages:
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
                    logger.error(f"Error retrieving email {msg_id}: {error}")
                    continue

            return emails

        except HttpError as error:
            logger.error(f"Error searching for emails: {error}")
            return []

    def _get_email_data(self, msg_id: str) -> Optional[Dict]:
        """Get email data for a specific message ID.

        Args:
            msg_id: Gmail message ID

        Returns:
            Dictionary with email data or None if retrieval fails
        """
        try:
            # Get the full message
            message = (
                self.service.users()
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
            logger.error(f"Error retrieving email {msg_id}: {error}")
            return None

    def _get_message_body(self, message: Dict) -> Tuple[str, bool]:
        """Extract the message body from the email.

        Args:
            message: Gmail message object

        Returns:
            Tuple of (body_text, is_html)
        """
        body = ""
        is_html = False

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

        return body, is_html

    def _decode_body(self, part: Dict) -> str:
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
            self.service.users().messages().modify(
                userId=self.user_id, id=msg_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            logger.debug(f"Marked email {msg_id} as read")
            return True
        except HttpError as error:
            logger.error(f"Error marking email {msg_id} as read: {error}")
            return False
