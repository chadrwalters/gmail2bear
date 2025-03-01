"""Tests for the auth module."""

import json
import os
import pickle
from unittest import mock

import pytest

from gmail2bear.auth import (
    SCOPES,
    KeychainManager,
    get_credentials,
    migrate_to_keychain,
)


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

    # Create a simple dictionary to represent credentials
    # This avoids the issue with pickling MagicMock objects
    mock_creds_data = {
        "token": "test_token",
        "refresh_token": "test_refresh_token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "scopes": SCOPES,
        "valid": True,
        "expired": False,
    }

    # Save the dictionary to the pickle file
    with open(token_file, "wb") as f:
        pickle.dump(mock_creds_data, f)

    return str(token_file)


@pytest.fixture
def mock_expired_token_file(tmp_path):
    """Create a mock token file with expired credentials."""
    token_file = tmp_path / "expired_token.pickle"

    # Create a simple dictionary to represent expired credentials
    mock_creds_data = {
        "token": "test_token",
        "refresh_token": "test_refresh_token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "scopes": SCOPES,
        "valid": False,
        "expired": True,
    }

    # Save the dictionary to the pickle file
    with open(token_file, "wb") as f:
        pickle.dump(mock_creds_data, f)

    return str(token_file)


@pytest.fixture
def mock_token_data():
    """Create mock token data."""
    return {
        "token": "test_token",
        "refresh_token": "test_refresh_token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "scopes": SCOPES,
    }


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


# New tests for KeychainManager class


def test_keychain_manager_init():
    """Test KeychainManager initialization."""
    # Test with default service name
    manager = KeychainManager()
    assert manager.service_name == "Gmail to Bear"

    # Test with custom service name
    manager = KeychainManager("Custom Service")
    assert manager.service_name == "Custom Service"

    # Test enabled status based on platform
    with mock.patch("platform.system", return_value="Darwin"):
        manager = KeychainManager()
        assert manager.enabled is True

    with mock.patch("platform.system", return_value="Linux"):
        manager = KeychainManager()
        assert manager.enabled is False


def test_keychain_manager_is_supported():
    """Test _is_supported method."""
    manager = KeychainManager()

    with mock.patch("platform.system", return_value="Darwin"):
        assert manager._is_supported() is True

    with mock.patch("platform.system", return_value="Linux"):
        assert manager._is_supported() is False

    with mock.patch("platform.system", return_value="Windows"):
        assert manager._is_supported() is False


def test_keychain_manager_store_token_unsupported():
    """Test store_token method on unsupported platform."""
    with mock.patch("platform.system", return_value="Linux"):
        manager = KeychainManager()
        result = manager.store_token("test_account", {"token": "test"})
        assert result is False


def test_keychain_manager_store_token_success():
    """Test store_token method success case."""
    with mock.patch("platform.system", return_value="Darwin"):
        manager = KeychainManager()

        # Mock subprocess.run to simulate successful execution
        with mock.patch("subprocess.run") as mock_run:
            mock_process = mock.MagicMock()
            mock_process.returncode = 0
            mock_run.return_value = mock_process

            result = manager.store_token("test_account", {"token": "test"})

            assert result is True
            mock_run.assert_called_once()
            # Verify the security command was called with correct arguments
            args = mock_run.call_args[0][0]
            assert args[0] == "security"
            assert args[1] == "add-generic-password"
            assert "test_account" in args
            assert "Gmail to Bear" in args


def test_keychain_manager_store_token_already_exists():
    """Test store_token method when item already exists."""
    with mock.patch("platform.system", return_value="Darwin"):
        manager = KeychainManager()

        # First call fails with "already exists" error
        with mock.patch("subprocess.run") as mock_run:
            mock_process1 = mock.MagicMock()
            mock_process1.returncode = 1
            mock_process1.stderr = "already exists"

            mock_process2 = mock.MagicMock()
            mock_process2.returncode = 0

            mock_process3 = mock.MagicMock()
            mock_process3.returncode = 0

            mock_run.side_effect = [mock_process1, mock_process2, mock_process3]

            result = manager.store_token("test_account", {"token": "test"})

            assert result is True
            assert mock_run.call_count == 3  # Initial attempt, delete, retry


def test_keychain_manager_store_token_error():
    """Test store_token method error case."""
    with mock.patch("platform.system", return_value="Darwin"):
        manager = KeychainManager()

        # Mock subprocess.run to simulate failed execution
        with mock.patch("subprocess.run") as mock_run:
            mock_process = mock.MagicMock()
            mock_process.returncode = 1
            mock_process.stderr = "some error"
            mock_run.return_value = mock_process

            result = manager.store_token("test_account", {"token": "test"})

            assert result is False


def test_keychain_manager_store_token_exception():
    """Test store_token method exception handling."""
    with mock.patch("platform.system", return_value="Darwin"):
        manager = KeychainManager()

        # Mock subprocess.run to raise an exception
        with mock.patch("subprocess.run", side_effect=Exception("Test error")):
            result = manager.store_token("test_account", {"token": "test"})

            assert result is False


def test_keychain_manager_retrieve_token_unsupported():
    """Test retrieve_token method on unsupported platform."""
    with mock.patch("platform.system", return_value="Linux"):
        manager = KeychainManager()
        result = manager.retrieve_token("test_account")
        assert result is None


def test_keychain_manager_retrieve_token_success(mock_token_data):
    """Test retrieve_token method success case."""
    with mock.patch("platform.system", return_value="Darwin"):
        manager = KeychainManager()

        # Mock subprocess.run to simulate successful execution
        with mock.patch("subprocess.run") as mock_run:
            mock_process = mock.MagicMock()
            mock_process.returncode = 0
            mock_process.stdout = json.dumps(mock_token_data)
            mock_run.return_value = mock_process

            result = manager.retrieve_token("test_account")

            assert result == mock_token_data
            mock_run.assert_called_once()
            # Verify the security command was called with correct arguments
            args = mock_run.call_args[0][0]
            assert args[0] == "security"
            assert args[1] == "find-generic-password"
            assert "test_account" in args
            assert "Gmail to Bear" in args


def test_keychain_manager_retrieve_token_not_found():
    """Test retrieve_token method when token not found."""
    with mock.patch("platform.system", return_value="Darwin"):
        manager = KeychainManager()

        # Mock subprocess.run to simulate token not found
        with mock.patch("subprocess.run") as mock_run:
            mock_process = mock.MagicMock()
            mock_process.returncode = 1
            mock_run.return_value = mock_process

            result = manager.retrieve_token("test_account")

            assert result is None


def test_keychain_manager_retrieve_token_exception():
    """Test retrieve_token method exception handling."""
    with mock.patch("platform.system", return_value="Darwin"):
        manager = KeychainManager()

        # Mock subprocess.run to raise an exception
        with mock.patch("subprocess.run", side_effect=Exception("Test error")):
            result = manager.retrieve_token("test_account")

            assert result is None


def test_keychain_manager_delete_token_unsupported():
    """Test delete_token method on unsupported platform."""
    with mock.patch("platform.system", return_value="Linux"):
        manager = KeychainManager()
        result = manager.delete_token("test_account")
        assert result is False


def test_keychain_manager_delete_token_success():
    """Test delete_token method success case."""
    with mock.patch("platform.system", return_value="Darwin"):
        manager = KeychainManager()

        # Mock subprocess.run to simulate successful execution
        with mock.patch("subprocess.run") as mock_run:
            mock_process = mock.MagicMock()
            mock_process.returncode = 0
            mock_run.return_value = mock_process

            result = manager.delete_token("test_account")

            assert result is True
            mock_run.assert_called_once()
            # Verify the security command was called with correct arguments
            args = mock_run.call_args[0][0]
            assert args[0] == "security"
            assert args[1] == "delete-generic-password"
            assert "test_account" in args
            assert "Gmail to Bear" in args


def test_keychain_manager_delete_token_not_found():
    """Test delete_token method when token not found."""
    with mock.patch("platform.system", return_value="Darwin"):
        manager = KeychainManager()

        # Mock subprocess.run to simulate token not found
        with mock.patch("subprocess.run") as mock_run:
            mock_process = mock.MagicMock()
            mock_process.returncode = 1
            mock_run.return_value = mock_process

            result = manager.delete_token("test_account")

            assert result is False


def test_keychain_manager_delete_token_exception():
    """Test delete_token method exception handling."""
    with mock.patch("platform.system", return_value="Darwin"):
        manager = KeychainManager()

        # Mock subprocess.run to raise an exception
        with mock.patch("subprocess.run", side_effect=Exception("Test error")):
            result = manager.delete_token("test_account")

            assert result is False


# Tests for migrate_to_keychain function


def test_migrate_to_keychain_file_not_found():
    """Test migrate_to_keychain when token file not found."""
    with mock.patch("os.path.exists", return_value=False):
        result = migrate_to_keychain("nonexistent_token.pickle")
        assert result is False


def test_migrate_to_keychain_success(mock_token_file, mock_token_data):
    """Test successful migration to keychain."""
    with mock.patch("os.path.exists", return_value=True):
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=pickle.dumps(mock_token_data))
        ):
            with mock.patch("gmail2bear.auth.Credentials") as mock_credentials:
                mock_creds = mock.MagicMock()
                mock_creds.to_json.return_value = json.dumps(mock_token_data)
                mock_load = mock.MagicMock(return_value=mock_creds)

                with mock.patch("pickle.load", mock_load):
                    with mock.patch("platform.system", return_value="Darwin"):
                        with mock.patch("subprocess.run") as mock_run:
                            mock_process = mock.MagicMock()
                            mock_process.returncode = 0
                            mock_run.return_value = mock_process

                            result = migrate_to_keychain(mock_token_file)

                            assert result is True
                            mock_run.assert_called_once()


def test_migrate_to_keychain_with_delete(mock_token_file, mock_token_data):
    """Test migration to keychain with file deletion."""
    with mock.patch("os.path.exists", return_value=True):
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=pickle.dumps(mock_token_data))
        ):
            with mock.patch("gmail2bear.auth.Credentials") as mock_credentials:
                mock_creds = mock.MagicMock()
                mock_creds.to_json.return_value = json.dumps(mock_token_data)
                mock_load = mock.MagicMock(return_value=mock_creds)

                with mock.patch("pickle.load", mock_load):
                    with mock.patch("platform.system", return_value="Darwin"):
                        with mock.patch("subprocess.run") as mock_run:
                            mock_process = mock.MagicMock()
                            mock_process.returncode = 0
                            mock_run.return_value = mock_process

                            with mock.patch("os.remove") as mock_remove:
                                result = migrate_to_keychain(
                                    mock_token_file, delete_file=True
                                )

                                assert result is True
                                mock_remove.assert_called_once_with(mock_token_file)


def test_migrate_to_keychain_unsupported_platform(mock_token_file):
    """Test migration to keychain on unsupported platform."""
    with mock.patch("os.path.exists", return_value=True):
        with mock.patch("builtins.open", mock.mock_open()):
            with mock.patch("gmail2bear.auth.Credentials") as mock_credentials:
                mock_creds = mock.MagicMock()
                mock_load = mock.MagicMock(return_value=mock_creds)

                with mock.patch("pickle.load", mock_load):
                    with mock.patch("platform.system", return_value="Linux"):
                        result = migrate_to_keychain(mock_token_file)

                        assert result is False


def test_migrate_to_keychain_exception(mock_token_file):
    """Test migration to keychain with exception."""
    with mock.patch("os.path.exists", return_value=True):
        with mock.patch("builtins.open", mock.mock_open()):
            with mock.patch("pickle.load", side_effect=Exception("Test error")):
                result = migrate_to_keychain(mock_token_file)
                assert result is False


# Tests for get_credentials with use_keychain parameter


def test_get_credentials_with_keychain(mock_credentials_file, mock_token_data):
    """Test getting credentials with keychain."""
    # Mock keychain manager
    mock_keychain = mock.MagicMock()
    mock_keychain.retrieve_token.return_value = mock_token_data

    with mock.patch("gmail2bear.auth.KeychainManager", return_value=mock_keychain):
        with mock.patch("gmail2bear.auth.Credentials") as mock_credentials:
            mock_creds = mock.MagicMock()
            mock_from_authorized_user_info = mock.MagicMock(return_value=mock_creds)
            mock_credentials.from_authorized_user_info = mock_from_authorized_user_info

            # Call the function
            credentials = get_credentials(
                credentials_path=mock_credentials_file, use_keychain=True
            )

            # Verify result
            assert credentials is mock_creds
            mock_keychain.retrieve_token.assert_called_once()
            mock_from_authorized_user_info.assert_called_once_with(mock_token_data)


def test_get_credentials_keychain_fallback_to_file(
    mock_credentials_file, mock_token_file
):
    """Test get_credentials fallback to file when keychain retrieval fails."""
    with mock.patch("platform.system", return_value="Darwin"):
        with mock.patch("gmail2bear.auth.KeychainManager") as mock_keychain_manager:
            # Configure the mock keychain manager to fail retrieval
            mock_manager_instance = mock_keychain_manager.return_value
            mock_manager_instance.enabled = True
            mock_manager_instance.retrieve_token.return_value = None

            with mock.patch("os.path.exists", return_value=True):
                with mock.patch("builtins.open", mock.mock_open()):
                    with mock.patch("pickle.load") as mock_load:
                        mock_creds = mock.MagicMock()
                        mock_creds.valid = True
                        mock_load.return_value = mock_creds

                        with mock.patch("gmail2bear.auth.logger"):
                            credentials = get_credentials(
                                mock_credentials_file,
                                mock_token_file,
                                use_keychain=True,
                            )

                            assert credentials is mock_creds
                            mock_manager_instance.retrieve_token.assert_called_once()


def test_get_credentials_save_to_keychain_after_oauth(mock_credentials_file):
    """Test saving credentials to keychain after OAuth flow."""
    # Mock OAuth flow
    mock_flow = mock.MagicMock()
    mock_creds = mock.MagicMock()
    mock_creds.to_json.return_value = (
        '{"token": "test_token", "refresh_token": "test_refresh"}'
    )
    mock_flow.run_local_server.return_value = mock_creds

    # Mock keychain manager
    mock_keychain = mock.MagicMock()

    # Create a temporary token path
    token_path = os.path.join(os.path.dirname(mock_credentials_file), "token.pickle")

    with mock.patch(
        "os.path.exists", side_effect=lambda path: path == mock_credentials_file
    ):
        with mock.patch(
            "gmail2bear.auth.InstalledAppFlow.from_client_secrets_file",
            return_value=mock_flow,
        ):
            with mock.patch(
                "gmail2bear.auth.KeychainManager", return_value=mock_keychain
            ):
                with mock.patch("platform.system", return_value="Darwin"):
                    with mock.patch("pickle.dump") as mock_dump:
                        with mock.patch("os.makedirs"):
                            with mock.patch("builtins.open", mock.mock_open()):
                                # Call the function
                                credentials = get_credentials(
                                    credentials_path=mock_credentials_file,
                                    token_path=token_path,
                                    use_keychain=True,
                                )

                                # Verify result
                                assert credentials is mock_creds
                                mock_keychain.store_token.assert_called_once()
                                mock_dump.assert_called_once()
