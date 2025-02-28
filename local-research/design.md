# Gmail to Bear Integration - Technical Design Document

## System Architecture

### Overview
The Gmail to Bear integration is a Python-based application that monitors Gmail for emails from specific senders and converts them to Bear notes. The application will be developed in phases, starting with a manually executed script (MVP) and evolving into a background service.

### Components
1. **Gmail API Client**: Handles authentication and communication with Gmail API
2. **Email Processor**: Extracts and formats email content
3. **Bear Integration**: Creates notes in Bear using x-callback-url scheme
4. **State Manager**: Tracks processed emails to prevent duplicates
5. **Configuration Manager**: Handles user settings
6. **Logging System**: Records application events and errors
7. **Service Manager** (Phase 3): Runs the application as a background service

### Phased Implementation

#### Phase 1: MVP
- Manually executed script
- Single sender support
- Plain text email processing
- Basic Bear note creation
- Simple state management with text file
- Console logging

#### Phase 2: Enhanced Features
- Multiple sender support
- HTML to Markdown conversion
- Customizable templates
- Improved error handling
- File-based logging

#### Phase 3: Background Service
- macOS Launch Agent integration
- Automatic startup and recovery
- System notifications
- Advanced configuration

### Data Flow
1. The application authenticates with Gmail API using OAuth2
2. It queries Gmail for new emails from specified senders
3. For each new email, it extracts relevant content (subject, body, date, sender)
4. It formats the content according to the configured template
5. It creates a new Bear note using the formatted content
6. It marks the email as read and (in later phases) archives it in Gmail
7. It records the processed email ID to prevent future duplicate processing

## Technical Specifications

### Gmail API Integration
- **Authentication**: OAuth2 using Google API client libraries
- **Required Scopes**: `https://www.googleapis.com/auth/gmail.modify` (allows reading and modifying emails)
- **API Endpoints Used**:
  - `users.messages.list`: To query for emails from specific senders
  - `users.messages.get`: To retrieve full email content
  - `users.messages.modify`: To mark emails as read and archive them
- **Polling Mechanism**:
  - MVP: Manual execution
  - Later phases: Time-based polling with configurable interval

### Email Processing
- **Email Filtering**: Query-based filtering using Gmail search syntax (e.g., `from:example@gmail.com`)
- **Content Extraction**:
  - Headers parsing for subject, date, and sender
  - MIME parsing for email body (prioritizing text/plain)
  - Base64 decoding of email body content
- **HTML Handling** (Phase 2): Conversion of HTML content to Markdown using a library like `html2text`

### Bear Integration
- **Note Creation**: Using Bear's x-callback-url scheme
- **URL Format**: `bear://x-callback-url/create?title={title}&text={text}&open_note=no`
- **Template System**:
  - MVP: Basic template with email subject and body
  - Phase 2: Configurable templates with placeholders for email fields
- **Background Operation**: Using `open_note=no` parameter to prevent UI interruption

### State Management
- **Processed Email Tracking**:
  - MVP: Simple text file with one ID per line
  - Later phases: Consider SQLite for more robust storage
- **Duplicate Prevention**: Check against stored IDs before processing
- **Error Recovery**: Ability to resume processing after failures

### Configuration
- **Format**: INI file format for easy editing
- **Settings**:
  - `sender_email`: Email address(es) to monitor
  - `poll_interval`: Time between Gmail checks (in seconds)
  - `note_title`: Template for Bear note titles
  - `note_body`: Template for Bear note content
  - `log_level`: Logging verbosity level

### Logging
- **MVP**: Console logging with basic information
- **Phase 2 and 3**:
  - **Library**: Python's built-in `logging` module
  - **Log File**: Persistent log file with timestamp, level, and message
  - **Levels**: Configurable (DEBUG, INFO, WARNING, ERROR)
  - **Content**: Operation status, processed emails, errors, and warnings

### OAuth Token Management
- **Token Storage**:
  - MVP: Encrypted file storage with proper key derivation
  - Phase 3: Consider macOS Keychain integration
- **Security Measures**:
  - File permission restrictions (owner-only access: 0600)
  - Encryption of token files using Fernet symmetric encryption
  - Proper key derivation with salting
  - Separation of sensitive credentials from general configuration
- **Automatic Refresh**: Leveraging Google API client's built-in token refresh capabilities
- **Refresh Failure Detection**: Explicit handling of refresh failures with appropriate error logging
- **Reauthorization Flow**: User-friendly process for manual reauthorization when needed

### Service Management (Phase 3)
- **Launch Agent**:
  - macOS launchd plist file for automatic startup
  - Configured to run at user login and keep running in the background
  - Redirects stdout/stderr to log files
  - Sets low I/O priority to minimize system impact
- **Service Mode**:
  - Dedicated application mode for continuous operation
  - Main polling loop with configurable interval
  - Graceful error handling with automatic recovery
- **User Control**:
  - CLI commands for service management (start, stop, restart, status)
  - Standard launchctl commands for manual control
- **Error Handling**: Automatic restart on crashes with exponential backoff for recurring issues

## Implementation Details

### Project Structure
```
gmail2bear/
├── src/
│   ├── gmail2bear/
│   │   ├── __init__.py
│   │   ├── cli.py            # Command-line interface
│   │   ├── config.py         # Configuration handling
│   │   ├── gmail_client.py   # Gmail API integration
│   │   ├── bear_client.py    # Bear app integration
│   │   ├── email_processor.py # Email content extraction
│   │   ├── state_manager.py  # Processed email tracking
│   │   └── service.py        # Main service logic (Phase 3)
│   └── __init__.py
├── tests/                    # Unit and integration tests
├── config/
│   ├── config.ini.example    # Example configuration
│   └── com.gmail2bear.plist  # Launch Agent template (Phase 3)
├── credentials.json          # Google API credentials (to be added by user)
├── .gitignore                # Git ignore file
├── pyproject.toml            # Project metadata and dependencies
├── README.md                 # Project documentation
└── LICENSE                   # License information
```

### Key Classes and Functions

#### `GmailClient` Class
- `__init__(credentials_path)`: Initialize with Google API credentials
- `authenticate()`: Perform OAuth authentication
- `get_messages_from_sender(sender_email)`: Query for emails from a specific sender
- `get_message_content(message_id)`: Retrieve full email content
- `mark_as_read(message_id)`: Mark email as read
- `archive_message(message_id)` (Phase 2): Archive the email

#### `BearClient` Class
- `create_note(title, body, tags=None)`: Create a new note in Bear
- `format_note(template, email_data)` (Phase 2): Format email data according to template

#### `EmailProcessor` Class
- `extract_email_data(message)`: Extract relevant data from Gmail message
- `decode_body(body_data)`: Decode base64-encoded email body
- `convert_html_to_text(html_content)` (Phase 2): Convert HTML to Markdown

#### `StateManager` Class
- `__init__(state_file_path)`: Initialize with path to state file
- `is_processed(message_id)`: Check if an email has been processed
- `mark_as_processed(message_id)`: Record an email as processed

#### `ConfigManager` Class
- `__init__(config_file_path)`: Initialize with path to config file
- `get_config()`: Read and parse configuration
- `get_sender_email()`: Get configured sender email
- `get_poll_interval()`: Get configured polling interval
- `get_note_template()`: Get configured Bear note template

#### `TokenManager` Class
- `__init__(token_dir)`: Initialize with directory for token storage
- `save_token(token_data)`: Securely save OAuth token
- `load_token()`: Load and decrypt OAuth token
- `is_token_valid()`: Check if token is valid and not expired

#### `Service` Class (Phase 3)
- `__init__(config_path, credentials_path)`: Initialize service
- `run()`: Main service loop
- `process_email(email_data)`: Process a single email
- `handle_error(error)`: Error handling logic

### Dependencies
- `google-api-python-client`: For Gmail API access
- `google-auth-oauthlib`: For OAuth authentication
- `google-auth-httplib2`: For HTTP requests to Google API
- `cryptography`: For secure token encryption
- `configparser`: For configuration file parsing (standard library)
- `logging`: For logging (standard library)
- `urllib.parse`: For URL encoding (standard library)
- `subprocess`: For launching Bear URLs (standard library)
- `time`: For sleep functionality (standard library)
- `base64`: For decoding email content (standard library)
- `html2text` (Phase 2): For converting HTML to Markdown

## Security Considerations

### Credential Handling
- Encrypted storage of OAuth tokens with proper key derivation
- Token refresh handled automatically by Google API client
- No storage of Gmail passwords
- Proper file permissions (0600) for sensitive files

### Data Privacy
- Email content only stored temporarily during processing
- No persistent storage of email content beyond Bear notes
- Logs contain message IDs but not email content
- Input validation for all external data

## Error Handling and Recovery

### Network Errors
- Exponential backoff for transient API errors
- Logging of connection failures
- Retry mechanism for failed API calls

### API Rate Limits
- Respect for Gmail API quotas
- Backoff strategy for rate limit errors

### Application Errors
- Exception handling for all external calls
- Graceful degradation on non-critical failures
- Clear error messages for troubleshooting

## Testing Strategy

### Unit Tests
- Test each component in isolation with mocked dependencies
- Focus on email parsing, template formatting, and state management
- Use Python's unittest or pytest framework

### Integration Tests
- Test Gmail API client with test account
- Test Bear integration with actual Bear application
- Test end-to-end flow with controlled test emails

### Manual Testing
- Verify correct operation with various email formats
- Confirm proper handling of edge cases
- Validate functionality across different phases

## Deployment and Operations

### Installation
- Python package installable via pip
- Configuration file setup with user-specific values
- OAuth authorization flow for first-time setup

### Launch Agent Setup (Phase 3)
- Template plist file for launchd configuration
- Instructions for installing and loading the agent

### Monitoring and Maintenance
- Log file for troubleshooting
- Periodic token refresh for OAuth credentials
- Documentation for common issues and solutions
