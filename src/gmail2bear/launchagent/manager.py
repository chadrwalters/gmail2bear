"""Launch Agent manager for Gmail to Bear.

This module provides functionality to install, uninstall, and manage
the macOS Launch Agent for Gmail to Bear.
"""

import logging
import os
import platform
import subprocess
import sys
from string import Template

logger = logging.getLogger(__name__)

# Constants
LAUNCH_AGENT_NAME = "com.gmail2bear"
LAUNCH_AGENT_PLIST = f"{LAUNCH_AGENT_NAME}.plist"
LAUNCH_AGENTS_DIR = os.path.expanduser("~/Library/LaunchAgents")


class LaunchAgentManager:
    """Manager for Gmail to Bear Launch Agent."""

    def __init__(
        self,
        config_path: str,
        credentials_path: str,
        token_path: str,
        state_path: str,
        poll_interval: int = 300,
    ):
        """Initialize the Launch Agent manager.

        Args:
            config_path: Path to the configuration file
            credentials_path: Path to the Google API credentials file
            token_path: Path to the OAuth token file
            state_path: Path to the state file
            poll_interval: Polling interval in seconds (default: 300)
        """
        self.config_path = os.path.abspath(os.path.expanduser(config_path))
        self.credentials_path = os.path.abspath(os.path.expanduser(credentials_path))
        self.token_path = os.path.abspath(os.path.expanduser(token_path))
        self.state_path = os.path.abspath(os.path.expanduser(state_path))
        self.poll_interval = poll_interval
        self.use_uv = self._check_uv_available()

        # Get the template path
        self.template_path = os.path.join(
            os.path.dirname(__file__), "com.gmail2bear.plist.template"
        )
        self.plist_path = os.path.join(LAUNCH_AGENTS_DIR, LAUNCH_AGENT_PLIST)

    def _check_uv_available(self) -> bool:
        """Check if UV is available.

        Returns:
            True if UV is available, False otherwise
        """
        try:
            subprocess.run(
                ["uv", "--version"], check=True, capture_output=True, text=True
            )
            logger.info("UV detected and will be used for running the service")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.info("UV not detected, will use standard Python module import")
            return False

    def is_macos(self) -> bool:
        """Check if the current system is macOS.

        Returns:
            True if the system is macOS, False otherwise
        """
        return platform.system() == "Darwin"

    def is_installed(self) -> bool:
        """Check if the Launch Agent is installed.

        Returns:
            True if installed, False otherwise
        """
        return os.path.exists(self.plist_path)

    def is_running(self) -> bool:
        """Check if the Launch Agent is running.

        Returns:
            True if running, False otherwise
        """
        if not self.is_installed():
            return False

        try:
            # Use launchctl to check if the agent is running
            result = subprocess.run(
                ["launchctl", "list", LAUNCH_AGENT_NAME],
                capture_output=True,
                text=True,
                check=False,
            )
            # If the exit code is 0, the agent is running
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking Launch Agent status: {e}")
            return False

    def install(self) -> bool:
        """Install the Launch Agent.

        Returns:
            True if successful, False otherwise
        """
        if not self.is_macos():
            logger.error("Launch Agent installation is only supported on macOS")
            return False

        # Create LaunchAgents directory if it doesn't exist
        os.makedirs(LAUNCH_AGENTS_DIR, exist_ok=True)

        # Create log directory
        log_dir = os.path.dirname(self.config_path)
        os.makedirs(log_dir, exist_ok=True)

        try:
            # Read the template
            with open(self.template_path) as f:
                template_content = f.read()

            # Get the Python executable path
            python_path = sys.executable

            # Get the current PATH environment variable
            env_path = os.environ.get("PATH", "")

            # Get the PYTHONPATH (if any)
            pythonpath = os.environ.get("PYTHONPATH", "")

            # Replace placeholders in the template
            template = Template(template_content)

            # If UV is available, modify the template to use UV directly
            if self.use_uv:
                # Get the UV executable path
                uv_path = self._get_uv_path()

                # Replace the Python module approach with direct UV command
                template_content = template_content.replace(
                    "<string>${PYTHON_PATH}</string>\n        <string>-m</string>\n        <string>uv.run</string>\n        <string>gmail2bear</string>",
                    f"<string>{uv_path}</string>\n        <string>run</string>\n        <string>gmail2bear</string>",
                )

                # Remove the poll-interval parameter from the run command arguments
                # but keep it for the StartInterval key
                template_content = template_content.replace(
                    "<string>--poll-interval</string>\n        <string>${POLL_INTERVAL}</string>",
                    "",
                )

                template = Template(template_content)
            else:
                # Use direct module import for non-UV approach
                template_content = template_content.replace(
                    "<string>${PYTHON_PATH}</string>\n        <string>-m</string>\n        <string>uv.run</string>\n        <string>gmail2bear</string>",
                    "<string>${PYTHON_PATH}</string>\n        <string>-m</string>\n        <string>gmail2bear.cli</string>",
                )

                # Remove the poll-interval parameter from the run command arguments
                # but keep it for the StartInterval key
                template_content = template_content.replace(
                    "<string>--poll-interval</string>\n        <string>${POLL_INTERVAL}</string>",
                    "",
                )

                template = Template(template_content)

            plist_content = template.substitute(
                PYTHON_PATH=python_path,
                CONFIG_PATH=self.config_path,
                CREDENTIALS_PATH=self.credentials_path,
                TOKEN_PATH=self.token_path,
                STATE_PATH=self.state_path,
                LOG_DIR=log_dir,
                ENV_PATH=env_path,
                PYTHONPATH=pythonpath,
                POLL_INTERVAL=self.poll_interval,
            )

            # Write the plist file
            with open(self.plist_path, "w") as f:
                f.write(plist_content)

            logger.info(f"Created Launch Agent plist at {self.plist_path}")

            # Set proper permissions
            os.chmod(self.plist_path, 0o644)

            # Load the Launch Agent
            self._load_agent()

            logger.info("Launch Agent installed successfully")
            return True

        except Exception as e:
            logger.error(f"Error installing Launch Agent: {e}")
            return False

    def uninstall(self) -> bool:
        """Uninstall the Launch Agent.

        Returns:
            True if successful, False otherwise
        """
        if not self.is_macos():
            logger.error("Launch Agent uninstallation is only supported on macOS")
            return False

        if not self.is_installed():
            logger.info("Launch Agent is not installed")
            return True

        try:
            # Unload the Launch Agent
            self._unload_agent()

            # Remove the plist file
            os.remove(self.plist_path)
            logger.info(f"Removed Launch Agent plist at {self.plist_path}")

            logger.info("Launch Agent uninstalled successfully")
            return True

        except Exception as e:
            logger.error(f"Error uninstalling Launch Agent: {e}")
            return False

    def start(self) -> bool:
        """Start the Launch Agent.

        Returns:
            True if successful, False otherwise
        """
        if not self.is_macos():
            logger.error("Launch Agent management is only supported on macOS")
            return False

        if not self.is_installed():
            logger.error("Launch Agent is not installed")
            return False

        if self.is_running():
            logger.info("Launch Agent is already running")
            return True

        return self._load_agent()

    def stop(self) -> bool:
        """Stop the Launch Agent.

        Returns:
            True if successful, False otherwise
        """
        if not self.is_macos():
            logger.error("Launch Agent management is only supported on macOS")
            return False

        if not self.is_installed():
            logger.error("Launch Agent is not installed")
            return False

        if not self.is_running():
            logger.info("Launch Agent is not running")
            return True

        return self._unload_agent()

    def restart(self) -> bool:
        """Restart the Launch Agent.

        Returns:
            True if successful, False otherwise
        """
        if not self.is_macos():
            logger.error("Launch Agent management is only supported on macOS")
            return False

        if not self.is_installed():
            logger.error("Launch Agent is not installed")
            return False

        # Stop the agent
        if not self.stop():
            return False

        # Start the agent
        return self.start()

    def _load_agent(self) -> bool:
        """Load the Launch Agent using launchctl.

        Returns:
            True if successful, False otherwise
        """
        try:
            subprocess.run(
                ["launchctl", "load", self.plist_path],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info("Launch Agent loaded successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error loading Launch Agent: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error loading Launch Agent: {e}")
            return False

    def _unload_agent(self) -> bool:
        """Unload the Launch Agent using launchctl.

        Returns:
            True if successful, False otherwise
        """
        try:
            subprocess.run(
                ["launchctl", "unload", self.plist_path],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info("Launch Agent unloaded successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error unloading Launch Agent: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error unloading Launch Agent: {e}")
            return False

    def get_status(self) -> dict:
        """Get the status of the Launch Agent.

        Returns:
            Dictionary with status information
        """
        status = {
            "installed": self.is_installed(),
            "running": False,
            "plist_path": self.plist_path,
            "config_path": self.config_path,
            "credentials_path": self.credentials_path,
            "token_path": self.token_path,
            "state_path": self.state_path,
            "using_uv": self.use_uv,
        }

        if status["installed"]:
            status["running"] = self.is_running()

        return status

    def _get_uv_path(self) -> str:
        """Get the path to the UV executable.

        Returns:
            Path to the UV executable
        """
        try:
            # Try to find UV in the PATH
            result = subprocess.run(
                ["which", "uv"], check=True, capture_output=True, text=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Default to /usr/local/bin/uv if not found
            return "/usr/local/bin/uv"
