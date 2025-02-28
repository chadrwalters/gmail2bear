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

## Installation

Coming soon! The project is currently under development.

## Usage

Coming soon! The project is currently under development.

## Development

### Setup Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/gmail2bear.git
   cd gmail2bear
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Set up Google API credentials:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Gmail API
   - Create OAuth credentials
   - Download the credentials.json file and place it in the project directory

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
