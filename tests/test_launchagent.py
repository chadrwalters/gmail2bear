"""Tests for the launch agent manager."""

import os
import subprocess
from pathlib import Path
from unittest import mock

import pytest
from gmail2bear.launchagent.manager import LaunchAgentManager


@pytest.fixture
def mock_paths(tmp_path):
    """Create mock paths for testing."""
    config_path = tmp_path / "config.ini"
    credentials_path = tmp_path / "credentials.json"
    token_path = tmp_path / "token.pickle"
    state_path = tmp_path / "state.json"

    # Create empty files
    config_path.write_text("")
    credentials_path.write_text("")
    token_path.write_text("")
    state_path.write_text("")

    return {
        "config_path": str(config_path),
        "credentials_path": str(credentials_path),
        "token_path": str(token_path),
        "state_path": str(state_path),
    }


@pytest.fixture
def launch_agent_manager(mock_paths):
    """Create a launch agent manager with mock paths."""
    with mock.patch("platform.system", return_value="Darwin"):
        manager = LaunchAgentManager(
            config_path=mock_paths["config_path"],
            credentials_path=mock_paths["credentials_path"],
            token_path=mock_paths["token_path"],
            state_path=mock_paths["state_path"],
            poll_interval=300,
        )

        # Mock the template path to use a temporary file
        template_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gmail2bear</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_PATH}</string>
        <string>-m</string>
        <string>gmail2bear</string>
        <string>run</string>
        <string>--config</string>
        <string>${CONFIG_PATH}</string>
        <string>--credentials</string>
        <string>${CREDENTIALS_PATH}</string>
        <string>--token</string>
        <string>${TOKEN_PATH}</string>
        <string>--state</string>
        <string>${STATE_PATH}</string>
        <string>--poll-interval</string>
        <string>${POLL_INTERVAL}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/gmail2bear.out.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/gmail2bear.err.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>${ENV_PATH}</string>
        <key>PYTHONPATH</key>
        <string>${PYTHONPATH}</string>
    </dict>
</dict>
</plist>
"""
        template_path = Path(mock_paths["config_path"]).parent / "template.plist"
        template_path.write_text(template_content)
        manager.template_path = str(template_path)

        # Mock the plist path
        plist_dir = Path(mock_paths["config_path"]).parent / "LaunchAgents"
        plist_dir.mkdir(exist_ok=True)
        manager.plist_path = str(plist_dir / "com.gmail2bear.plist")

        return manager


def test_init(mock_paths):
    """Test initialization of LaunchAgentManager."""
    with mock.patch("platform.system", return_value="Darwin"):
        manager = LaunchAgentManager(
            config_path=mock_paths["config_path"],
            credentials_path=mock_paths["credentials_path"],
            token_path=mock_paths["token_path"],
            state_path=mock_paths["state_path"],
            poll_interval=300,
        )

        assert manager.config_path == os.path.abspath(
            os.path.expanduser(mock_paths["config_path"])
        )
        assert manager.credentials_path == os.path.abspath(
            os.path.expanduser(mock_paths["credentials_path"])
        )
        assert manager.token_path == os.path.abspath(
            os.path.expanduser(mock_paths["token_path"])
        )
        assert manager.state_path == os.path.abspath(
            os.path.expanduser(mock_paths["state_path"])
        )
        assert manager.poll_interval == 300


def test_is_macos_true():
    """Test is_macos when on macOS."""
    with mock.patch("platform.system", return_value="Darwin"):
        manager = LaunchAgentManager(
            config_path="config.ini",
            credentials_path="credentials.json",
            token_path="token.pickle",
            state_path="state.json",
        )

        assert manager.is_macos() is True


def test_is_macos_false():
    """Test is_macos when not on macOS."""
    with mock.patch("platform.system", return_value="Linux"):
        manager = LaunchAgentManager(
            config_path="config.ini",
            credentials_path="credentials.json",
            token_path="token.pickle",
            state_path="state.json",
        )

        assert manager.is_macos() is False


def test_is_installed_true(launch_agent_manager):
    """Test is_installed when plist exists."""
    # Create the plist file
    Path(launch_agent_manager.plist_path).write_text("test")

    assert launch_agent_manager.is_installed() is True


def test_is_installed_false(launch_agent_manager):
    """Test is_installed when plist doesn't exist."""
    # Ensure the plist file doesn't exist
    if os.path.exists(launch_agent_manager.plist_path):
        os.remove(launch_agent_manager.plist_path)

    assert launch_agent_manager.is_installed() is False


def test_is_running_not_installed(launch_agent_manager):
    """Test is_running when not installed."""
    # Ensure the plist file doesn't exist
    if os.path.exists(launch_agent_manager.plist_path):
        os.remove(launch_agent_manager.plist_path)

    assert launch_agent_manager.is_running() is False


def test_is_running_true(launch_agent_manager):
    """Test is_running when running."""
    # Create the plist file
    Path(launch_agent_manager.plist_path).write_text("test")

    # Mock subprocess.run to return success
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.MagicMock(returncode=0)

        assert launch_agent_manager.is_running() is True
        mock_run.assert_called_once()


def test_is_running_false(launch_agent_manager):
    """Test is_running when not running."""
    # Create the plist file
    Path(launch_agent_manager.plist_path).write_text("test")

    # Mock subprocess.run to return failure
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.MagicMock(returncode=1)

        assert launch_agent_manager.is_running() is False
        mock_run.assert_called_once()


def test_is_running_error(launch_agent_manager):
    """Test is_running when subprocess raises an error."""
    # Create the plist file
    Path(launch_agent_manager.plist_path).write_text("test")

    # Mock subprocess.run to raise an exception
    with mock.patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.SubprocessError("Test error")

        assert launch_agent_manager.is_running() is False
        mock_run.assert_called_once()


def test_install_not_macos(launch_agent_manager):
    """Test install when not on macOS."""
    with mock.patch.object(launch_agent_manager, "is_macos", return_value=False):
        assert launch_agent_manager.install() is False


def test_install_success(launch_agent_manager):
    """Test successful installation."""
    with mock.patch.object(
        launch_agent_manager, "is_macos", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "_load_agent", return_value=True
    ), mock.patch(
        "os.makedirs"
    ) as mock_makedirs, mock.patch(
        "os.chmod"
    ) as mock_chmod:
        assert launch_agent_manager.install() is True

        # Verify directories were created
        assert mock_makedirs.call_count == 2

        # Verify file was created
        assert os.path.exists(launch_agent_manager.plist_path)

        # Verify permissions were set
        mock_chmod.assert_called_once_with(launch_agent_manager.plist_path, 0o644)

        # Verify agent was loaded
        launch_agent_manager._load_agent.assert_called_once()


def test_install_error(launch_agent_manager):
    """Test installation with error."""
    with mock.patch.object(
        launch_agent_manager, "is_macos", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "_load_agent", side_effect=Exception("Test error")
    ):
        # The install method should catch the exception and return False
        assert launch_agent_manager.install() is False


def test_uninstall_not_macos(launch_agent_manager):
    """Test uninstall when not on macOS."""
    with mock.patch.object(launch_agent_manager, "is_macos", return_value=False):
        assert launch_agent_manager.uninstall() is False


def test_uninstall_not_installed(launch_agent_manager):
    """Test uninstall when not installed."""
    with mock.patch.object(
        launch_agent_manager, "is_macos", return_value=True
    ), mock.patch.object(launch_agent_manager, "is_installed", return_value=False):
        assert launch_agent_manager.uninstall() is True


def test_uninstall_success(launch_agent_manager):
    """Test successful uninstallation."""
    # Create the plist file
    Path(launch_agent_manager.plist_path).write_text("test")

    with mock.patch.object(
        launch_agent_manager, "is_macos", return_value=True
    ), mock.patch.object(launch_agent_manager, "_unload_agent", return_value=True):
        assert launch_agent_manager.uninstall() is True

        # Verify agent was unloaded
        launch_agent_manager._unload_agent.assert_called_once()

        # Verify file was removed
        assert not os.path.exists(launch_agent_manager.plist_path)


def test_uninstall_error(launch_agent_manager):
    """Test uninstallation with error."""
    # Create the plist file
    Path(launch_agent_manager.plist_path).write_text("test")

    with mock.patch.object(
        launch_agent_manager, "is_macos", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "_unload_agent", return_value=True
    ), mock.patch(
        "os.remove"
    ) as mock_remove:
        # Make remove raise an exception
        mock_remove.side_effect = OSError("Test error")

        assert launch_agent_manager.uninstall() is False


def test_start_not_macos(launch_agent_manager):
    """Test start when not on macOS."""
    with mock.patch.object(launch_agent_manager, "is_macos", return_value=False):
        assert launch_agent_manager.start() is False


def test_start_not_installed(launch_agent_manager):
    """Test start when not installed."""
    with mock.patch.object(
        launch_agent_manager, "is_macos", return_value=True
    ), mock.patch.object(launch_agent_manager, "is_installed", return_value=False):
        assert launch_agent_manager.start() is False


def test_start_already_running(launch_agent_manager):
    """Test start when already running."""
    with mock.patch.object(
        launch_agent_manager, "is_macos", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "is_installed", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "is_running", return_value=True
    ):
        assert launch_agent_manager.start() is True


def test_start_success(launch_agent_manager):
    """Test successful start."""
    with mock.patch.object(
        launch_agent_manager, "is_macos", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "is_installed", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "is_running", return_value=False
    ), mock.patch.object(
        launch_agent_manager, "_load_agent", return_value=True
    ):
        assert launch_agent_manager.start() is True

        # Verify agent was loaded
        launch_agent_manager._load_agent.assert_called_once()


def test_stop_not_macos(launch_agent_manager):
    """Test stop when not on macOS."""
    with mock.patch.object(launch_agent_manager, "is_macos", return_value=False):
        assert launch_agent_manager.stop() is False


def test_stop_not_installed(launch_agent_manager):
    """Test stop when not installed."""
    with mock.patch.object(
        launch_agent_manager, "is_macos", return_value=True
    ), mock.patch.object(launch_agent_manager, "is_installed", return_value=False):
        assert launch_agent_manager.stop() is False


def test_stop_not_running(launch_agent_manager):
    """Test stop when not running."""
    with mock.patch.object(
        launch_agent_manager, "is_macos", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "is_installed", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "is_running", return_value=False
    ):
        assert launch_agent_manager.stop() is True


def test_stop_success(launch_agent_manager):
    """Test successful stop."""
    with mock.patch.object(
        launch_agent_manager, "is_macos", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "is_installed", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "is_running", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "_unload_agent", return_value=True
    ):
        assert launch_agent_manager.stop() is True

        # Verify agent was unloaded
        launch_agent_manager._unload_agent.assert_called_once()


def test_restart_not_macos(launch_agent_manager):
    """Test restart when not on macOS."""
    with mock.patch.object(launch_agent_manager, "is_macos", return_value=False):
        assert launch_agent_manager.restart() is False


def test_restart_not_installed(launch_agent_manager):
    """Test restart when not installed."""
    with mock.patch.object(
        launch_agent_manager, "is_macos", return_value=True
    ), mock.patch.object(launch_agent_manager, "is_installed", return_value=False):
        assert launch_agent_manager.restart() is False


def test_restart_success(launch_agent_manager):
    """Test successful restart."""
    with mock.patch.object(
        launch_agent_manager, "is_macos", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "is_installed", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "stop", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "start", return_value=True
    ):
        assert launch_agent_manager.restart() is True

        # Verify stop and start were called
        launch_agent_manager.stop.assert_called_once()
        launch_agent_manager.start.assert_called_once()


def test_restart_stop_failure(launch_agent_manager):
    """Test restart when stop fails."""
    with mock.patch.object(
        launch_agent_manager, "is_macos", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "is_installed", return_value=True
    ), mock.patch.object(
        launch_agent_manager, "stop", return_value=False
    ):
        assert launch_agent_manager.restart() is False

        # Verify stop was called but not start
        launch_agent_manager.stop.assert_called_once()


def test_load_agent_success(launch_agent_manager):
    """Test successful agent loading."""
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.MagicMock(returncode=0)

        assert launch_agent_manager._load_agent() is True

        # Verify subprocess.run was called with correct arguments
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "launchctl"
        assert args[1] == "load"
        # The third argument should be the plist path, not "-w"
        assert args[2] == launch_agent_manager.plist_path


def test_load_agent_failure(launch_agent_manager):
    """Test agent loading failure."""
    with mock.patch("subprocess.run") as mock_run:
        # Set up the mock to raise CalledProcessError
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["launchctl", "load"], stderr="Test error"
        )

        assert launch_agent_manager._load_agent() is False


def test_load_agent_error(launch_agent_manager):
    """Test agent loading with subprocess error."""
    with mock.patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.SubprocessError("Test error")

        assert launch_agent_manager._load_agent() is False

        # Verify subprocess.run was called
        mock_run.assert_called_once()


def test_unload_agent_success(launch_agent_manager):
    """Test successful agent unloading."""
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.MagicMock(returncode=0)

        assert launch_agent_manager._unload_agent() is True

        # Verify subprocess.run was called with correct arguments
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "launchctl"
        assert args[1] == "unload"
        # The third argument should be the plist path, not "-w"
        assert args[2] == launch_agent_manager.plist_path


def test_unload_agent_failure(launch_agent_manager):
    """Test agent unloading failure."""
    with mock.patch("subprocess.run") as mock_run:
        # Set up the mock to raise CalledProcessError
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["launchctl", "unload"], stderr="Test error"
        )

        assert launch_agent_manager._unload_agent() is False


def test_unload_agent_error(launch_agent_manager):
    """Test agent unloading with subprocess error."""
    with mock.patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.SubprocessError("Test error")

        assert launch_agent_manager._unload_agent() is False

        # Verify subprocess.run was called
        mock_run.assert_called_once()


def test_get_status(launch_agent_manager):
    """Test getting service status."""
    with mock.patch.object(
        launch_agent_manager, "is_installed", return_value=True
    ), mock.patch.object(launch_agent_manager, "is_running", return_value=True):
        status = launch_agent_manager.get_status()

        assert status["installed"] is True
        assert status["running"] is True
        assert "plist_path" in status
        assert status["plist_path"] == launch_agent_manager.plist_path
