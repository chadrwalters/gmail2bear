"""Command-line interface for Gmail to Bear.

This module provides the command-line interface for the Gmail to Bear integration.
"""

import argparse
import logging
import os
import platform
import sys
from logging.handlers import RotatingFileHandler
from typing import List, Optional

from gmail2bear.config import Config
from gmail2bear.launchagent.manager import LaunchAgentManager
from gmail2bear.processor import EmailProcessor

# Default paths
DEFAULT_CONFIG_DIR = os.path.join(os.getcwd(), ".gmail2bear")
DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_CONFIG_DIR, "config.ini")
DEFAULT_CREDENTIALS_PATH = os.path.join(DEFAULT_CONFIG_DIR, "credentials.json")
DEFAULT_TOKEN_PATH = os.path.join(DEFAULT_CONFIG_DIR, "token.pickle")
DEFAULT_STATE_PATH = os.path.join(DEFAULT_CONFIG_DIR, "state.txt")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("gmail2bear")


def setup_logging(config_path: str, level: int = logging.INFO) -> None:
    """Set up logging based on configuration.

    Args:
        config_path: Path to the configuration file
        level: Logging level
    """
    # Create a basic console handler first
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )

    # Set up root logger with console handler
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)

    # Load configuration
    config = Config(config_path)
    if not config.loaded:
        # If config couldn't be loaded, use default level
        root_logger.setLevel(logging.INFO)
        return

    # Set log level from config
    log_level_str = config.get_logging_level()
    log_level = getattr(logging, log_level_str, logging.INFO)
    root_logger.setLevel(log_level)

    # Set up file logging if configured
    log_file = config.get_log_file()
    if log_file:
        try:
            # Get log rotation settings
            max_log_size = config.get_max_log_size()
            backup_count = config.get_log_backup_count()

            # Create rotating file handler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_log_size,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )

            # Add to root logger
            root_logger.addHandler(file_handler)
            logger.info(f"Logging to file: {log_file}")
        except Exception as e:
            logger.error(f"Failed to set up file logging: {e}")


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Command-line arguments (optional)

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Gmail to Bear integration")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Common arguments
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--config",
        "-c",
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to configuration file (default: {DEFAULT_CONFIG_PATH})",
    )
    common_parser.add_argument(
        "--credentials",
        default=DEFAULT_CREDENTIALS_PATH,
        help=f"Path to Google API credentials file (default: {DEFAULT_CREDENTIALS_PATH})",
    )
    common_parser.add_argument(
        "--token",
        default=DEFAULT_TOKEN_PATH,
        help=f"Path to token file (default: {DEFAULT_TOKEN_PATH})",
    )
    common_parser.add_argument(
        "--state",
        default=DEFAULT_STATE_PATH,
        help=f"Path to state file (default: {DEFAULT_STATE_PATH})",
    )
    common_parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )

    # Run command
    run_parser = subparsers.add_parser(
        "run", parents=[common_parser], help="Run the processor"
    )
    run_parser.add_argument(
        "--once", action="store_true", help="Run once and exit (don't poll)"
    )
    run_parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force reauthentication with Gmail API",
    )

    # Init config command
    subparsers.add_parser(
        "init-config", parents=[common_parser], help="Initialize configuration"
    )

    # Service commands
    service_parser = subparsers.add_parser(
        "service", parents=[common_parser], help="Manage the service"
    )
    service_subparsers = service_parser.add_subparsers(
        dest="service_command", help="Service command"
    )

    # Install service command
    install_parser = service_subparsers.add_parser(
        "install", help="Install the service"
    )
    install_parser.add_argument(
        "--poll-interval",
        type=int,
        default=300,
        help="Polling interval in seconds (default: 300)",
    )

    # Uninstall service command
    service_subparsers.add_parser("uninstall", help="Uninstall the service")

    # Start service command
    service_subparsers.add_parser("start", help="Start the service")

    # Stop service command
    service_subparsers.add_parser("stop", help="Stop the service")

    # Restart service command
    service_subparsers.add_parser("restart", help="Restart the service")

    # Status service command
    service_subparsers.add_parser("status", help="Check service status")

    # Security commands
    security_parser = subparsers.add_parser(
        "security", parents=[common_parser], help="Security-related commands"
    )
    security_subparsers = security_parser.add_subparsers(
        dest="security_command", help="Security command"
    )

    # Migrate to keychain command
    keychain_parser = security_subparsers.add_parser(
        "migrate-to-keychain", help="Migrate token from file to Keychain"
    )
    keychain_parser.add_argument(
        "--service-name",
        default="Gmail to Bear",
        help="Keychain service name (default: 'Gmail to Bear')",
    )
    keychain_parser.add_argument(
        "--delete-file",
        action="store_true",
        help="Delete token file after migration",
    )

    # Network commands
    network_parser = subparsers.add_parser(
        "network", parents=[common_parser], help="Network-related commands"
    )
    network_subparsers = network_parser.add_subparsers(
        dest="network_command", help="Network command"
    )

    # Check network command
    network_subparsers.add_parser("check", help="Check network connectivity")

    # System commands
    system_parser = subparsers.add_parser(
        "system", parents=[common_parser], help="System-related commands"
    )
    system_subparsers = system_parser.add_subparsers(
        dest="system_command", help="System command"
    )

    # Send signal command
    signal_parser = system_subparsers.add_parser(
        "signal", help="Send signal to the service"
    )
    signal_parser.add_argument(
        "signal_name",
        choices=["pause", "resume", "reload"],
        help="Signal to send",
    )

    # Parse arguments
    return parser.parse_args(args)


def handle_service_command(args: argparse.Namespace) -> int:
    """Handle service management commands.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code
    """
    # Import here to avoid circular imports

    # Check if running on macOS
    if platform.system() != "Darwin":
        logger.error("Service management is only supported on macOS")
        return 1

    # Create the Launch Agent manager
    manager = LaunchAgentManager(
        config_path=args.config,
        credentials_path=args.credentials,
        token_path=args.token,
        state_path=args.state,
        poll_interval=getattr(args, "poll_interval", 300),
    )

    # Handle the service command
    if args.service_command == "install":
        if manager.install():
            logger.info("Launch Agent installed successfully")
            return 0
        else:
            logger.error("Failed to install Launch Agent")
            return 1
    elif args.service_command == "uninstall":
        if manager.uninstall():
            logger.info("Launch Agent uninstalled successfully")
            return 0
        else:
            logger.error("Failed to uninstall Launch Agent")
            return 1
    elif args.service_command == "start":
        if manager.start():
            logger.info("Launch Agent started successfully")
            return 0
        else:
            logger.error("Failed to start Launch Agent")
            return 1
    elif args.service_command == "stop":
        if manager.stop():
            logger.info("Launch Agent stopped successfully")
            return 0
        else:
            logger.error("Failed to stop Launch Agent")
            return 1
    elif args.service_command == "restart":
        if manager.restart():
            logger.info("Launch Agent restarted successfully")
            return 0
        else:
            logger.error("Failed to restart Launch Agent")
            return 1
    elif args.service_command == "status":
        status = manager.get_status()
        print("Launch Agent status:")
        print(f"  Installed: {'Yes' if status['installed'] else 'No'}")
        print(f"  Running: {'Yes' if status['running'] else 'No'}")
        print(f"  Plist path: {status['plist_path']}")
        print(f"  Config path: {status['config_path']}")
        print(f"  Credentials path: {status['credentials_path']}")
        print(f"  Token path: {status['token_path']}")
        print(f"  State path: {status['state_path']}")
        return 0
    elif args.service_command == "run":
        # Run as a service directly
        processor = EmailProcessor(
            config_path=args.config,
            credentials_path=args.credentials,
            state_path=args.state,
            token_path=args.token,
        )
        # Run the service
        processor.run_service()
        return 0
    else:
        logger.error(f"Unknown service command: {args.service_command}")
        return 1


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for the application.

    Args:
        args: Command-line arguments (optional)

    Returns:
        Exit code
    """
    parsed_args = parse_args(args)

    # Set up logging
    if hasattr(parsed_args, "debug") and parsed_args.debug:
        setup_logging(parsed_args.config, level=logging.DEBUG)
    else:
        setup_logging(parsed_args.config)

    # Create config directory if it doesn't exist
    if hasattr(parsed_args, "config") and parsed_args.config:
        config_dir = os.path.dirname(parsed_args.config)
        if config_dir:  # Only create directory if there is a directory part
            os.makedirs(config_dir, exist_ok=True)

    # Handle commands
    if hasattr(parsed_args, "command"):
        if parsed_args.command == "run":
            return run_command(parsed_args)
        elif parsed_args.command == "init-config":
            return init_config_command(parsed_args)
        elif parsed_args.command == "service":
            return service_command(parsed_args)
        elif parsed_args.command == "security":
            return security_command(parsed_args)
        elif parsed_args.command == "network":
            return network_command(parsed_args)
        elif parsed_args.command == "system":
            return system_command(parsed_args)

    # Special case for tests that use the old command-line format
    if hasattr(parsed_args, "init_config") and parsed_args.init_config:
        # Create processor
        processor = EmailProcessor(
            config_path=parsed_args.config,
            credentials_path=parsed_args.credentials,
            state_path=parsed_args.state,
            token_path=parsed_args.token,
        )
        # Create default config
        if processor.config.create_default_config():
            logger.info(f"Created default configuration at {parsed_args.config}")
            return 0
        else:
            logger.error(
                f"Failed to create default configuration at {parsed_args.config}"
            )
            return 1

    # Default to run command for backward compatibility
    if hasattr(parsed_args, "once"):
        return run_command(parsed_args)

    # If no command specified, print help
    parser = argparse.ArgumentParser(description="Gmail to Bear integration")
    parser.print_help()
    return 1


def run_command(args: argparse.Namespace) -> int:
    """Run the processor.

    Args:
        args: Command-line arguments

    Returns:
        Exit code
    """
    # Initialize processor
    processor = EmailProcessor(
        config_path=args.config,
        credentials_path=args.credentials,
        state_path=args.state,
        token_path=args.token,
    )

    # Authenticate with Gmail API
    if not processor.authenticate(force_refresh=args.force_refresh):
        logger.error("Authentication failed")
        return 1

    # Process emails
    try:
        processed_count = processor.process_emails(once=args.once)
        logger.info(f"Processed {processed_count} emails")
        return 0
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Error processing emails: {e}")
        return 1


def init_config_command(args: argparse.Namespace) -> int:
    """Initialize configuration.

    Args:
        args: Command-line arguments

    Returns:
        Exit code
    """
    # Initialize processor
    processor = EmailProcessor(
        config_path=args.config,
        credentials_path=args.credentials,
        state_path=args.state,
        token_path=args.token,
    )

    logger.info("Initializing default configuration")
    if processor.config.create_default_config():
        logger.info(f"Created default configuration at {args.config}")
        return 0
    else:
        logger.error("Failed to create default configuration")
        return 1


def service_command(args: argparse.Namespace) -> int:
    """Manage the service.

    Args:
        args: Command-line arguments

    Returns:
        Exit code
    """
    # Create service manager
    if hasattr(args, "poll_interval"):
        manager = LaunchAgentManager(
            config_path=args.config,
            credentials_path=args.credentials,
            token_path=args.token,
            state_path=args.state,
            poll_interval=args.poll_interval,
        )
    else:
        manager = LaunchAgentManager(
            config_path=args.config,
            credentials_path=args.credentials,
            token_path=args.token,
            state_path=args.state,
        )

    # Handle service commands
    if args.service_command == "install":
        logger.info("Installing service")
        if manager.install():
            logger.info("Service installed successfully")
            return 0
        else:
            logger.error("Failed to install service")
            return 1
    elif args.service_command == "uninstall":
        logger.info("Uninstalling service")
        if manager.uninstall():
            logger.info("Service uninstalled successfully")
            return 0
        else:
            logger.error("Failed to uninstall service")
            return 1
    elif args.service_command == "start":
        logger.info("Starting service")
        if manager.start():
            logger.info("Service started successfully")
            return 0
        else:
            logger.error("Failed to start service")
            return 1
    elif args.service_command == "stop":
        logger.info("Stopping service")
        if manager.stop():
            logger.info("Service stopped successfully")
            return 0
        else:
            logger.error("Failed to stop service")
            return 1
    elif args.service_command == "restart":
        logger.info("Restarting service")
        if manager.restart():
            logger.info("Service restarted successfully")
            return 0
        else:
            logger.error("Failed to restart service")
            return 1
    elif args.service_command == "status":
        status = manager.get_status()
        if status["installed"]:
            logger.info("Service is installed")
            if status["running"]:
                logger.info(f"Service is running (PID: {status.get('pid', 'unknown')})")
            else:
                logger.info("Service is not running")
        else:
            logger.info("Service is not installed")
        return 0
    else:
        logger.error(f"Unknown service command: {args.service_command}")
        return 1


def security_command(args: argparse.Namespace) -> int:
    """Handle security-related commands.

    Args:
        args: Command-line arguments

    Returns:
        Exit code
    """
    if args.security_command == "migrate-to-keychain":
        logger.info(f"Migrating token from {args.token} to Keychain")
        from gmail2bear.auth import migrate_to_keychain

        success = migrate_to_keychain(args.token, args.service_name, args.delete_file)
        if success:
            logger.info("Token successfully migrated to Keychain")
            return 0
        else:
            logger.error("Failed to migrate token to Keychain")
            return 1
    else:
        logger.error(f"Unknown security command: {args.security_command}")
        return 1


def network_command(args: argparse.Namespace) -> int:
    """Handle network-related commands.

    Args:
        args: Command-line arguments

    Returns:
        Exit code
    """
    if args.network_command == "check":
        # Create a processor instance to use its network check method
        processor = EmailProcessor(
            args.config, args.credentials, args.state, args.token
        )

        # Check network connectivity
        if processor._is_network_available():
            logger.info("Network is available")
            return 0
        else:
            logger.error("Network is not available")
            return 1
    else:
        logger.error(f"Unknown network command: {args.network_command}")
        return 1


def system_command(args: argparse.Namespace) -> int:
    """Handle system-related commands.

    Args:
        args: Command-line arguments

    Returns:
        Exit code
    """
    if args.system_command == "signal":
        # Get the service manager
        manager = LaunchAgentManager(
            args.config, args.credentials, args.token, args.state
        )

        # Check if service is running
        if not manager.is_running():
            logger.error("Service is not running")
            return 1

        # Get the service PID
        status = manager.get_status()
        if "pid" not in status or not status["pid"]:
            logger.error("Could not determine service PID")
            return 1

        pid = status["pid"]

        # Send the appropriate signal
        import signal

        if args.signal_name == "pause":
            logger.info(f"Sending pause signal to service (PID: {pid})")
            os.kill(pid, signal.SIGUSR1)
        elif args.signal_name == "resume":
            logger.info(f"Sending resume signal to service (PID: {pid})")
            os.kill(pid, signal.SIGUSR2)
        elif args.signal_name == "reload":
            logger.info(f"Sending reload signal to service (PID: {pid})")
            os.kill(pid, signal.SIGHUP)
        else:
            logger.error(f"Unknown signal: {args.signal_name}")
            return 1

        return 0
    else:
        logger.error(f"Unknown system command: {args.system_command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
