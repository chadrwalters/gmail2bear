"""Gmail API authentication module.

This module handles OAuth2 authentication with the Gmail API.
"""

import json
import logging
import os
import pickle
from pathlib import Path
from typing import Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Gmail API scopes
# https://developers.google.com/gmail/api/auth/scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.modify"]

logger = logging.getLogger(__name__)


def get_credentials(
    credentials_path: str, token_path: Optional[str] = None, force_refresh: bool = False
) -> Credentials:
    """Get Gmail API credentials.

    Args:
        credentials_path: Path to the credentials.json file
        token_path: Path to save the token.pickle file (defaults to same directory as credentials)
        force_refresh: Force reauthentication even if token exists

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

    # Load existing token if it exists and we're not forcing refresh
    if os.path.exists(token_path) and not force_refresh:
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
            except Exception as e:
                logger.warning(f"Error refreshing credentials: {e}")
                credentials = None

        # If still no valid credentials, run the OAuth flow
        if not credentials:
            logger.info("Running OAuth flow to get new credentials")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                credentials = flow.run_local_server(port=0)
            except Exception as e:
                raise ValueError(f"Authentication failed: {e}")

        # Save the credentials for future use
        logger.debug(f"Saving credentials to {token_path}")
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, "wb") as token:
            pickle.dump(credentials, token)

    return credentials


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
