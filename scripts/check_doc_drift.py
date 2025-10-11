#!/usr/bin/env python3
"""
Documentation drift auditor script.
Checks for documentation drift, missing SOPs, and outdated PRDs.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from datetime import datetime, timedelta
import re


class DocumentationAuditor:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.findings = []
        
    def add_finding(self, category: str, message: str, severity: str = "INFO"):
        """Add a finding to the audit report."""
        self.findings.append({
            "category": category,
            "message": message,
            "severity": severity
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
                self.add_finding("ERROR", f"Failed to process {py_file}: {e}", "ERROR")
        
        return modules
    
    def get_documented_modules(self) -> Dict[str, List[str]]:
        """Get modules that are documented in .agent/system/."""
        documented = {}
        
        system_docs_path = self.project_root / ".agent" / "system"
        if system_docs_path.exists():
            for md_file in system_docs_path.glob("*.md"):
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract module references
                    module_refs = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*\.py)', content)
                    documented[md_file.stem] = module_refs
                except Exception as e:
                    self.add_finding("ERROR", f"Failed to read {md_file}: {e}", "ERROR")
        
        return documented
    
    def check_orphaned_docs(self):
        """Check for documentation files without corresponding code."""
        docs_path = self.project_root / ".agent" / "system"
        if not docs_path.exists():
            self.add_finding("STRUCTURE", ".agent/system/ directory not found", "WARNING")
            return
        
        for doc_file in docs_path.glob("*.md"):
            with open(doc_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for Python file references
            py_refs = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*\.py)', content)
            
            for py_ref in py_refs:
                py_path = self.project_root / py_ref
                if not py_path.exists():
                    self.add_finding("ORPHAN_DOC", 
                                   f"Documentation {doc_file.name} references non-existent {py_ref}", 
                                   "WARNING")
    
    def check_undocumented_modules(self):
        """Check for Python modules that lack documentation."""
        modules = self.get_python_modules()
        documented = self.get_documented_modules()
        
        # Main modules that should be documented
        key_modules = ["bot.py", "config.py"]
        key_directories = ["core", "helpers", "integrations", "utils"]
        
        for module in key_modules:
            if module not in modules:
                continue
            
            is_documented = False
            for doc_file, refs in documented.items():
                if any(module in ref for ref in refs):
                    is_documented = True
                    break
            
            if not is_documented:
                self.add_finding("UNDOCUMENTED", 
                               f"Key module {module} may lack documentation", 
                               "INFO")
        
        # Check for new files in key directories
        for directory in key_directories:
            dir_path = self.project_root / directory
            if dir_path.exists():
                for py_file in dir_path.glob("*.py"):
                    if py_file.name == "__init__.py":
                        continue
                    
                    rel_path = str(py_file.relative_to(self.project_root))
                    is_documented = False
                    
                    for doc_file, refs in documented.items():
                        if any(py_file.name in ref for ref in refs):
                            is_documented = True
                            break
                    
                    if not is_documented:
                        self.add_finding("UNDOCUMENTED", 
                                       f"Module {rel_path} may need documentation", 
                                       "INFO")
    
    def check_stale_links(self):
        """Check for stale cross-references in documentation."""
        docs_path = self.project_root / ".agent" / "system"
        if not docs_path.exists():
            return
        
        for doc_file in docs_path.glob("*.md"):
            with open(doc_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for markdown links that might be broken
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
            
            for link_text, link_target in links:
                if link_target.startswith('http'):
                    # External link - skip for now
                    continue
                
                # Internal link - check if target exists
                target_path = docs_path / link_target
                if not target_path.exists():
                    self.add_finding("STALE_LINK", 
                                   f"Broken link in {doc_file.name}: [{link_text}]({link_target})", 
                                   "WARNING")
    
    def check_missing_sops(self):
        """Check for missing Standard Operating Procedures."""
        # Common SOPs that should exist
        expected_sops = [
            "deployment.md",
            "onboarding.md", 
            "troubleshooting.md",
            "security.md"
        ]
        
        docs_path = self.project_root / ".agent" / "system"
        if docs_path.exists():
            existing_docs = [f.name for f in docs_path.glob("*.md")]
            
            for sop in expected_sops:
                if sop not in existing_docs:
                    self.add_finding("MISSING_SOP", 
                                   f"Missing SOP: {sop}", 
                                   "INFO")
    
    def check_file_timestamps(self):
        """Check for recently modified files that might need doc updates."""
        recent_threshold = datetime.now() - timedelta(days=7)
        
        for py_file in self.project_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["__pycache__", ".venv", ".git", "scripts"]):
                continue
            
            file_mtime = datetime.fromtimestamp(py_file.stat().st_mtime)
            if file_mtime > recent_threshold:
                rel_path = str(py_file.relative_to(self.project_root))
                self.add_finding("RECENT_CHANGE", 
                               f"Recently modified: {rel_path} ({file_mtime.strftime('%Y-%m-%d')})", 
                               "INFO")
    
    def run_audit(self):
        """Run the complete documentation audit."""
        print("Running Documentation Audit")
        print("=" * 50)
        
        # Run all checks
        self.check_orphaned_docs()
        self.check_undocumented_modules()
        self.check_stale_links()
        self.check_missing_sops()
        self.check_file_timestamps()
        
        # Print results
        if not self.findings:
            print("✅ No documentation issues found!")
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
                severity_symbol = {"ERROR": "[ERROR]", "WARNING": "[WARN]", "INFO": "[INFO]"}
                print(f"  {severity_symbol.get(finding['severity'], '[INFO]')} {finding['message']}")
        
        # Summary
        summary = {"ERROR": 0, "WARNING": 0, "INFO": 0}
        for finding in self.findings:
            summary[finding["severity"]] += 1
        
        print(f"\nSummary:")
        print(f"  Errors: {summary['ERROR']}")
        print(f"  Warnings: {summary['WARNING']}")
        print(f"  Info: {summary['INFO']}")
        
        if summary["ERROR"] > 0:
            print(f"\nAudit completed with {summary['ERROR']} error(s)")
            sys.exit(1)
        else:
            print(f"\nAudit completed successfully")


def main():
    """Main audit function."""
    auditor = DocumentationAuditor()
    auditor.run_audit()


if __name__ == "__main__":
    main()
