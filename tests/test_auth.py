"""Tests for the auth module."""

import pickle
from unittest import mock

import pytest
from gmail2bear.auth import SCOPES, get_credentials


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

    # Mock the Credentials class
    with mock.patch("gmail2bear.auth.Credentials") as mock_credentials:
        # Configure the mock to return appropriate values for properties
        mock_instance = mock_credentials.return_value
        mock_instance.valid = True
        mock_instance.expired = False

        # Save the mock to the pickle file
        with open(token_file, "wb") as f:
            pickle.dump(mock_instance, f)

    return str(token_file)


@pytest.fixture
def mock_expired_token_file(tmp_path):
    """Create a mock token file with expired credentials."""
    token_file = tmp_path / "expired_token.pickle"

    # Mock the Credentials class
    with mock.patch("gmail2bear.auth.Credentials") as mock_credentials:
        # Configure the mock to return appropriate values for properties
        mock_instance = mock_credentials.return_value
        mock_instance.valid = False
        mock_instance.expired = True
        mock_instance.refresh_token = "refresh_token"

        # Save the mock to the pickle file
        with open(token_file, "wb") as f:
            pickle.dump(mock_instance, f)

    return str(token_file)


def test_get_credentials_missing_file():
    """Test that get_credentials raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        get_credentials("nonexistent_file.json")


def test_get_credentials_existing_token():
    """Test that get_credentials loads existing token."""
    # For this test, we'll mock everything instead of using the fixtures
    with mock.patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True

        with mock.patch("builtins.open", mock.mock_open()):
            with mock.patch("pickle.load") as mock_load:
                # Create a mock credentials object with the right properties
                mock_creds = mock.MagicMock()
                mock_creds.valid = True
                mock_creds.expired = False
                mock_load.return_value = mock_creds

                with mock.patch("gmail2bear.auth.logger") as mock_logger:
                    with mock.patch("os.makedirs"):
                        credentials = get_credentials(
                            "fake_credentials.json", "fake_token.pickle"
                        )

    assert credentials is not None
    assert credentials.valid
    mock_logger.debug.assert_called_with(mock.ANY)


def test_get_credentials_force_refresh():
    """Test that get_credentials forces refresh when requested."""
    with mock.patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True

        with mock.patch("gmail2bear.auth.InstalledAppFlow") as mock_flow:
            mock_creds = mock.MagicMock()
            flow_instance = mock_flow.from_client_secrets_file.return_value
            flow_instance.run_local_server.return_value = mock_creds

            with mock.patch("builtins.open", mock.mock_open()):
                with mock.patch("pickle.dump"):
                    with mock.patch("os.makedirs"):
                        get_credentials(
                            "fake_credentials.json",
                            "fake_token.pickle",
                            force_refresh=True,
                        )

    mock_flow.from_client_secrets_file.assert_called_once_with(
        "fake_credentials.json", SCOPES
    )


def test_get_credentials_expired_token():
    """Test that get_credentials refreshes expired token."""
    with mock.patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True

        with mock.patch("builtins.open", mock.mock_open()):
            with mock.patch("pickle.load") as mock_load:
                # Create a mock credentials object with expired properties
                mock_creds = mock.MagicMock()
                mock_creds.valid = False
                mock_creds.expired = True
                mock_creds.refresh_token = "refresh_token"
                mock_load.return_value = mock_creds

                with mock.patch("gmail2bear.auth.Request") as mock_request:
                    with mock.patch("pickle.dump"):
                        with mock.patch("gmail2bear.auth.logger"):
                            with mock.patch("os.makedirs"):
                                get_credentials(
                                    "fake_credentials.json", "fake_token.pickle"
                                )

    # Check that refresh was attempted
    assert mock_request.called


def test_get_credentials_refresh_error():
    """Test that get_credentials handles refresh errors."""
    with mock.patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True

        with mock.patch("builtins.open", mock.mock_open()):
            with mock.patch("pickle.load") as mock_load:
                # Create a mock credentials object with expired properties
                mock_creds = mock.MagicMock()
                mock_creds.valid = False
                mock_creds.expired = True
                mock_creds.refresh_token = "refresh_token"
                mock_load.return_value = mock_creds

                with mock.patch("gmail2bear.auth.Request") as mock_request:
                    # Make refresh raise an exception
                    mock_request.side_effect = Exception("Refresh error")

                    with mock.patch("gmail2bear.auth.InstalledAppFlow") as mock_flow:
                        mock_new_creds = mock.MagicMock()
                        flow_return = mock_flow.from_client_secrets_file.return_value
                        flow_return.run_local_server.return_value = mock_new_creds

                        with mock.patch("pickle.dump"):
                            with mock.patch("gmail2bear.auth.logger"):
                                with mock.patch("os.makedirs"):
                                    get_credentials(
                                        "fake_credentials.json", "fake_token.pickle"
                                    )

    # Check that flow was run after refresh failed
    mock_flow.from_client_secrets_file.assert_called_once_with(
        "fake_credentials.json", SCOPES
    )
