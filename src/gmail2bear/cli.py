"""Command-line interface for Gmail to Bear integration."""

import argparse
import logging
import sys
from pathlib import Path

from gmail2bear import __version__
from gmail2bear.processor import EmailProcessor


def setup_logging(level: int = logging.INFO) -> None:
    """Set up logging configuration.

    Args:
        level: The logging level to use
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(description="Convert Gmail emails to Bear notes.")
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
        "--state",
        type=str,
        default=str(Path.home() / ".gmail2bear" / "state.json"),
        help="Path to state file",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=str(Path.home() / ".gmail2bear" / "token.pickle"),
        help="Path to token file",
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

    # Config command
    config_parser = subparsers.add_parser("config", help="Create default configuration")
    config_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing configuration"
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point for the application.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
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

    # Initialize the processor
    processor = EmailProcessor(
        config_path=args.config,
        credentials_path=args.credentials,
        state_path=args.state,
        token_path=args.token,
    )

    # Handle commands
    if args.command == "run":
        logger.info("Running email processing")

        # First authenticate
        if not processor.authenticate():
            logger.error("Authentication failed, cannot process emails")
            return 1

        # Then process emails
        processed_count = processor.process_emails(once=args.once)
        logger.info(f"Processed {processed_count} emails")

    elif args.command == "auth":
        logger.info("Authenticating with Gmail API")
        if processor.authenticate(force_refresh=args.force):
            logger.info("Authentication successful")
        else:
            logger.error("Authentication failed")
            return 1

    elif args.command == "config":
        from gmail2bear.config import Config

        logger.info("Creating default configuration")
        config = Config(args.config)

        if Path(args.config).exists() and not args.force:
            logger.error(f"Configuration file already exists: {args.config}")
            logger.error("Use --force to overwrite")
            return 1

        if config.create_default_config():
            logger.info(f"Default configuration created at: {args.config}")
            logger.info("Please edit this file with your settings before running")
        else:
            logger.error("Failed to create default configuration")
            return 1

    else:
        logger.error("No command specified")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
