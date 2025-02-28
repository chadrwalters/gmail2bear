# Gmail to Bear

A Python application that automatically converts emails from Gmail to notes in Bear.

## Overview

Gmail to Bear is a tool that monitors your Gmail inbox for emails from specific senders and automatically converts them into Bear notes using customizable templates. It helps you save time by eliminating the need to manually copy and paste email content into your note-taking app.

## Features

### Phase 1: MVP (Current)
- Monitor Gmail for emails from a specific sender
- Extract email content (subject, body)
- Create Bear notes with basic formatting
- Mark processed emails as read
- Track processed emails to prevent duplicates
- Run as a manually executed script

### Phase 2: Coming Soon
- Support for multiple sender emails
- HTML email processing with Markdown conversion
- Customizable note templates
- Email archiving in Gmail
- Improved error handling and recovery
- File-based logging

### Phase 3: Future
- Run as a background service using macOS Launch Agent
- Automatic startup and recovery
- System notifications for critical events
- Advanced configuration options

## Requirements

- Python 3.8+
- macOS (for Bear integration)
- Gmail account
- Bear note-taking app
- Google API credentials
- [UV](https://github.com/astral-sh/uv) - Fast Python package installer and resolver

## Installation

Coming soon! The project is currently under development.

## Usage

Coming soon! The project is currently under development.

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
