"""
Logging utilities for secure token handling and log sanitization.
"""

import logging
import re


def mask_token(token: str, mask_char: str = "*", show_last: int = 4) -> str:
    """
    Mask a sensitive token for logging purposes.
    
    Args:
        token: The token to mask
        mask_char: Character to use for masking
        show_last: Number of characters to show at the end
        
    Returns:
        Masked token string
    """
    if not token or len(token) <= show_last:
        return mask_char * len(token) if token else "None"
    
    masked_length = len(token) - show_last
    return mask_char * masked_length + token[-show_last:]


def mask_discord_tokens(text: str) -> str:
    """
    Mask Discord tokens that might appear in log messages.
    
    Args:
        text: Text that might contain tokens
        
    Returns:
        Text with tokens masked
    """
    if not text:
        return text
    
    # Discord bot tokens are typically 59 characters long and follow a pattern
    # Format: [A-Za-z0-9_-]{24}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27}
    token_pattern = r'([A-Za-z0-9_-]{24})\.([A-Za-z0-9_-]{6})\.([A-Za-z0-9_-]{27})'
    
    def mask_token_match(match):
        full_token = match.group(0)
        return mask_token(full_token)
    
    return re.sub(token_pattern, mask_token_match, text)


def mask_api_keys(text: str) -> str:
    """
    Mask various API keys that might appear in log messages.
    
    Args:
        text: Text that might contain API keys
        
    Returns:
        Text with API keys masked
    """
    if not text:
        return text
    
    # Riot API keys (RGAPI- followed by alphanumeric)
    riot_pattern = r'(RGAPI-[a-f0-9]{32})'
    text = re.sub(riot_pattern, lambda m: mask_token(m.group(1)), text)
    
    # Generic long alphanumeric strings that might be keys
    generic_pattern = r'([a-zA-Z0-9_-]{32,})'
    text = re.sub(generic_pattern, lambda m: mask_token(m.group(1)), text)
    
    return mask_discord_tokens(text)


def sanitize_log_message(message: str) -> str:
    """
    Sanitize a log message by masking sensitive information.
    
    Args:
        message: Original log message
        
    Returns:
        Sanitized log message
    """
    if not message:
        return message
    
    # Mask various types of sensitive data
    sanitized = mask_api_keys(message)
    
    # Mask environment variable values if they appear in logs
    env_var_pattern = r'(DISCORD_TOKEN|RIOT_API_KEY|DATABASE_URL)=([^\s]+)'
    sanitized = re.sub(env_var_pattern, r'\1=' + mask_token(r'\2'), sanitized)
    
    return sanitized


class SecureLogger:
    """A logger wrapper that automatically sanitizes messages."""
    
    def __init__(self, logger_name: str = __name__):
        import logging
        self.logger = logging.getLogger(logger_name)
    
    def _sanitize_and_log(self, level: int, message: str, *args, **kwargs):
        """Sanitize message and log it."""
        sanitized_message = sanitize_log_message(str(message))
        self.logger.log(level, sanitized_message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message with sanitization."""
        self._sanitize_and_log(logging.DEBUG, message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message with sanitization."""
        self._sanitize_and_log(logging.INFO, message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message with sanitization."""
        self._sanitize_and_log(logging.WARNING, message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message with sanitization."""
        self._sanitize_and_log(logging.ERROR, message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message with sanitization."""
        self._sanitize_and_log(logging.CRITICAL, message, *args, **kwargs)
