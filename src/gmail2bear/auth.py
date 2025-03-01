"""Gmail API authentication module.

This module handles OAuth2 authentication with the Gmail API.
"""

import json
import logging
import os
import pickle
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Gmail API scopes
# https://developers.google.com/gmail/api/auth/scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

logger = logging.getLogger(__name__)


class KeychainManager:
    """Manager for macOS Keychain integration."""

    def __init__(self, service_name: str = "Gmail to Bear"):
        """Initialize the Keychain manager.

        Args:
            service_name: Name of the service in Keychain
        """
        self.service_name = service_name
        self.enabled = self._is_supported()

    def _is_supported(self) -> bool:
        """Check if Keychain is supported on this system.

        Returns:
            True if supported, False otherwise
        """
        return platform.system() == "Darwin"

    def store_token(self, account: str, token_data: Dict[str, Any]) -> bool:
        """Store a token in Keychain.

        Args:
            account: Account identifier (e.g., email address)
            token_data: Token data to store

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.warning("Keychain not supported on this system")
            return False

        try:
            # Convert token data to JSON string
            token_json = json.dumps(token_data)

            # Use security command-line tool to store in Keychain
            cmd = [
                "security",
                "add-generic-password",
                "-a",
                account,
                "-s",
                self.service_name,
                "-w",
                token_json,
                "-U",  # Update if exists
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode != 0:
                # If the item already exists, try to update it
                if "already exists" in result.stderr:
                    logger.debug("Token already exists in Keychain, updating")
                    cmd = [
                        "security",
                        "delete-generic-password",
                        "-a",
                        account,
                        "-s",
                        self.service_name,
                    ]
                    subprocess.run(cmd, capture_output=True, check=False)
                    return self.store_token(account, token_data)
                else:
                    logger.error(f"Error storing token in Keychain: {result.stderr}")
                    return False

            logger.debug(f"Stored token in Keychain for {account}")
            return True

        except Exception as e:
            logger.error(f"Error storing token in Keychain: {e}")
            return False

    def retrieve_token(self, account: str) -> Optional[Dict[str, Any]]:
        """Retrieve a token from Keychain.

        Args:
            account: Account identifier (e.g., email address)

        Returns:
            Token data if found, None otherwise
        """
        if not self.enabled:
            logger.warning("Keychain not supported on this system")
            return None

        try:
            # Use security command-line tool to retrieve from Keychain
            cmd = [
                "security",
                "find-generic-password",
                "-a",
                account,
                "-s",
                self.service_name,
                "-w",  # Get password
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode != 0:
                logger.warning(f"Token not found in Keychain for {account}")
                return None

            # Parse JSON string to token data
            token_json = result.stdout.strip()
            token_data = json.loads(token_json)
            logger.debug(f"Retrieved token from Keychain for {account}")
            return token_data

        except Exception as e:
            logger.error(f"Error retrieving token from Keychain: {e}")
            return None

    def delete_token(self, account: str) -> bool:
        """Delete a token from Keychain.

        Args:
            account: Account identifier (e.g., email address)

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.warning("Keychain not supported on this system")
            return False

        try:
            # Use security command-line tool to delete from Keychain
            cmd = [
                "security",
                "delete-generic-password",
                "-a",
                account,
                "-s",
                self.service_name,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode != 0:
                logger.warning(f"Token not found in Keychain for {account}")
                return False

            logger.debug(f"Deleted token from Keychain for {account}")
            return True

        except Exception as e:
            logger.error(f"Error deleting token from Keychain: {e}")
            return False


def get_credentials(
    credentials_path: str,
    token_path: Optional[str] = None,
    force_refresh: bool = False,
    use_keychain: bool = False,
    keychain_service_name: str = "Gmail to Bear",
) -> Credentials:
    """Get Gmail API credentials.

    Args:
        credentials_path: Path to the credentials.json file
        token_path: Path to save the token.pickle file (defaults to same directory)
        force_refresh: Force reauthentication even if token exists
        use_keychain: Whether to use macOS Keychain for token storage
        keychain_service_name: Service name for Keychain storage

    Returns:
        Google OAuth2 credentials

    Raises:
        FileNotFoundError: If credentials file doesn't exist
        ValueError: If authentication fails
    """
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Credentials file not found: {credentials_path}")

    # If token_path is not specified, use the same directory as credentials
    if token_path is None:
        token_path = str(Path(credentials_path).parent / "token.pickle")

    credentials = None
    keychain_manager = None
    account_id = None

    # Set up Keychain manager if enabled
    if use_keychain:
        keychain_manager = KeychainManager(keychain_service_name)
        # Use the credentials file path as the account ID
        account_id = os.path.abspath(credentials_path)

        # Try to get credentials from Keychain
        if not force_refresh and keychain_manager.enabled:
            logger.debug("Trying to load token from Keychain")
            token_data = keychain_manager.retrieve_token(account_id)
            if token_data:
                try:
                    credentials = Credentials.from_authorized_user_info(token_data)
                    logger.info("Loaded credentials from Keychain")
                except Exception as e:
                    logger.warning(f"Error loading credentials from Keychain: {e}")
                    credentials = None

    # If not using Keychain or Keychain retrieval failed, try file-based storage
    if not credentials and os.path.exists(token_path) and not force_refresh:
        logger.debug(f"Loading existing token from {token_path}")
        try:
            with open(token_path, "rb") as token:
                credentials = pickle.load(token)
        except (pickle.UnpicklingError, EOFError) as e:
            logger.warning(f"Error loading token: {e}")
            # Continue to get new credentials

    # If credentials don't exist or are invalid, get new ones
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            logger.info("Refreshing expired credentials")
            try:
                credentials.refresh(Request())
            except Exception as err:
                logger.warning(f"Error refreshing credentials: {err}")
                credentials = None

        # If still no valid credentials, run the OAuth flow
        if not credentials:
            logger.info("Running OAuth flow to get new credentials")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES
                )
                credentials = flow.run_local_server(port=0)
            except Exception as err:
                raise ValueError(f"Authentication failed: {err}") from err

        # Save the credentials
        if credentials:
            # Save to Keychain if enabled
            if (
                use_keychain
                and keychain_manager
                and keychain_manager.enabled
                and account_id
            ):
                logger.debug("Saving credentials to Keychain")
                token_data = json.loads(credentials.to_json())
                keychain_manager.store_token(account_id, token_data)

            # Always save to file as fallback
            logger.debug(f"Saving credentials to {token_path}")
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, "wb") as token:
                pickle.dump(credentials, token)

    return credentials


def migrate_to_keychain(
    token_path: str,
    keychain_service_name: str = "Gmail to Bear",
    delete_file: bool = False,
) -> bool:
    """Migrate token from file to Keychain.

    Args:
        token_path: Path to the token.pickle file
        keychain_service_name: Service name for Keychain storage
        delete_file: Whether to delete the token file after migration

    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(token_path):
        logger.error(f"Token file not found: {token_path}")
        return False

    try:
        # Load token from file
        with open(token_path, "rb") as token_file:
            credentials = pickle.load(token_file)

        # Convert to token data
        token_data = json.loads(credentials.to_json())

        # Store in Keychain
        keychain_manager = KeychainManager(keychain_service_name)
        if not keychain_manager.enabled:
            logger.error("Keychain not supported on this system")
            return False

        # Use the token file path as the account ID
        account_id = os.path.abspath(token_path)
        success = keychain_manager.store_token(account_id, token_data)

        if success and delete_file:
            logger.info(f"Deleting token file after successful migration: {token_path}")
            os.remove(token_path)

        return success

    except Exception as e:
        logger.error(f"Error migrating token to Keychain: {e}")
        return False


def get_user_info(credentials: Credentials) -> Dict[str, str]:
    """Get user information from Gmail API.

    Args:
        credentials: Google OAuth2 credentials

    Returns:
        Dictionary with user information
    """
    # This is a placeholder for now
    # In a real implementation, we would make an API call to get user info
    return {"email": "user@example.com"}
