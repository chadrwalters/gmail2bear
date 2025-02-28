"""Bear integration module.

This module handles interactions with the Bear note-taking app.
"""

import logging
import re
import subprocess
import urllib.parse
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BearClient:
    """Client for interacting with Bear via x-callback-url."""

    def __init__(self):
        """Initialize the Bear client."""
        self.base_url = "bear://x-callback-url"

    def create_note(
        self,
        title: str,
        body: str,
        tags: Optional[List[str]] = None,
        id_suffix: Optional[str] = None
    ) -> bool:
        """Create a new note in Bear.

        Args:
            title: Note title
            body: Note body
            tags: List of tags to add to the note
            id_suffix: Optional suffix to add to the note ID for uniqueness

        Returns:
            True if successful, False otherwise
        """
        # Prepare tags
        tag_string = ""
        if tags:
            # Format tags for Bear (space-separated with # prefix)
            tag_string = " ".join([f"#{tag}" for tag in tags])

        # Add tags to the body
        if tag_string:
            body = f"{body}\n\n{tag_string}"

        # Add ID suffix if provided
        if id_suffix:
            body = f"{body}\n\nID: {id_suffix}"

        # Construct the URL
        params = {
            "title": title,
            "text": body,
            "open_note": "no"  # Don't open the note after creation
        }

        url = self._build_url("create", params)

        # Call the URL using macOS open command
        return self._call_url(url)

    def _build_url(self, action: str, params: Dict[str, str]) -> str:
        """Build a Bear x-callback-url.

        Args:
            action: The Bear action to perform
            params: Dictionary of parameters

        Returns:
            Formatted URL string
        """
        # URL encode all parameters
        encoded_params = "&".join([
            f"{key}={urllib.parse.quote(str(value))}"
            for key, value in params.items()
        ])

        return f"{self.base_url}/{action}?{encoded_params}"

    def _call_url(self, url: str) -> bool:
        """Call a Bear URL using the macOS open command.

        Args:
            url: The URL to call

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.debug(f"Calling Bear URL: {url[:100]}...")  # Log only the beginning for privacy

            # Use subprocess to call the macOS open command
            result = subprocess.run(
                ["open", url],
                check=True,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.debug("Successfully created note in Bear")
                return True
            else:
                logger.error(f"Error creating note in Bear: {result.stderr}")
                return False

        except subprocess.SubprocessError as e:
            logger.error(f"Error calling Bear URL: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error calling Bear URL: {e}")
            return False
