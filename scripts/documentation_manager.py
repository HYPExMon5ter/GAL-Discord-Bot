#!/usr/bin/env python3
"""
Unified Documentation Manager.
Audits and fixes documentation issues in a single script.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from datetime import datetime, timedelta


class DocumentationManager:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.docs_path = self.project_root / ".agent" / "system"
        self.findings = []
        self.fixes_applied = []
        
    def add_finding(self, category: str, message: str, severity: str = "INFO", fixable: bool = True):
        """Add a finding to the audit report."""
        self.findings.append({
            "category": category,
            "message": message,
            "severity": severity,
            "fixable": fixable
        })
    
    def add_fix(self, doc_file: str, description: str):
        """Record a fix that was applied."""
        self.fixes_applied.append({
            "doc_file": doc_file,
            "description": description
        })
    
    def get_python_modules(self) -> Dict[str, List[str]]:
        """Get all Python modules and their classes/functions."""
        modules = {}
        
        for py_file in self.project_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["__pycache__", ".venv", ".git", "scripts"]):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract classes and main functions
                classes = []
                functions = []
                lines = content.split('\n')
                
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('class '):
                        class_name = stripped.split('(')[0].replace('class ', '').replace(':', '')
                        classes.append(class_name)
                    elif stripped.startswith('def ') and not stripped.startswith('def _'):
                        func_name = stripped.split('(')[0].replace('def ', '')
                        if not func_name.startswith('_'):
                            functions.append(func_name)
                    elif stripped.startswith('async def ') and not stripped.startswith('async def _'):
                        func_name = stripped.split('(')[0].replace('async def ', '')
                        if not func_name.startswith('_'):
                            functions.append(func_name)
                
                relative_path = str(py_file.relative_to(self.project_root))
                modules[relative_path] = {
                    "classes": classes,
                    "functions": functions
                }
                
            except Exception as e:
                self.add_finding("ERROR", f"Failed to process {py_file}: {e}", "ERROR", False)
        
        return modules
    
    def check_orphaned_docs(self):
        """Check for documentation files without corresponding code and fix them."""
        if not self.docs_path.exists():
            self.add_finding("STRUCTURE", ".agent/system/ directory not found", "WARNING", False)
            return
        
        for doc_file in self.docs_path.glob("*.md"):
            with open(doc_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for Python file references
            py_refs = re.findall(r'([a-zA-Z_0-9/]*[a-zA-Z_][a-zA-Z0-9_]*\.py)', content)
            
            # Known library/package names that shouldn't be treated as file references
            library_names = {
                'discord.py', 'requests.py', 'asyncio.py', 'aiohttp.py', 'sqlalchemy.py',
                'pandas.py', 'numpy.py', 'matplotlib.py', 'flask.py', 'fastapi.py'
            }
            
            # Special patterns to ignore (self.python_exe, etc.)
            ignore_patterns = [
                r'self\.',  # Python self references in code examples
                r'cls\.',   # Python cls references in code examples
            ]
            
            file_needs_update = False
            
            for py_ref in py_refs:
                # Skip if it's a known library name
                if py_ref in library_names:
                    continue
                
                # Skip if it matches ignore patterns
                if any(re.search(pattern, py_ref) for pattern in ignore_patterns):
                    continue
                
                # Skip if it appears to be in a directory structure listing or code block
                lines = content.split('\n')
                ref_found_in_dir_structure = False
                in_code_block = False
                for i, line in enumerate(lines):
                    if '```' in line:
                        in_code_block = not in_code_block
                    if py_ref in line:
                        # Check if this line appears to be part of a directory tree listing
                        if ('├──' in line or '└──' in line or 
                            (line.strip().startswith(py_ref) and i > 0 and 
                             any('├──' in lines[j] or '└──' in lines[j] for j in range(max(0, i-5), i)))):
                            ref_found_in_dir_structure = True
                            break
                
                if ref_found_in_dir_structure or in_code_block:
                    continue
                    
                # Check if file exists
                py_path = self.project_root / py_ref
                if not py_path.exists():
                    # Try to find the correct path
                    correct_path = self.find_correct_path(py_ref)
                    if correct_path:
                        # Fix the reference
                        content = content.replace(py_ref, correct_path)
                        file_needs_update = True
                        self.add_finding("ORPHAN_DOC", 
                                       f"Fixed reference in {doc_file.name}: {py_ref} -> {correct_path}", 
                                       "INFO", True)
                    else:
                        self.add_finding("ORPHAN_DOC", 
                                       f"Documentation {doc_file.name} references non-existent {py_ref}", 
                                       "WARNING", False)
            
            # Write updated content if needed
            if file_needs_update:
                with open(doc_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.add_fix(doc_file.name, "Fixed file path references")
    
    def find_correct_path(self, incorrect_path: str) -> str:
        """Find the correct path for a file reference."""
        filename = Path(incorrect_path).name
        
        # Search in common directories
        search_dirs = [
            "api/routers",
            "api/schemas", 
            "api/services",
            "api",
            "core/events/handlers",
            "core/events/subscribers",
            "core/commands",
            "core",
            "utils",
            "helpers",
            "integrations",
            "scripts"
        ]
        
        for search_dir in search_dirs:
            search_path = self.project_root / search_dir / filename
            if search_path.exists():
                return str(search_path.relative_to(self.project_root))
        
        return None
    
    def check_stale_links(self):
        """Check for stale cross-references in documentation."""
        if not self.docs_path.exists():
            return
        
        for doc_file in self.docs_path.glob("*.md"):
            with open(doc_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for markdown links that might be broken
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
            file_needs_update = False
            
            for link_text, link_target in links:
                if link_target.startswith('http'):
                    # External link - skip for now
                    continue
                
                # Internal link - check if target exists
                if link_target.startswith('./'):
                    target_path = self.docs_path / link_target[2:]
                elif link_target.startswith('../'):
                    # Navigate up from system directory
                    target_path = self.docs_path.parent / link_target[3:]
                else:
                    target_path = self.docs_path / link_target
                
                # Handle anchor links (strip the anchor part)
                if '#' in target_path.name:
                    target_path = target_path.with_name(target_path.name.split('#')[0])
                
                if not target_path.exists():
                    # Try to find the correct file
                    link_name = Path(link_target).stem
                    correct_path = self.find_documentation_file(link_name)
                    
                    if correct_path:
                        # Fix the link
                        new_target = str(correct_path.relative_to(self.docs_path))
                        if '#' in link_target:
                            new_target += '#' + link_target.split('#')[1]
                        
                        content = content.replace(link_target, new_target)
                        file_needs_update = True
                        self.add_finding("STALE_LINK", 
                                       f"Fixed link in {doc_file.name}: [{link_text}]({link_target}) -> [{link_text}]({new_target})", 
                                       "INFO", True)
                    else:
                        self.add_finding("STALE_LINK", 
                                       f"Broken link in {doc_file.name}: [{link_text}]({link_target})", 
                                       "WARNING", False)
            
            # Write updated content if needed
            if file_needs_update:
                with open(doc_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.add_fix(doc_file.name, "Fixed broken links")
    
    def find_documentation_file(self, name: str) -> Path:
        """Find a documentation file by name."""
        # Look for files that contain the name
        for doc_file in self.docs_path.rglob("*.md"):
            if name.lower() in doc_file.stem.lower():
                return doc_file
        return None
    
    def check_missing_sops(self):
        """Check for missing Standard Operating Procedures."""
        # Common SOPs that should exist
        expected_sops = [
            "deployment.md",
            "onboarding.md", 
            "troubleshooting.md",
            "security.md"
        ]
        
        sops_path = self.project_root / ".agent" / "sops"
        if sops_path.exists():
            existing_docs = [f.name for f in sops_path.glob("*.md")]
            
            for sop in expected_sops:
                if sop not in existing_docs:
                    self.add_finding("MISSING_SOP", 
                                   f"Missing SOP: {sop}", 
                                   "INFO", False)
    
    def check_file_timestamps(self):
        """Check for recently modified files that might need doc updates."""
        recent_threshold = datetime.now() - timedelta(days=7)
        
        # Only report a summary of recent changes
        recent_files = []
        
        for py_file in self.project_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["__pycache__", ".venv", ".git", "scripts"]):
                continue
            
            file_mtime = datetime.fromtimestamp(py_file.stat().st_mtime)
            if file_mtime > recent_threshold:
                rel_path = str(py_file.relative_to(self.project_root))
                recent_files.append((rel_path, file_mtime))
        
        if recent_files:
            # Sort by modification time
            recent_files.sort(key=lambda x: x[1], reverse=True)
            
            # Report only the most recent ones
            for rel_path, file_mtime in recent_files[:5]:
                self.add_finding("RECENT_CHANGE", 
                               f"Recently modified: {rel_path} ({file_mtime.strftime('%Y-%m-%d')})", 
                               "INFO", False)
            
            if len(recent_files) > 5:
                self.add_finding("RECENT_CHANGE", 
                               f"... and {len(recent_files) - 5} more recently modified files", 
                               "INFO", False)
    
    def check_undocumented_modules(self):
        """Check for Python modules that lack documentation."""
        modules = self.get_python_modules()
        
        # Only check for specific new/undocumented modules
        # Focus on recently modified files or special cases
        recent_threshold = datetime.now() - timedelta(days=7)  # Only very recent files
        special_modules = ["core/discord_events.py", "integrations/sheet_cache_manager.py", 
                          "utils/feature_flags.py", "api/dependencies.py", "api/main.py", "api/models.py",
                          "core/views.py", "api/utils/service_runner.py"]
        
        # Check special modules
        for module in special_modules:
            if module in modules:
                self.add_finding("UNDOCUMENTED", 
                               f"Module {module} may need documentation", 
                               "INFO", False)
        
        # Check for recently modified modules that might need documentation
        # Skip modules we've already documented
        documented_modules = {
            "core\\commands\\utility.py",
            "core\\commands\\placement.py", 
            "core\\commands\\registration.py",
            "integrations\\lobby_manager.py",
            "integrations\\riot_api.py",
            "api\\routers\\websocket.py",
            "api\\services\\graphics_service.py",
            "api\\routers\\graphics.py",
            "api\\schemas\\graphics.py"
        }
        
        for py_file in self.project_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["__pycache__", ".venv", ".git", "scripts", "tests", "node_modules"]):
                continue
            
            file_mtime = datetime.fromtimestamp(py_file.stat().st_mtime)
            if file_mtime > recent_threshold:
                # Only flag certain types of files as needing documentation
                rel_path = str(py_file.relative_to(self.project_root))
                if (rel_path not in documented_modules and
                    py_file.name not in ["__init__.py", "test_components.py"] and 
                    not py_file.name.startswith("test_")):
                    self.add_finding("UNDOCUMENTED", 
                                   f"Recently modified module {rel_path} may need documentation", 
                                   "INFO", False)
    
    def fix_architecture_anchor(self):
        """Fix missing anchors in architecture.md."""
        doc_file = self.docs_path / "architecture.md"
        if not doc_file.exists():
            return False
        
        with open(doc_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        file_needs_update = False
        
        # Add missing anchor for Security & Logging
        if "## Security & Logging" in content and "{#security--logging}" not in content:
            content = content.replace(
                "## Security & Logging",
                "## Security & Logging {#security--logging}"
            )
            file_needs_update = True
            self.add_finding("ANCHOR", "Added missing anchor for Security & Logging section", "INFO", True)
        
        if file_needs_update:
            with open(doc_file, 'w', encoding='utf-8') as f:
                f.write(content)
            self.add_fix("architecture.md", "Added missing section anchor")
        
        return True
    
    def run_audit_and_fix(self):
        """Run the complete documentation audit and apply fixes."""
        print("Running Documentation Audit and Fix")
        print("=" * 50)
        
        # Run all checks and fixes
        self.check_orphaned_docs()
        self.check_stale_links()
        self.check_missing_sops()
        self.check_file_timestamps()
        self.check_undocumented_modules()
        self.fix_architecture_anchor()
        
        # Print results
        if not self.findings:
            print("No documentation issues found!")
            return
        
        # Group findings by category
        categories = {}
        for finding in self.findings:
            category = finding["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(finding)
        
        print(f"\nAudit Results: {len(self.findings)} findings")
        print("=" * 50)
        
        # Sort categories by severity
        severity_order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
        
        for category in sorted(categories.keys()):
            print(f"\n{category.replace('_', ' ').title()}")
            print("-" * 30)
            
            # Sort findings within category by severity
            category_findings = sorted(categories[category], 
                                     key=lambda x: severity_order.get(x["severity"], 3))
            
            for finding in category_findings:
                status_symbol = "[FIXED]" if finding.get("fixable", False) else "[OPEN]"
                severity_symbol = {"ERROR": "[ERROR]", "WARNING": "[WARN]", "INFO": "[INFO]"}
                print(f"  {status_symbol} {severity_symbol.get(finding['severity'], '[INFO]')} {finding['message']}")
        
        # Print fixes applied
        if self.fixes_applied:
            print(f"\nFixes Applied: {len(self.fixes_applied)}")
            print("=" * 50)
            for fix in self.fixes_applied:
                print(f"  [FIXED] {fix['doc_file']}: {fix['description']}")
        
        # Summary
        summary = {"ERROR": 0, "WARNING": 0, "INFO": 0}
        for finding in self.findings:
            summary[finding["severity"]] += 1
        
        print(f"\nSummary:")
        print(f"  Errors: {summary['ERROR']}")
        print(f"  Warnings: {summary['WARNING']}")
        print(f"  Info: {summary['INFO']}")
        print(f"  Fixes Applied: {len(self.fixes_applied)}")
        
        if summary["ERROR"] > 0:
            print(f"\nAudit completed with {summary['ERROR']} error(s)")
            sys.exit(1)
        else:
            print(f"\nAudit completed successfully")


def main():
    """Main function."""
    manager = DocumentationManager()
    manager.run_audit_and_fix()


if __name__ == "__main__":
    main()
