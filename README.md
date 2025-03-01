# Gmail to Bear

A Python application that automatically converts emails from Gmail to notes in Bear.

## Overview

Gmail to Bear is a tool that monitors your Gmail inbox for emails from specific senders and automatically converts them into Bear notes using customizable templates. It helps you save time by eliminating the need to manually copy and paste email content into your note-taking app.

## Important Note on Configuration

> **Current Development Status**: Currently, the configuration files are stored in the `.gmail2bear` directory within the project repository. This is a temporary location for development purposes.
>
> When running the application, you need to specify the configuration paths explicitly:
> ```bash
> uv run gmail2bear run --config ./.gmail2bear/config.ini --credentials ./.gmail2bear/credentials.json --token ./.gmail2bear/token.pickle --state ./.gmail2bear/state.txt
> ```
>
> In a future update, we will move the configuration to the standard location at `~/.gmail2bear/` in the user's home directory, which will eliminate the need for these explicit path specifications.

## Features

### Phase 1: MVP ✅
- Monitor Gmail for emails from a specific sender
- Extract email content (subject, body)
- Create Bear notes with basic formatting
- Mark processed emails as read
- Track processed emails to prevent duplicates
- Run as a manually executed script

### Phase 2: Enhanced Features ✅
- Support for multiple sender emails
- HTML email processing with Markdown conversion
- Customizable note templates
- Email archiving in Gmail
- Improved error handling and recovery
- File-based logging with rotation

### Phase 3: Background Service ✅
- Run as a background service using macOS Launch Agent
- Automatic startup at login
- System notifications for new emails and errors
- Configuration reloading without restart
- Service management commands (install, start, stop, status)
- Graceful shutdown and error recovery
- Network monitoring with automatic reconnection
- System event handling (sleep/wake, power events)
- Secure token storage using macOS Keychain

### Phase 4: Service Stability Improvements ✅
- Robust error handling for network issues with detailed logging
- Automatic retry mechanisms for transient failures with exponential backoff
- Multiple DNS server fallback for reliable network detection
- Error backoff periods to prevent excessive resource usage during persistent failures
- Comprehensive error tracking and reporting
- Improved authentication failure handling

## Requirements

- Python 3.8+
- macOS (for Bear integration and Launch Agent)
- Gmail account
- Bear note-taking app
- Google API credentials
- [UV](https://github.com/astral-sh/uv) - Fast Python package installer and resolver (recommended)

## Installation

### One-Liner Installation (Recommended)

The easiest way to install Gmail to Bear is with our one-liner installation script:

```bash
curl -sSL https://raw.githubusercontent.com/chadrwalters/gmail2bear/main/scripts/install_oneliner.sh | bash
```

This script will:
1. Check if UV is installed (and use it if available)
2. Clone the repository
3. Install the package
4. Create a default configuration
5. Install the service

### Quick Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/chadrwalters/gmail2bear.git
   cd gmail2bear
   ```

2. Run the installation script:
   ```bash
   python scripts/install_service.py
   ```

3. Follow the on-screen instructions to complete the setup.

### Manual Installation with UV (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/chadrwalters/gmail2bear.git
   cd gmail2bear
   ```

2. Install the package using UV:
   ```bash
   uv pip install -e .
   ```

3. Create a default configuration:
   ```bash
   uv run gmail2bear init-config
   ```

4. Edit the configuration file at `~/.gmail2bear/config.ini` to set your preferences.

5. Place your Google API credentials at `~/.gmail2bear/credentials.json`.

6. Install the Launch Agent (optional, for background service):
   ```bash
   uv run gmail2bear service install
   ```

### Manual Installation with pip

1. Clone the repository:
   ```bash
   git clone https://github.com/chadrwalters/gmail2bear.git
   cd gmail2bear
   ```

2. Install the package:
   ```bash
   pip install -e .
   ```

3. Create a default configuration:
   ```bash
   gmail2bear init-config
   ```

4. Edit the configuration file at `~/.gmail2bear/config.ini` to set your preferences.

5. Place your Google API credentials at `~/.gmail2bear/credentials.json`.

6. Install the Launch Agent (optional, for background service):
   ```bash
   gmail2bear service install
   ```

## Usage

### Running Once

To process emails once and exit:

```bash
# With UV (recommended)
uv run gmail2bear run --once

# Without UV
gmail2bear run --once
```

### Running as a Service

To manage the background service:

```bash
# With UV (recommended)
# Install the service
uv run gmail2bear service install

# Start the service
uv run gmail2bear service start

# Check service status
uv run gmail2bear service status

# Stop the service
uv run gmail2bear service stop

# Restart the service
uv run gmail2bear service restart

# Uninstall the service
uv run gmail2bear service uninstall

# Without UV
# Install the service
gmail2bear service install

# Start the service
gmail2bear service start

# Check service status
gmail2bear service status

# Stop the service
gmail2bear service stop

# Restart the service
gmail2bear service restart

# Uninstall the service
gmail2bear service uninstall
```

### System Commands

To send signals to the running service:

```bash
# With UV (recommended)
# Pause email processing
uv run gmail2bear system signal --signal pause

# Resume email processing
uv run gmail2bear system signal --signal resume

# Reload configuration
uv run gmail2bear system signal --signal reload

# Without UV
# Pause email processing
gmail2bear system signal --signal pause

# Resume email processing
gmail2bear system signal --signal resume

# Reload configuration
gmail2bear system signal --signal reload
```

### Security Commands

To manage token security:

```bash
# With UV (recommended)
# Migrate tokens from file to Keychain
uv run gmail2bear security migrate-to-keychain

# Migrate and delete the token file after migration
uv run gmail2bear security migrate-to-keychain --delete-file

# Specify a custom service name for Keychain
uv run gmail2bear security migrate-to-keychain --service-name "MyGmail2Bear"

# Without UV
# Migrate tokens from file to Keychain
gmail2bear security migrate-to-keychain

# Migrate and delete the token file after migration
gmail2bear security migrate-to-keychain --delete-file

# Specify a custom service name for Keychain
gmail2bear security migrate-to-keychain --service-name "MyGmail2Bear"
```

### Network Commands

To check network connectivity:

```bash
# With UV (recommended)
# Check if network is available
uv run gmail2bear network check

# Without UV
# Check if network is available
gmail2bear network check
```

### Running the Service Directly

To run the service directly in the terminal (useful for debugging):

```bash
# With UV (recommended)
uv run gmail2bear run

# Without UV
gmail2bear run
```

## Troubleshooting

### UV-Related Issues

If you encounter issues with UV:

1. Make sure UV is installed correctly:
   ```bash
   uv --version
   ```

2. If UV is not found, install it:
   ```bash
   pip install uv
   ```

3. If you see errors about modules not being found when using UV, try reinstalling the package:
   ```bash
   uv pip install -e .
   ```

4. If you still have issues, you can fall back to using pip:
   ```bash
   pip install -e .
   gmail2bear run
   ```

### Common Issues

1. **Configuration not found**: Make sure your configuration files are in the correct location.
   ```bash
   ls -la ~/.gmail2bear/
   ```

2. **Service not starting**: Check the service logs for errors.
   ```bash
   cat ~/.gmail2bear/gmail2bear.err
   cat ~/.gmail2bear/gmail2bear.out
   ```

3. **Authentication errors**: Make sure your Google API credentials are valid and properly set up.
   ```bash
   uv run gmail2bear run --once --debug
   ```

## Configuration

The configuration file is located at `~/.gmail2bear/config.ini` by default. You can specify a different location using the `--config` option.

### Gmail Settings

```ini
[gmail]
# Email address(es) to monitor (comma-separated for multiple)
sender_email = example@gmail.com, another@gmail.com

# How often to check for new emails (in seconds)
poll_interval = 300

# Whether to archive emails after processing
archive_emails = true
```

### Bear Settings

```ini
[bear]
# Template for Bear note title
# Available placeholders: {subject}, {sender}, {id}
# Date formatting: {date} or with format specifiers {date:%Y-%m-%d}
note_title_template = Email: {subject}

# Template for Bear note body
# Available placeholders: {subject}, {body}, {sender}, {id}
# Date formatting: {date} or with format specifiers {date:%Y-%m-%d %H:%M}
note_body_template = # {subject}

From: {sender}
Date: {date}

{body}

---
Source: Gmail ID {id}

# Tags to add to Bear notes (comma-separated)
tags = email,gmail
```

#### Template Formatting Examples

You can customize how your emails appear in Bear using the template placeholders:

**Simple Title Examples:**
```
Email: {subject}
Message from {sender}
{date} - {subject}
```

**Date Formatting Examples:**
```
{date:%Y-%m-%d} - {subject}
{date:%B %d, %Y} - Email from {sender}
{date:%Y%m%d%H%M} - {subject}
```

**Body Template Examples:**
```
# {subject}

Received on {date:%A, %B %d, %Y at %I:%M %p}
From: {sender}

{body}

---
Source: Gmail ID {id}
```

The date formatting uses Python's [datetime format codes](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes).

### Service Settings

```ini
[service]
# Whether to show system notifications
show_notifications = true

# Whether to start the service at login
start_at_login = true

# Notification sound (default, none, or system sound name)
notification_sound = default

# Network check interval in seconds
network_check_interval = 60

# Configuration check interval in seconds
config_check_interval = 300

# Whether to handle system events (sleep/wake, power events)
handle_system_events = true
```

### Security Settings

```ini
[security]
# Whether to use macOS Keychain for token storage
use_keychain = true

# Service name for Keychain entries
keychain_service_name = Gmail2Bear
```

### Logging Settings

```ini
[logging]
# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
level = INFO

# Log file path
file = ~/.gmail2bear/gmail2bear.log

# Maximum log file size in KB before rotation
max_log_size = 1024

# Number of backup log files to keep
backup_count = 3
```

## Service Stability

Gmail2Bear includes several features to ensure reliable operation even in challenging network conditions:

### Retry Mechanism

The application uses an intelligent retry mechanism with exponential backoff for transient failures:

- Automatically retries operations that fail due to temporary issues
- Uses exponential backoff with jitter to prevent thundering herd problems
- Distinguishes between transient and permanent errors
- Provides detailed logging of retry attempts

### Network Resilience

Multiple features ensure the application can handle network disruptions:

- Checks multiple DNS servers to accurately detect network availability
- Automatically pauses during network outages and resumes when connectivity is restored
- Re-authenticates automatically when network is restored
- Tracks network failure history for better diagnostics

### Error Management

Sophisticated error handling prevents resource exhaustion during persistent failures:

- Implements error backoff periods after consecutive failures
- Provides detailed error tracking and reporting
- Gracefully handles authentication failures with helpful notifications
- Prevents tight error loops that could consume system resources

## Development

### Setup Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/chadrwalters/gmail2bear.git
   cd gmail2bear
   ```

2. Install UV if you don't have it already:
   ```bash
   pip install uv
   ```

3. Create a virtual environment with UV:
   ```bash
   uv venv create .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. Install development dependencies with UV:
   ```bash
   uv pip install -e ".[dev]"
   ```

5. Set up pre-commit hooks:
   ```bash
   uv run pre-commit install
   ```

6. Set up Google API credentials:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Gmail API
   - Create OAuth credentials
   - Download the credentials.json file and place it in the project directory

### Code Quality Tools

This project uses several tools to maintain code quality:

1. **Ruff** - Fast Python linter and formatter
   ```bash
   uv run ruff check .
   uv run ruff format .
   ```

2. **Black** - Code formatter
   ```bash
   uv run black src/ tests/
   ```

3. **isort** - Import sorter
   ```bash
   uv run isort src/ tests/
   ```

4. **mypy** - Type checking
   ```bash
   uv run mypy src/
   ```

5. **pre-commit** - Git hook scripts
   ```bash
   uv run pre-commit run --all-files
   ```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=gmail2bear
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

Before submitting your PR, please ensure:
1. All tests pass: `uv run pytest`
2. Code passes all linting checks: `uv run pre-commit run --all-files`
3. You've added tests for new functionality

## License

This project is licensed under the MIT License - see the LICENSE file for details.
