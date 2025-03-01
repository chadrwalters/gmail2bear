"""Tests for the CLI module."""

from unittest import mock

import pytest
from gmail2bear import cli


@pytest.fixture
def mock_args():
    """Create mock command-line arguments."""
    args = mock.MagicMock()
    args.config = "config.ini"
    args.credentials = "credentials.json"
    args.state = "state.txt"
    args.token = "token.pickle"
    args.once = False
    args.force_refresh = False
    args.init_config = False
    args.debug = False
    args.command = "run"
    return args


def test_version():
    """Test that the version is defined."""
    from gmail2bear import __version__

    assert __version__ is not None


def test_setup_logging():
    """Test that setup_logging configures logging correctly."""
    with mock.patch("logging.getLogger") as mock_get_logger:
        with mock.patch("gmail2bear.cli.Config") as mock_config_class:
            mock_config = mock.MagicMock()
            mock_config.loaded = True
            mock_config.get_logging_level.return_value = "INFO"
            mock_config.get_log_file.return_value = None
            mock_config_class.return_value = mock_config

            cli.setup_logging("config.ini")

            mock_get_logger.assert_called()
            mock_config.get_logging_level.assert_called_once()


def test_parse_args():
    """Test that parse_args parses arguments correctly."""
    with mock.patch("sys.argv", ["gmail2bear", "run", "--once"]):
        args = cli.parse_args()
        assert args.once is True
        assert args.command == "run"


def test_parse_args_defaults():
    """Test the default argument values."""
    with mock.patch("sys.argv", ["gmail2bear", "run"]):
        args = cli.parse_args()
        assert args.once is False
        assert args.force_refresh is False
        assert args.command == "run"
        assert "config.ini" in args.config
        assert "credentials.json" in args.credentials
        assert "token.pickle" in args.token
        assert "state.txt" in args.state


def test_parse_args_init_config():
    """Test the --init-config argument."""
    with mock.patch("sys.argv", ["gmail2bear", "init-config"]):
        args = cli.parse_args()
        assert args.command == "init-config"


def test_parse_args_force_refresh():
    """Test the --force-refresh argument."""
    with mock.patch("sys.argv", ["gmail2bear", "run", "--force-refresh"]):
        args = cli.parse_args()
        assert args.force_refresh is True
        assert args.command == "run"


def test_parse_args_once():
    """Test the --once argument."""
    with mock.patch("sys.argv", ["gmail2bear", "run", "--once"]):
        args = cli.parse_args()
        assert args.once is True
        assert args.command == "run"


def test_main_init_config_success():
    """Test main with --init-config (success)."""
    with mock.patch("gmail2bear.cli.init_config_command") as mock_init_config:
        mock_init_config.return_value = 0
        with mock.patch("gmail2bear.cli.parse_args") as mock_parse_args:
            mock_parse_args.return_value = mock.MagicMock(
                config="config.ini",
                credentials="credentials.json",
                state="state.txt",
                token="token.pickle",
                debug=False,
                command="init-config",
            )
            with mock.patch("gmail2bear.cli.setup_logging"):
                result = cli.main()
        assert result == 0
        mock_init_config.assert_called_once()


def test_main_init_config_failure():
    """Test main with --init-config (failure)."""
    with mock.patch("gmail2bear.cli.init_config_command") as mock_init_config:
        mock_init_config.return_value = 1
        with mock.patch("gmail2bear.cli.parse_args") as mock_parse_args:
            mock_parse_args.return_value = mock.MagicMock(
                config="config.ini",
                credentials="credentials.json",
                state="state.txt",
                token="token.pickle",
                debug=False,
                command="init-config",
            )
            with mock.patch("gmail2bear.cli.setup_logging"):
                result = cli.main()
        assert result == 1
        mock_init_config.assert_called_once()


def test_main_auth_failure():
    """Test main with authentication failure."""
    with mock.patch("gmail2bear.cli.run_command") as mock_run_command:
        mock_run_command.return_value = 1
        with mock.patch("gmail2bear.cli.parse_args") as mock_parse_args:
            mock_parse_args.return_value = mock.MagicMock(
                force_refresh=False,
                once=True,
                config="config.ini",
                credentials="credentials.json",
                state="state.txt",
                token="token.pickle",
                debug=False,
                command="run",
            )
            with mock.patch("gmail2bear.cli.setup_logging"):
                result = cli.main()
        assert result == 1
        mock_run_command.assert_called_once()


def test_main_process_success():
    """Test main with successful processing."""
    with mock.patch("gmail2bear.cli.run_command") as mock_run_command:
        mock_run_command.return_value = 0
        with mock.patch("gmail2bear.cli.parse_args") as mock_parse_args:
            mock_parse_args.return_value = mock.MagicMock(
                force_refresh=False,
                once=True,
                config="config.ini",
                credentials="credentials.json",
                state="state.txt",
                token="token.pickle",
                debug=False,
                command="run",
            )
            with mock.patch("gmail2bear.cli.setup_logging"):
                result = cli.main()
        assert result == 0
        mock_run_command.assert_called_once()


def test_main_process_exception():
    """Test main with exception during processing."""
    with mock.patch("gmail2bear.cli.run_command") as mock_run_command:
        mock_run_command.return_value = 1
        with mock.patch("gmail2bear.cli.parse_args") as mock_parse_args:
            mock_parse_args.return_value = mock.MagicMock(
                force_refresh=False,
                once=True,
                config="config.ini",
                credentials="credentials.json",
                state="state.txt",
                token="token.pickle",
                debug=False,
                command="run",
            )
            with mock.patch("gmail2bear.cli.setup_logging"):
                result = cli.main()
        assert result == 1
        mock_run_command.assert_called_once()


def test_main_keyboard_interrupt():
    """Test main with keyboard interrupt during processing."""
    with mock.patch("gmail2bear.cli.run_command") as mock_run_command:
        mock_run_command.return_value = 0
        with mock.patch("gmail2bear.cli.parse_args") as mock_parse_args:
            mock_parse_args.return_value = mock.MagicMock(
                force_refresh=False,
                once=True,
                config="config.ini",
                credentials="credentials.json",
                state="state.txt",
                token="token.pickle",
                debug=False,
                command="run",
            )
            with mock.patch("gmail2bear.cli.setup_logging"):
                result = cli.main()
        assert result == 0
        mock_run_command.assert_called_once()
