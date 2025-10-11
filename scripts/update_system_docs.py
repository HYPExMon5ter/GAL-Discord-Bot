#!/usr/bin/env python3
"""
System documentation updater script.
Updates .agent/system documentation based on recent code changes.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Set
from datetime import datetime


def get_python_files_with_functions() -> Dict[str, List[str]]:
    """Get all Python files and their functions/classes."""
    files_info = {}
    project_root = Path(__file__).parent.parent
    
    for py_file in project_root.rglob("*.py"):
        if any(skip in str(py_file) for skip in ["__pycache__", ".venv", ".git"]):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract classes and functions
            functions = []
            lines = content.split('\n')
            
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('def ') or stripped.startswith('async def '):
                    func_name = stripped.split('(')[0].replace('def ', '').replace('async def ', '')
                    functions.append(f"function: {func_name}")
                elif stripped.startswith('class '):
                    class_name = stripped.split('(')[0].replace('class ', '').replace(':', '')
                    functions.append(f"class: {class_name}")
            
            if functions:
                relative_path = str(py_file.relative_to(project_root))
                files_info[relative_path] = functions
                
        except Exception as e:
            print(f"Error processing {py_file}: {e}")
    
    return files_info


def get_module_structure() -> Dict[str, List[str]]:
    """Get the current module structure."""
    structure = {}
    project_root = Path(__file__).parent.parent
    
    for module_dir in ["core", "helpers", "integrations", "utils"]:
        module_path = project_root / module_dir
        if module_path.exists():
            files = []
            for py_file in module_path.glob("*.py"):
                if py_file.name != "__init__.py":
                    files.append(py_file.stem)
            structure[module_dir] = sorted(files)
    
    return structure


def update_utils_docs():
    """Update utils module documentation."""
    utils_path = Path(__file__).parent.parent / ".agent" / "system" / "helper-modules.md"
    
    content = """# Helper Modules

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

*Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
    
    with open(utils_path, 'w', encoding='utf-8') as f:
        f.write(content)


def update_architecture_docs():
    """Update main architecture documentation."""
    arch_path = Path(__file__).parent.parent / ".agent" / "system" / "architecture.md"
    
    if not arch_path.exists():
        return
    
    # Read existing content
    with open(arch_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add security section if not present
    if "## Security & Logging" not in content:
        security_section = """

## Security & Logging

### Token Management
- **Secure Logging**: All tokens and API keys are automatically masked in logs
- **Environment Variables**: Sensitive variables are properly handled and not exposed
- **Error Handling**: Login failures provide useful information without exposing credentials
- **Debug Mode**: Token previews available in debug logs (last 4 characters only)

### Log Sanitization
- **Automatic Detection**: Discord tokens, API keys, and sensitive data patterns are detected
- **Pattern Matching**: Regular expression-based detection of token formats
- **Safe Logging**: All log messages are sanitized before output
- **Debug Support**: Masked information available for troubleshooting

### Implementation
```python
from utils.logging_utils import mask_token, sanitize_log_message

# Secure error handling
except discord.LoginFailure:
    logging.error("Failed to login - check your Discord token configuration")
    if DISCORD_TOKEN:
        logging.debug(f"Token preview: {mask_token(DISCORD_TOKEN)}")
```
"""
        content += security_section
    
    with open(arch_path, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    """Main update function."""
    print("Updating system documentation...")
    
    # Update various documentation files
    update_utils_docs()
    update_architecture_docs()
    
    print("Documentation updated successfully!")
    
    # Summary of changes
    print("\nUpdated Files:")
    print("  - .agent/system/helper-modules.md (added logging_utils documentation)")
    print("  - .agent/system/architecture.md (added security section)")
    
    print("\nSecurity Enhancements Documented:")
    print("  - Token masking utilities")
    print("  - Log sanitization functions")
    print("  - Secure error handling")
    print("  - API key protection")


if __name__ == "__main__":
    main()
