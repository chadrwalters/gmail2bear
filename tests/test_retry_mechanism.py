"""Tests for the retry mechanism and error handling improvements."""

import time
from unittest import mock

import pytest
from gmail2bear.gmail_client import GmailClient
from gmail2bear.processor import EmailProcessor, retry_on_failure
from googleapiclient.errors import HttpError


def test_retry_on_failure_decorator():
    """Test that the retry_on_failure decorator works correctly."""
    mock_func = mock.Mock()
    mock_func.side_effect = [ConnectionError("Test error"), "success"]
    mock_func.__name__ = "mock_func"  # Add __name__ attribute to the mock

    # Apply the decorator
    decorated_func = retry_on_failure(max_retries=2, initial_backoff=0.1)(mock_func)

    # Call the decorated function
    result = decorated_func()

    # Verify the function was called twice
    assert mock_func.call_count == 2
    assert result == "success"


def test_retry_on_failure_max_retries():
    """Test that the retry_on_failure decorator respects max_retries."""
    mock_func = mock.Mock()
    mock_func.side_effect = [
        ConnectionError("Error 1"),
        ConnectionError("Error 2"),
        ConnectionError("Error 3"),
        "success",
    ]
    mock_func.__name__ = "mock_func"  # Add __name__ attribute to the mock

    # Apply the decorator with max_retries=2
    decorated_func = retry_on_failure(max_retries=2, initial_backoff=0.1)(mock_func)

    # Call the decorated function, should raise after 3 attempts (initial + 2 retries)
    with pytest.raises(ConnectionError):
        decorated_func()

    # Verify the function was called 3 times
    assert mock_func.call_count == 3


def test_retry_on_failure_different_exception():
    """Test that the retry_on_failure decorator only retries specified exceptions."""
    mock_func = mock.Mock()
    mock_func.side_effect = ValueError("Wrong exception")

    # Apply the decorator with retry_exceptions=(ConnectionError,)
    decorated_func = retry_on_failure(
        max_retries=2, initial_backoff=0.1, retry_exceptions=(ConnectionError,)
    )(mock_func)

    # Call the decorated function, should raise immediately
    with pytest.raises(ValueError):
        decorated_func()

    # Verify the function was called only once
    assert mock_func.call_count == 1


def test_gmail_client_execute_with_retry(monkeypatch):
    """Test that the GmailClient._execute_with_retry method works correctly."""
    # Create a mock credentials object
    mock_credentials = mock.Mock()

    # Create a mock service
    mock_service = mock.Mock()

    # Create a real HttpError for the first two attempts
    mock_resp = mock.Mock()
    mock_resp.status = 503  # Service Unavailable
    http_error = HttpError(resp=mock_resp, content=b"Service Unavailable")

    # Mock the build function to return our mock service
    monkeypatch.setattr(
        "gmail2bear.gmail_client.build", mock.Mock(return_value=mock_service)
    )

    # Create a GmailClient instance
    client = GmailClient(mock_credentials)

    # Create a mock request function that fails twice then succeeds
    mock_request = mock.Mock()
    mock_request.side_effect = [http_error, http_error, "success"]

    # Call _execute_with_retry
    with mock.patch("time.sleep") as mock_sleep:  # Mock sleep to speed up test
        result = client._execute_with_retry(mock_request, max_retries=3)

    # Verify the request was called 3 times
    assert mock_request.call_count == 3
    assert result == "success"

    # Verify sleep was called twice (after each failure)
    assert mock_sleep.call_count == 2


def test_gmail_client_execute_with_retry_non_transient_error(monkeypatch):
    """Test that non-transient errors are not retried."""
    # Create a mock credentials object
    mock_credentials = mock.Mock()

    # Create a mock service
    mock_service = mock.Mock()

    # Create a real HttpError with a non-transient status code
    mock_resp = mock.Mock()
    mock_resp.status = 404  # Not Found
    http_error = HttpError(resp=mock_resp, content=b"Not Found")

    # Mock the build function to return our mock service
    monkeypatch.setattr(
        "gmail2bear.gmail_client.build", mock.Mock(return_value=mock_service)
    )

    # Create a GmailClient instance
    client = GmailClient(mock_credentials)

    # Create a mock request function that fails
    mock_request = mock.Mock()
    mock_request.side_effect = http_error

    # Call _execute_with_retry, should raise immediately
    with mock.patch("time.sleep") as mock_sleep:
        with pytest.raises(HttpError):
            client._execute_with_retry(mock_request, max_retries=3)

    # Verify the request was called only once
    assert mock_request.call_count == 1

    # Verify sleep was not called
    assert mock_sleep.call_count == 0


def test_processor_network_check_multiple_dns_servers(monkeypatch, tmp_path):
    """Test that the network check tries multiple DNS servers."""
    # Create temporary files for the processor
    config_file = tmp_path / "config.ini"
    config_file.write_text("[gmail]\nsender_email = test@example.com")

    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text('{"installed": {"client_id": "test"}}')

    state_file = tmp_path / "state.txt"
    state_file.touch()

    # Create a processor instance with mock components
    with mock.patch("gmail2bear.processor.BearClient"), mock.patch(
        "gmail2bear.processor.NotificationManager"
    ), mock.patch("gmail2bear.processor.get_credentials"), mock.patch(
        "gmail2bear.processor.GmailClient"
    ):
        processor = EmailProcessor(
            config_path=str(config_file),
            credentials_path=str(credentials_file),
            state_path=str(state_file),
        )

        # Mock socket.create_connection to fail for the first DNS server but succeed for the second
        def mock_create_connection(address, timeout):
            if address == ("8.8.8.8", 53):  # Google DNS
                raise OSError("Connection failed")
            return mock.Mock()  # Return a mock socket for other addresses

        monkeypatch.setattr("socket.create_connection", mock_create_connection)

        # Check network availability
        result = processor._is_network_available()

        # Verify result is True (second DNS server succeeded)
        assert result is True


def test_processor_consecutive_errors_backoff(monkeypatch, tmp_path):
    """Test that the processor enters error backoff after consecutive errors."""
    # Create temporary files for the processor
    config_file = tmp_path / "config.ini"
    config_file.write_text("[gmail]\nsender_email = test@example.com")

    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text('{"installed": {"client_id": "test"}}')

    state_file = tmp_path / "state.txt"
    state_file.touch()

    # Create a processor instance with mock components
    with mock.patch("gmail2bear.processor.BearClient"), mock.patch(
        "gmail2bear.processor.NotificationManager"
    ), mock.patch("gmail2bear.processor.get_credentials"), mock.patch(
        "gmail2bear.processor.GmailClient"
    ):
        processor = EmailProcessor(
            config_path=str(config_file),
            credentials_path=str(credentials_file),
            state_path=str(state_file),
        )

        # Set up processor state
        processor.running = True
        processor.consecutive_errors = processor.max_consecutive_errors
        processor.last_error_time = time.time()

        # Mock methods
        processor._check_config = mock.Mock()
        processor._check_network = mock.Mock()
        processor.process_emails = mock.Mock()
        processor._interruptible_sleep = mock.Mock(side_effect=KeyboardInterrupt())

        # Run the service
        processor.run_service()

        # Verify process_emails was not called due to being in error backoff
        processor.process_emails.assert_not_called()

        # Verify _interruptible_sleep was called
        processor._interruptible_sleep.assert_called_once()
