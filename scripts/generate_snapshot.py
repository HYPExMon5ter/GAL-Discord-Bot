#!/usr/bin/env python3
"""
Context snapshot generator for AI sessions.
Creates a comprehensive snapshot of the current system state.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


def get_project_structure() -> Dict[str, Any]:
    """Get the current project structure."""
    project_root = Path(__file__).parent.parent
    structure = {
        "modules": {},
        "config_files": [],
        "key_files": []
    }
    
    # Get module structures
    for module_dir in ["core", "helpers", "integrations", "utils"]:
        module_path = project_root / module_dir
        if module_path.exists():
            files = []
            for py_file in module_path.glob("*.py"):
                if py_file.name != "__init__.py":
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            functions = []
                            classes = []
                            
                            lines = content.split('\n')
                            for line in lines:
                                stripped = line.strip()
                                if stripped.startswith('def ') or stripped.startswith('async def '):
                                    func_name = stripped.split('(')[0].replace('def ', '').replace('async def ', '')
                                    functions.append(func_name)
                                elif stripped.startswith('class '):
                                    class_name = stripped.split('(')[0].replace('class ', '').replace(':', '')
                                    classes.append(class_name)
                            
                            files.append({
                                "name": py_file.stem,
                                "functions": functions,
                                "classes": classes
                            })
                    except Exception:
                        files.append({"name": py_file.stem, "functions": [], "classes": []})
            
            structure["modules"][module_dir] = files
    
    # Get config files
    for config_file in ["config.py", "config.yaml", ".env", "requirements.txt"]:
        if (project_root / config_file).exists():
            structure["config_files"].append(config_file)
    
    # Get key files
    for key_file in ["bot.py"]:
        if (project_root / key_file).exists():
            structure["key_files"].append(key_file)
    
    return structure


def get_git_info() -> Dict[str, str]:
    """Get git repository information."""
    try:
        import subprocess
        result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                              capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        branch = result.stdout.strip() if result.returncode == 0 else "unknown"
        
        result = subprocess.run(['git', 'log', '--oneline', '-5'], 
                              capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        recent_commits = result.stdout.strip() if result.returncode == 0 else "No git history"
        
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        git_status = result.stdout.strip() if result.returncode == 0 else "Clean"
        
        return {
            "branch": branch,
            "recent_commits": recent_commits,
            "status": git_status or "Clean"
        }
    except Exception:
        return {
            "branch": "unknown",
            "recent_commits": "No git info available",
            "status": "Unknown"
        }


def get_agent_info() -> Dict[str, Any]:
    """Get Factory AI agent information."""
    project_root = Path(__file__).parent.parent
    agents_dir = project_root / ".factory" / "droids"
    
    agents = {}
    if agents_dir.exists():
        for agent_file in agents_dir.glob("*.md"):
            try:
                with open(agent_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Extract title and description
                    title = "Unknown"
                    description = "No description"
                    
                    for line in lines:
                        if line.startswith('# '):
                            title = line[2:].strip()
                        elif line.startswith('description:'):
                            description = line.split(':', 1)[1].strip().strip('"')
                    
                    agents[agent_file.stem] = {
                        "title": title,
                        "description": description
                    }
            except Exception:
                continue
    
    return agents


def generate_snapshot() -> str:
    """Generate the complete context snapshot."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Gather all information
    project_structure = get_project_structure()
    git_info = get_git_info()
    agent_info = get_agent_info()
    
    # Build the snapshot content
    snapshot_content = f"""# GAL Discord Bot - Context Snapshot

**Generated:** {timestamp}  
**Branch:** {git_info['branch']}  
**Status:** {git_info['status']}

## Quick Overview

This is the Guardian Angel League Discord Bot with Live Graphics Dashboard integration.

### Core Components
- **Discord Bot:** Main bot functionality with commands, events, and views
- **Google Sheets Integration:** Waitlist management and data synchronization  
- **Riot API Integration:** League of Legends profile verification
- **Live Graphics Dashboard:** Real-time graphics overlay system
- **Security:** Enhanced logging with token masking and API key protection

### Recent Security Enhancements
- Token masking utilities in `utils/logging_utils.py`
- Log sanitization to prevent credential exposure
- Secure error handling with masked debug information

## Project Structure

"""
    
    # Add module information
    for module_name, files in project_structure["modules"].items():
        snapshot_content += f"### {module_name.title()}/\n\n"
        for file_info in files:
            snapshot_content += f"**{file_info['name']}.py**\n"
            if file_info['functions']:
                snapshot_content += f"Functions: {', '.join(file_info['functions'])}\n"
            if file_info['classes']:
                snapshot_content += f"Classes: {', '.join(file_info['classes'])}\n"
            snapshot_content += "\n"
    
    # Add config information
    snapshot_content += "### Configuration\n\n"
    for config_file in project_structure["config_files"]:
        snapshot_content += f"- `{config_file}`\n"
    snapshot_content += "\n"
    
    # Add recent commits
    snapshot_content += f"## Recent Commits\n\n```\n{git_info['recent_commits']}\n```\n\n"
    
    # Add Factory AI agents
    if agent_info:
        snapshot_content += "## Factory AI Agents\n\n"
        for agent_id, agent_data in agent_info.items():
            snapshot_content += f"**{agent_data['title']}** (`{agent_id}`)\n"
            snapshot_content += f"- {agent_data['description']}\n\n"
    
    # Add key files overview
    snapshot_content += "## Key Files Overview\n\n"
    snapshot_content += "- **bot.py**: Main bot entry point and Discord client setup\n"
    snapshot_content += "- **config.py**: Configuration management and environment handling\n"
    snapshot_content += "- **core/**: Core bot functionality (commands, events, views, etc.)\n"
    snapshot_content += "- **integrations/**: External service integrations (Sheets, Riot API)\n"
    snapshot_content += "- **helpers/**: Utility functions and helper modules\n"
    snapshot_content += "- **utils/**: General utilities including security functions\n\n"
    
    snapshot_content += "---\n*End of context snapshot*\n"
    
    return snapshot_content


def main():
    """Main function to generate and save the snapshot."""
    print("Generating context snapshot...")
    
    # Generate snapshot content
    snapshot = generate_snapshot()
    
    # Save to file
    snapshot_path = Path(__file__).parent.parent / ".agent" / "snapshots" / "context_snapshot.md"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(snapshot_path, 'w', encoding='utf-8') as f:
        f.write(snapshot)
    
    print(f"Context snapshot saved to {snapshot_path}")
    
    # Print preview (first 200 lines or 2000 characters, whichever is shorter)
    lines = snapshot.split('\n')
    preview_lines = lines[:200] if len(lines) > 200 else lines
    preview = '\n'.join(preview_lines)
    
    if len(preview) > 2000:
        preview = preview[:2000] + "\n... (truncated)"
    
    print("\n=== CONTEXT SNAPSHOT PREVIEW ===\n")
    print(preview)
    print("\n=== END PREVIEW ===\n")
    
    print(f"Full snapshot contains {len(lines)} lines and {len(snapshot)} characters.")


if __name__ == "__main__":
    main()
