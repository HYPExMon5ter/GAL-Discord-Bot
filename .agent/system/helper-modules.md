# Helper Modules

## utils/

### Overview
The `utils/` module provides utility functions for the GAL Discord Bot, with recent security enhancements for logging and token management.

### Modules

#### utils.py
- `resolve_member()` - Resolve Discord member from user ID
- `send_reminder_dms()` - Send reminder DMs to users
- `hyperlink_lolchess_profile()` - Create League of Legends profile hyperlinks
- `UtilsError` - Custom exception class for utility errors
- `MemberNotFoundError` - Exception for when members cannot be found

#### logging_utils.py (NEW)
- `mask_token()` - Mask sensitive tokens for logging purposes
- `mask_discord_tokens()` - Detect and mask Discord bot tokens in text
- `mask_api_keys()` - Mask various API keys that might appear in logs
- `sanitize_log_message()` - Comprehensive sanitization for log messages
- `SecureLogger` - Logger wrapper that automatically sanitizes messages

### Security Features
- **Token Masking**: All sensitive tokens are automatically masked in logs
- **API Key Protection**: Riot API keys and other credentials are protected
- **Log Sanitization**: Comprehensive sanitization prevents accidental exposure
- **Debug Information**: Masked token previews for debugging (last 4 characters only)

### Dependencies
- `re` - Regular expressions for pattern matching
- `typing` - Type hints
- No external dependencies required

### Usage Examples
```python
from utils.logging_utils import mask_token, sanitize_log_message

# Mask a token
masked = mask_token("abcd1234...efgh5678")  # -> "************5678"

# Sanitize log message
safe_message = sanitize_log_message("Login with token: abcdef...")
```

---

*Generated: 2025-10-18 02:10:26*
