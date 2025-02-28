"""Tests for the CLI module."""

import sys
from unittest import mock

import pytest

from gmail2bear import cli


def test_version():
    """Test that the version is defined."""
    from gmail2bear import __version__
    assert __version__ is not None


def test_setup_logging():
    """Test that logging setup works."""
    with mock.patch("logging.basicConfig") as mock_config:
        cli.setup_logging()
        mock_config.assert_called_once()


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
            result = cli.main()
    assert result == 1


def test_main_run():
    """Test main with run command."""
    with mock.patch.object(sys, "argv", ["gmail2bear", "run"]):
        with mock.patch("gmail2bear.cli.parse_args") as mock_parse_args:
            mock_parse_args.return_value = mock.MagicMock(
                command="run", verbose=False, config="config.ini", credentials="credentials.json"
            )
            with mock.patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = True
                result = cli.main()
    assert result == 0
