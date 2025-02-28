"""Tests for the CLI module."""

import sys
from unittest import mock

import pytest
from gmail2bear import cli


@pytest.fixture
def mock_args():
    """Create mock command-line arguments."""
    args = mock.MagicMock()
    args.config = "config.ini"
    args.credentials = "credentials.json"
    args.state = "state.json"
    args.token = "token.pickle"
    args.verbose = False
    args.command = None
    return args


def test_version():
    """Test that the version is defined."""
    from gmail2bear import __version__

    assert __version__ is not None


def test_setup_logging():
    """Test that setup_logging configures logging correctly."""
    with mock.patch("logging.basicConfig") as mock_basic_config:
        cli.setup_logging(level=20)  # INFO level
        mock_basic_config.assert_called_once()


def test_parse_args():
    """Test that parse_args parses arguments correctly."""
    with mock.patch("sys.argv", ["gmail2bear", "--verbose"]):
        args = cli.parse_args()
        assert args.verbose is True


def test_parse_args_version(capsys):
    """Test the --version argument."""
    with pytest.raises(SystemExit) as excinfo:
        with mock.patch.object(sys, "argv", ["gmail2bear", "--version"]):
            cli.parse_args()
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "gmail2bear" in captured.out


def test_parse_args_run():
    """Test the run command."""
    with mock.patch.object(sys, "argv", ["gmail2bear", "run"]):
        args = cli.parse_args()
    assert args.command == "run"
    assert not args.once


def test_parse_args_run_once():
    """Test the run --once command."""
    with mock.patch.object(sys, "argv", ["gmail2bear", "run", "--once"]):
        args = cli.parse_args()
    assert args.command == "run"
    assert args.once


def test_parse_args_auth():
    """Test the auth command."""
    with mock.patch.object(sys, "argv", ["gmail2bear", "auth"]):
        args = cli.parse_args()
    assert args.command == "auth"
    assert not args.force


def test_parse_args_auth_force():
    """Test the auth --force command."""
    with mock.patch.object(sys, "argv", ["gmail2bear", "auth", "--force"]):
        args = cli.parse_args()
    assert args.command == "auth"
    assert args.force


def test_main_no_command():
    """Test main with no command."""
    with mock.patch.object(sys, "argv", ["gmail2bear"]):
        with mock.patch("gmail2bear.cli.parse_args") as mock_parse_args:
            mock_parse_args.return_value = mock.MagicMock(command=None, verbose=False)
            with mock.patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                result = cli.main()
    assert result == 1


def test_main_auth_success():
    """Test main with auth command (success)."""
    with mock.patch.object(sys, "argv", ["gmail2bear", "auth"]):
        with mock.patch("gmail2bear.cli.parse_args") as mock_parse_args:
            mock_parse_args.return_value = mock.MagicMock(
                command="auth",
                verbose=False,
                force=False,
                config="config.ini",
                credentials="credentials.json",
                state="state.json",
                token="token.pickle",
            )
            with mock.patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                with mock.patch(
                    "gmail2bear.cli.EmailProcessor"
                ) as mock_processor_class:
                    mock_processor = mock.MagicMock()
                    mock_processor.authenticate.return_value = True
                    mock_processor_class.return_value = mock_processor
                    result = cli.main()
    assert result == 0


def test_main_auth_failure():
    """Test main with auth command (failure)."""
    with mock.patch.object(sys, "argv", ["gmail2bear", "auth"]):
        with mock.patch("gmail2bear.cli.parse_args") as mock_parse_args:
            mock_parse_args.return_value = mock.MagicMock(
                command="auth",
                verbose=False,
                force=False,
                config="config.ini",
                credentials="credentials.json",
                state="state.json",
                token="token.pickle",
            )
            with mock.patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                with mock.patch(
                    "gmail2bear.cli.EmailProcessor"
                ) as mock_processor_class:
                    mock_processor = mock.MagicMock()
                    mock_processor.authenticate.return_value = False
                    mock_processor_class.return_value = mock_processor
                    result = cli.main()
    assert result == 1


def test_main_config_new():
    """Test main with config command (new file)."""
    with mock.patch.object(sys, "argv", ["gmail2bear", "config"]):
        with mock.patch("gmail2bear.cli.parse_args") as mock_parse_args:
            mock_parse_args.return_value = mock.MagicMock(
                command="config", verbose=False, force=False, config="config.ini"
            )
            with mock.patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = False
                with mock.patch(
                    "gmail2bear.config.Config.create_default_config"
                ) as mock_create_default:
                    mock_create_default.return_value = True
                    result = cli.main()
    assert result == 0


def test_main_config_existing_no_force():
    """Test main with config command (existing file, no force)."""
    with mock.patch.object(sys, "argv", ["gmail2bear", "config"]):
        with mock.patch("gmail2bear.cli.parse_args") as mock_parse_args:
            mock_parse_args.return_value = mock.MagicMock(
                command="config", verbose=False, force=False, config="config.ini"
            )
            with mock.patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                result = cli.main()
    assert result == 1


def test_main_run():
    """Test main with run command."""
    with mock.patch.object(sys, "argv", ["gmail2bear", "run"]):
        with mock.patch("gmail2bear.cli.parse_args") as mock_parse_args:
            mock_args = mock.MagicMock(
                command="run",
                verbose=False,
                once=True,
                config="config.ini",
                credentials="credentials.json",
                state="state.json",
                token="token.pickle",
            )
            mock_parse_args.return_value = mock_args

            with mock.patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True

                with mock.patch(
                    "gmail2bear.cli.EmailProcessor"
                ) as mock_processor_class:
                    mock_processor = mock.MagicMock()
                    # Make authenticate return True
                    mock_processor.authenticate.return_value = True
                    # Make process_emails return a positive count
                    mock_processor.process_emails.return_value = 1
                    mock_processor_class.return_value = mock_processor

                    result = cli.main()

    assert result == 0
    mock_processor.authenticate.assert_called_once()
    mock_processor.process_emails.assert_called_once_with(once=True)
