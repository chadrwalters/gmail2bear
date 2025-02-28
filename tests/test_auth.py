"""Tests for the auth module."""

import os
import pickle
from unittest import mock

import pytest
from google.oauth2.credentials import Credentials

from gmail2bear.auth import get_credentials, SCOPES


@pytest.fixture
def mock_credentials_file(tmp_path):
    """Create a mock credentials file."""
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text('{"installed": {"client_id": "test"}}')
    return str(credentials_file)


@pytest.fixture
def mock_token_file(tmp_path):
    """Create a mock token file with valid credentials."""
    token_file = tmp_path / "token.pickle"

    # Create a mock credentials object
    mock_creds = mock.Mock(spec=Credentials)
    mock_creds.valid = True
    mock_creds.expired = False

    # Save to pickle file
    with open(token_file, "wb") as f:
        pickle.dump(mock_creds, f)

    return str(token_file)


@pytest.fixture
def mock_expired_token_file(tmp_path):
    """Create a mock token file with expired credentials."""
    token_file = tmp_path / "expired_token.pickle"

    # Create a mock credentials object
    mock_creds = mock.Mock(spec=Credentials)
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "refresh_token"

    # Save to pickle file
    with open(token_file, "wb") as f:
        pickle.dump(mock_creds, f)

    return str(token_file)


def test_get_credentials_missing_file():
    """Test that get_credentials raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        get_credentials("nonexistent_file.json")


def test_get_credentials_existing_token(mock_credentials_file, mock_token_file):
    """Test that get_credentials loads existing token."""
    with mock.patch("gmail2bear.auth.logger") as mock_logger:
        credentials = get_credentials(
            mock_credentials_file,
            token_path=mock_token_file
        )

    assert credentials is not None
    assert credentials.valid
    mock_logger.debug.assert_called_with(mock.ANY)


def test_get_credentials_force_refresh(mock_credentials_file, mock_token_file):
    """Test that get_credentials forces refresh when requested."""
    with mock.patch("gmail2bear.auth.InstalledAppFlow") as mock_flow:
        mock_flow.from_client_secrets_file.return_value.run_local_server.return_value = mock.Mock(spec=Credentials)

        get_credentials(
            mock_credentials_file,
            token_path=mock_token_file,
            force_refresh=True
        )

    mock_flow.from_client_secrets_file.assert_called_once_with(
        mock_credentials_file, SCOPES
    )


def test_get_credentials_expired_token(mock_credentials_file, mock_expired_token_file):
    """Test that get_credentials refreshes expired token."""
    with mock.patch("gmail2bear.auth.Request") as mock_request:
        with mock.patch("gmail2bear.auth.logger"):
            get_credentials(
                mock_credentials_file,
                token_path=mock_expired_token_file
            )

    # Check that refresh was attempted
    assert mock_request.called


def test_get_credentials_refresh_error(mock_credentials_file, mock_expired_token_file):
    """Test that get_credentials handles refresh errors."""
    with mock.patch("gmail2bear.auth.Request") as mock_request:
        # Make refresh raise an exception
        mock_request.side_effect = Exception("Refresh error")

        with mock.patch("gmail2bear.auth.InstalledAppFlow") as mock_flow:
            mock_flow.from_client_secrets_file.return_value.run_local_server.return_value = mock.Mock(spec=Credentials)

            with mock.patch("gmail2bear.auth.logger"):
                get_credentials(
                    mock_credentials_file,
                    token_path=mock_expired_token_file
                )

    # Check that flow was run after refresh failed
    mock_flow.from_client_secrets_file.assert_called_once_with(
        mock_credentials_file, SCOPES
    )
