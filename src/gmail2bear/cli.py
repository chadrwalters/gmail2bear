"""Command-line interface for Gmail to Bear integration."""

import argparse
import logging
import sys
from pathlib import Path

from gmail2bear import __version__


def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert Gmail emails to Bear notes."
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(Path.home() / ".gmail2bear" / "config.ini"),
        help="Path to configuration file",
    )
    parser.add_argument(
        "--credentials",
        type=str,
        default=str(Path.home() / ".gmail2bear" / "credentials.json"),
        help="Path to Google API credentials file",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run the email processing")
    run_parser.add_argument(
        "--once", action="store_true", help="Run once and exit (don't poll)"
    )

    # Auth command
    auth_parser = subparsers.add_parser("auth", help="Authenticate with Gmail API")
    auth_parser.add_argument(
        "--force", action="store_true", help="Force reauthentication"
    )

    return parser.parse_args()


def main():
    """Main entry point for the application."""
    args = parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)

    logger = logging.getLogger("gmail2bear")
    logger.info(f"Gmail to Bear {__version__}")

    # Create config directory if it doesn't exist
    config_dir = Path(args.config).parent
    if not config_dir.exists():
        logger.info(f"Creating configuration directory: {config_dir}")
        config_dir.mkdir(parents=True, exist_ok=True)

    # Handle commands
    if args.command == "run":
        logger.info("Running email processing")
        # TODO: Implement email processing
        logger.warning("Email processing not yet implemented")
    elif args.command == "auth":
        logger.info("Authenticating with Gmail API")
        # TODO: Implement authentication
        logger.warning("Authentication not yet implemented")
    else:
        logger.error("No command specified")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
