"""Tests for the Gmail client module."""

import base64
from unittest import mock

import pytest
from googleapiclient.errors import HttpError

from gmail2bear.gmail_client import GmailClient


@pytest.fixture
def mock_credentials():
    """Create mock credentials."""
    return mock.Mock()


@pytest.fixture
def gmail_client(mock_credentials):
    """Create a Gmail client with mock credentials."""
    return GmailClient(mock_credentials)


@pytest.fixture
def mock_message():
    """Create a mock Gmail message."""
    return {
        "id": "12345",
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Subject"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "Date", "value": "Mon, 01 Jan 2023 12:00:00 +0000"}
            ],
            "mimeType": "text/plain",
            "body": {
                "data": base64.b64encode("Test body".encode()).decode()
            }
        }
    }


@pytest.fixture
def mock_multipart_message():
    """Create a mock multipart Gmail message."""
    return {
        "id": "12345",
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Subject"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "Date", "value": "Mon, 01 Jan 2023 12:00:00 +0000"}
            ],
            "mimeType": "multipart/alternative",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": base64.b64encode("Test plain body".encode()).decode()
                    }
                },
                {
                    "mimeType": "text/html",
                    "body": {
                        "data": base64.b64encode("<p>Test HTML body</p>".encode()).decode()
                    }
                }
            ]
        }
    }


def test_gmail_client_init(gmail_client, mock_credentials):
    """Test that GmailClient initializes correctly."""
    assert gmail_client.user_id == "me"
    assert gmail_client.service is not None


def test_get_emails_from_sender_success(gmail_client):
    """Test that get_emails_from_sender successfully retrieves emails."""
    # Mock the Gmail API responses
    mock_list_response = {"messages": [{"id": "12345"}, {"id": "67890"}]}
    mock_get_response = {
        "id": "12345",
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Subject"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "Date", "value": "Mon, 01 Jan 2023 12:00:00 +0000"}
            ],
            "mimeType": "text/plain",
            "body": {
                "data": base64.b64encode("Test body".encode()).decode()
            }
        }
    }

    # Set up the mock service
    gmail_client.service = mock.Mock()
    gmail_client.service.users().messages().list().execute.return_value = mock_list_response
    gmail_client.service.users().messages().get().execute.return_value = mock_get_response

    # Call the method
    emails = gmail_client.get_emails_from_sender("sender@example.com", max_results=2)

    # Check the results
    assert len(emails) == 2
    assert emails[0]["id"] == "12345"
    assert emails[0]["subject"] == "Test Subject"
    assert emails[0]["sender"] == "sender@example.com"
    assert emails[0]["body"] == "Test body"
    assert emails[0]["is_html"] is False


def test_get_emails_from_sender_no_emails(gmail_client):
    """Test that get_emails_from_sender handles no emails."""
    # Mock the Gmail API response
    mock_list_response = {}

    # Set up the mock service
    gmail_client.service = mock.Mock()
    gmail_client.service.users().messages().list().execute.return_value = mock_list_response

    # Call the method
    emails = gmail_client.get_emails_from_sender("sender@example.com")

    # Check the results
    assert len(emails) == 0


def test_get_emails_from_sender_http_error(gmail_client):
    """Test that get_emails_from_sender handles HTTP errors."""
    # Set up the mock service to raise an error
    gmail_client.service = mock.Mock()
    gmail_client.service.users().messages().list().execute.side_effect = HttpError(
        resp=mock.Mock(status=500), content=b"Error"
    )

    with mock.patch("gmail2bear.gmail_client.logger") as mock_logger:
        # Call the method
        emails = gmail_client.get_emails_from_sender("sender@example.com")

    # Check the results
    assert len(emails) == 0
    mock_logger.error.assert_called_once_with(mock.ANY)


def test_get_emails_from_sender_filter_processed(gmail_client):
    """Test that get_emails_from_sender filters processed emails."""
    # Mock the Gmail API response
    mock_list_response = {"messages": [{"id": "12345"}, {"id": "67890"}]}

    # Set up the mock service
    gmail_client.service = mock.Mock()
    gmail_client.service.users().messages().list().execute.return_value = mock_list_response

    # Call the method with processed IDs
    emails = gmail_client.get_emails_from_sender(
        "sender@example.com",
        processed_ids=["12345", "67890"]
    )

    # Check the results
    assert len(emails) == 0


def test_get_email_data_success(gmail_client, mock_message):
    """Test that _get_email_data successfully retrieves email data."""
    # Set up the mock service
    gmail_client.service = mock.Mock()
    gmail_client.service.users().messages().get().execute.return_value = mock_message

    # Call the method
    email_data = gmail_client._get_email_data("12345")

    # Check the results
    assert email_data["id"] == "12345"
    assert email_data["subject"] == "Test Subject"
    assert email_data["sender"] == "sender@example.com"
    assert email_data["body"] == "Test body"
    assert email_data["is_html"] is False


def test_get_email_data_http_error(gmail_client):
    """Test that _get_email_data handles HTTP errors."""
    # Set up the mock service to raise an error
    gmail_client.service = mock.Mock()
    gmail_client.service.users().messages().get().execute.side_effect = HttpError(
        resp=mock.Mock(status=500), content=b"Error"
    )

    with mock.patch("gmail2bear.gmail_client.logger") as mock_logger:
        # Call the method
        email_data = gmail_client._get_email_data("12345")

    # Check the results
    assert email_data is None
    mock_logger.error.assert_called_once_with(mock.ANY)


def test_get_message_body_plain(gmail_client, mock_message):
    """Test that _get_message_body extracts plain text body."""
    # Call the method
    body, is_html = gmail_client._get_message_body(mock_message)

    # Check the results
    assert body == "Test body"
    assert is_html is False


def test_get_message_body_multipart(gmail_client, mock_multipart_message):
    """Test that _get_message_body extracts body from multipart message."""
    # Call the method
    body, is_html = gmail_client._get_message_body(mock_multipart_message)

    # Check the results
    assert body == "Test plain body"
    assert is_html is False


def test_mark_as_read_success(gmail_client):
    """Test that mark_as_read successfully marks an email as read."""
    # Set up the mock service
    gmail_client.service = mock.Mock()

    # Call the method
    result = gmail_client.mark_as_read("12345")

    # Check the results
    assert result is True
    gmail_client.service.users().messages().modify.assert_called_once_with(
        userId="me",
        id="12345",
        body={"removeLabelIds": ["UNREAD"]}
    )


def test_mark_as_read_error(gmail_client):
    """Test that mark_as_read handles errors."""
    # Set up the mock service to raise an error
    gmail_client.service = mock.Mock()
    gmail_client.service.users().messages().modify().execute.side_effect = HttpError(
        resp=mock.Mock(status=500), content=b"Error"
    )

    with mock.patch("gmail2bear.gmail_client.logger") as mock_logger:
        # Call the method
        result = gmail_client.mark_as_read("12345")

    # Check the results
    assert result is False
    mock_logger.error.assert_called_once_with(mock.ANY)
