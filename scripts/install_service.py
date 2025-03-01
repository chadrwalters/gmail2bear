#!/usr/bin/env python3
"""Installation script for Gmail to Bear service.

This script helps with installing and setting up the Gmail to Bear service.
"""

import argparse
import os
import platform
import subprocess
import sys


def check_requirements() -> bool:
    """Check if all requirements are met.

    Returns:
        True if all requirements are met, False otherwise
    """
    # Check if running on macOS
    if platform.system() != "Darwin":
        print("Error: This script is only supported on macOS.")
        return False

    # Check if Python 3.8+ is installed
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required.")
        return False

    # Check if UV is installed, if not check for pip
    global use_uv
    use_uv = False

    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True, text=True)
        use_uv = True
        print("UV detected. Will use UV for package installation.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("UV not found. Checking for pip...")
        try:
            subprocess.run(
                ["pip", "--version"], check=True, capture_output=True, text=True
            )
            print("pip detected. Will use pip for package installation.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: Neither UV nor pip is installed or not in PATH.")
            print("Please install UV (recommended) or pip to continue.")
            return False

    return True


def install_package() -> bool:
    """Install the Gmail to Bear package.

    Returns:
        True if successful, False otherwise
    """
    try:
        # Install the package in development mode
        if use_uv:
            subprocess.run(
                ["uv", "pip", "install", "-e", "."],
                check=True,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            )
            print("Gmail to Bear package installed successfully using UV.")
        else:
            subprocess.run(
                ["pip", "install", "-e", "."],
                check=True,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            )
            print("Gmail to Bear package installed successfully using pip.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing Gmail to Bear package: {e.stderr}")
        return False


def create_config(config_path: str) -> bool:
    """Create the default configuration file.

    Args:
        config_path: Path to the configuration file

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create the config directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # Run the init-config command
        subprocess.run(
            ["gmail2bear", "init-config", "--config", config_path],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"Default configuration created at {config_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating default configuration: {e.stderr}")
        return False


def install_service(args: argparse.Namespace) -> bool:
    """Install the Gmail to Bear service.

    Args:
        args: Command-line arguments

    Returns:
        True if successful, False otherwise
    """
    try:
        # Build the command
        cmd = ["gmail2bear", "service", "install"]

        # Add options
        cmd.extend(["--config", args.config])
        cmd.extend(["--credentials", args.credentials])
        cmd.extend(["--token", args.token])
        cmd.extend(["--state", args.state])

        if args.poll_interval:
            cmd.extend(["--poll-interval", str(args.poll_interval)])

        # Run the command
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Gmail to Bear service installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing Gmail to Bear service: {e.stderr}")
        return False


def main() -> int:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Install and set up the Gmail to Bear service"
    )

    parser.add_argument(
        "--config",
        default=os.path.expanduser("~/.gmail2bear/config.ini"),
        help="Path to configuration file",
    )

    parser.add_argument(
        "--credentials",
        default=os.path.expanduser("~/.gmail2bear/credentials.json"),
        help="Path to Google API credentials file",
    )

    parser.add_argument(
        "--token",
        default=os.path.expanduser("~/.gmail2bear/token.pickle"),
        help="Path to OAuth token file",
    )

    parser.add_argument(
        "--state",
        default=os.path.expanduser("~/.gmail2bear/state.txt"),
        help="Path to state file for tracking processed emails",
    )

    parser.add_argument(
        "--poll-interval",
        type=int,
        default=300,
        help="Polling interval in seconds",
    )

    parser.add_argument(
        "--skip-package-install",
        action="store_true",
        help="Skip installing the Gmail to Bear package",
    )

    parser.add_argument(
        "--skip-config-creation",
        action="store_true",
        help="Skip creating the default configuration file",
    )

    args = parser.parse_args()

    # Check requirements
    if not check_requirements():
        return 1

    # Install the package
    if not args.skip_package_install:
        if not install_package():
            return 1

    # Create the default configuration
    if not args.skip_config_creation and not os.path.exists(args.config):
        if not create_config(args.config):
            return 1

    # Install the service
    if not install_service(args):
        return 1

    print("\nInstallation completed successfully!")
    print("\nNext steps:")
    print(f"1. Edit the configuration file at {args.config}")
    print(f"2. Place your Google API credentials at {args.credentials}")
    print("3. Start the service with: gmail2bear service start")
    print("4. Check the service status with: gmail2bear service status")

    return 0


# Global variable to track if UV is available
use_uv = False

if __name__ == "__main__":
    sys.exit(main())
