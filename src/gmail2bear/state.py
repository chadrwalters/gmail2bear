"""State management module.

This module handles tracking of processed emails to prevent duplicates.
"""

import json
import logging
import os
from typing import List, Set

logger = logging.getLogger(__name__)


class StateManager:
    """Manages the state of processed emails."""

    def __init__(self, state_file_path: str):
        """Initialize the state manager.

        Args:
            state_file_path: Path to the state file
        """
        self.state_file_path = state_file_path
        self.processed_ids: Set[str] = set()
        self._load_state()

    def _load_state(self) -> None:
        """Load the state from the state file."""
        if not os.path.exists(self.state_file_path):
            logger.debug(
                f"State file not found at {self.state_file_path}, creating new state"
            )
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.state_file_path), exist_ok=True)
            self._save_state()
            return

        try:
            with open(self.state_file_path) as f:
                state_data = json.load(f)
                self.processed_ids = set(state_data.get("processed_ids", []))
                logger.debug(
                    f"Loaded {len(self.processed_ids)} processed email IDs from state"
                )
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Error loading state file: {e}")
            # Create a new state file if the existing one is corrupted
            self._save_state()

    def _save_state(self) -> None:
        """Save the state to the state file."""
        try:
            state_data = {"processed_ids": list(self.processed_ids)}

            with open(self.state_file_path, "w") as f:
                json.dump(state_data, f, indent=2)

            logger.debug(
                f"Saved {len(self.processed_ids)} processed email IDs to state file"
            )
        except OSError as e:
            logger.error(f"Error saving state file: {e}")

    def is_processed(self, email_id: str) -> bool:
        """Check if an email has already been processed.

        Args:
            email_id: Gmail message ID

        Returns:
            True if the email has been processed, False otherwise
        """
        return email_id in self.processed_ids

    def mark_as_processed(self, email_id: str) -> None:
        """Mark an email as processed.

        Args:
            email_id: Gmail message ID
        """
        self.processed_ids.add(email_id)
        self._save_state()

    def get_processed_ids(self) -> List[str]:
        """Get the list of processed email IDs.

        Returns:
            List of processed email IDs
        """
        return list(self.processed_ids)

    def clear_state(self) -> None:
        """Clear the state (for testing or resetting)."""
        self.processed_ids.clear()
        self._save_state()
