---
id: system.scripts
version: 1.0
last_updated: 2025-10-10
tags: [system, scripts, automation, maintenance]
---

# Scripts Directory Documentation

## Purpose
The `scripts/` directory contains automation and maintenance utilities for the Guardian Angel League Discord Bot system. These scripts support documentation management, system monitoring, and database operations.

## Directory Structure
```
scripts/
├── check_doc_drift.py          # Documentation audit and drift detection
├── generate_snapshot.py        # AI session context snapshot generator  
├── migrate_columns.py          # Database schema migration utility
└── update_system_docs.py       # System documentation update automation
```

## Script Details

### 1. Documentation Drift Auditor (`check_doc_drift.py`)
**Purpose**: Automated auditing of documentation completeness and accuracy  
**Size**: 11,175 lines  
**Dependencies**: Standard library (os, sys, pathlib, datetime, re)  

#### Functionality
- **Module Analysis**: Scans Python codebase for classes, functions, and modules
- **Documentation Coverage**: Identifies undocumented code components
- **Cross-Reference Validation**: Checks for broken internal links and references
- **SOP Gap Detection**: Identifies missing Standard Operating Procedures
- **Pattern Recognition**: Detects repeated workflows that may need SOPs

#### Key Features
- **Comprehensive Scanning**: Analyzes entire codebase excluding __pycache__, .venv, .git
- **Smart Detection**: Extracts class definitions and public functions
- **Audit Reporting**: Generates structured findings with severity levels
- **Pattern Matching**: Identifies recurring code patterns for SOP creation

#### Usage
```bash
python scripts/check_doc_drift.py
```

#### Output
- Console report with findings categorized by severity
- Recommendations for missing documentation
- Pattern detection results for SOP creation
- Cross-reference validation results

#### Configuration
- **Skip Directories**: Automatically excludes build artifacts and cache directories
- **Function Detection**: Identifies public functions (non-underscore prefixed)
- **Class Extraction**: Parses class definitions and inheritance
- **Severity Levels**: INFO, WARNING, ERROR for different finding types

### 2. Context Snapshot Generator (`generate_snapshot.py`)
**Purpose**: Creates comprehensive system state snapshots for AI sessions  
**Size**: 9,208 lines  
**Dependencies**: Standard library (os, json, pathlib, datetime, typing)  

#### Functionality
- **Project Structure Analysis**: Maps complete codebase organization
- **Module Documentation**: Extracts functions and classes from Python files
- **Configuration Capture**: Documents current system configuration state
- **Dependency Mapping**: Records package versions and requirements
- **File Metadata**: Captures file sizes, modification dates, and relationships

#### Key Features
- **Comprehensive Coverage**: Analyzes core/, helpers/, integrations/, utils/ directories
- **Function Extraction**: Identifies both synchronous and asynchronous functions
- **Class Parsing**: Extracts class definitions and inheritance relationships
- **JSON Output**: Structured data format for AI consumption

#### Usage
```bash
python scripts/generate_snapshot.py
```

#### Output
- JSON snapshot file with complete system state
- Module structure with functions and classes
- File metadata and relationships
- Configuration state capture

#### Configuration
- **Project Root Detection**: Automatically identifies project boundaries
- **Module Filtering**: Focuses on main application directories
- **Encoding Support**: Handles UTF-8 file encoding
- **Error Handling**: Graceful handling of unreadable files

### 3. Database Migration Utility (`migrate_columns.py`)
**Purpose**: Migrates configuration from config.yaml to persistence system  
**Size**: 2,905 lines  
**Dependencies**: asyncio, logging, os, sys, core.migration  

#### Functionality
- **Schema Migration**: Transitions from YAML-based to database storage
- **Configuration Transfer**: Moves column assignments to persistence layer
- **Data Validation**: Ensures migration integrity and completeness
- **Error Handling**: Comprehensive error reporting and rollback capabilities
- **Progress Tracking**: Detailed migration status and results reporting

#### Key Features
- **Async Operations**: Uses asyncio for efficient database operations
- **Batch Processing**: Handles multiple guild configurations
- **Validation Checks**: Ensures data integrity during migration
- **Rollback Support**: Ability to undo failed migrations
- **Status Reporting**: Detailed success/failure statistics

#### Usage
```bash
python scripts/migrate_columns.py
```

#### Output
- Migration progress reports
- Success/failure statistics
- Validation error details
- Configuration cleanup confirmation

#### Configuration
- **Project Root Setup**: Automatically configures Python path
- **Logging Configuration**: Configurable log levels and formatting
- **Error Recovery**: Comprehensive error handling and reporting

### 4. System Documentation Updater (`update_system_docs.py`)
**Purpose**: Automated updates to .agent/system documentation  
**Size**: 6,566 lines  
**Dependencies**: Standard library (os, sys, pathlib, datetime, typing)  

#### Functionality
- **Code Analysis**: Scans codebase for recent changes and updates
- **Documentation Sync**: Updates .agent/system files with current state
- **Version Management**: Maintains documentation versioning and timestamps
- **Cross-Reference Updates**: Ensures internal links remain valid
- **Metadata Updates**: Refreshes file sizes, line counts, and timestamps

#### Key Features
- **Incremental Updates**: Processes only modified files for efficiency
- **Function Extraction**: Identifies both synchronous and asynchronous functions
- **Class Documentation**: Updates class definitions and inheritance
- **Path Resolution**: Handles relative and absolute path references
- **Version Control**: Maintains consistent version numbering

#### Usage
```bash
python scripts/update_system_docs.py
```

#### Output
- Updated .agent/system documentation files
- Version increment reports
- Cross-reference validation results
- File metadata updates

#### Configuration
- **Path Management**: Automatic project root detection
- **File Filtering**: Excludes build artifacts and cache directories
- **Encoding Support**: UTF-8 file processing
- **Error Tolerance**: Continues processing despite individual file errors

## Integration Points

### Documentation System Integration
- **.agent Directory**: All scripts work with the .agent documentation structure
- **Version Control**: Scripts maintain documentation versioning and timestamps
- **Cross-References**: Automated updates to maintain link integrity
- **Metadata Sync**: Keep documentation synchronized with codebase changes

### Database Integration
- **Migration Scripts**: Direct interaction with persistence layer
- **Configuration Management**: Handles YAML to database transitions
- **Validation Logic**: Ensures data integrity during migrations
- **Error Handling**: Comprehensive database error management

### Code Analysis Integration
- **AST Parsing**: Advanced code structure analysis
- **Function Detection**: Synchronous and asynchronous function identification
- **Class Extraction**: Inheritance relationship mapping
- **Pattern Recognition**: Workflow detection for SOP generation

## Dependencies and Requirements

### System Dependencies
- **Python 3.8+**: Required for asyncio and type annotations
- **Standard Library**: All scripts use only standard library modules
- **Pathlib**: Modern path handling for cross-platform compatibility
- **JSON Module**: For structured data output and input

### Application Dependencies
- **Core Modules**: Access to core.migration for database operations
- **Configuration System**: Integration with bot configuration management
- **Database Access**: Connection to persistence layer for migrations

### External Dependencies
- **None**: All scripts are self-contained with no external package requirements

## Usage Patterns

### Maintenance Workflows
1. **Daily**: Run `check_doc_drift.py` to identify documentation gaps
2. **Weekly**: Execute `update_system_docs.py` after code changes
3. **On Demand**: Use `generate_snapshot.py` for AI session preparation
4. **One-time**: Run `migrate_columns.py` for system upgrades

### Development Workflows
1. **Before Commit**: Run documentation audit to ensure completeness
2. **After Feature**: Update system documentation to reflect changes
3. **Before Release**: Generate full snapshot for release documentation
4. **During Migration**: Use migration utilities for system upgrades

### CI/CD Integration
1. **Pre-commit Hooks**: Automated documentation quality checks
2. **Build Pipeline**: Documentation update and validation
3. **Release Process**: Comprehensive documentation generation
4. **Monitoring**: Regular drift detection and reporting

## Error Handling and Recovery

### Script-Level Error Handling
- **Graceful Degradation**: Scripts continue processing despite individual file errors
- **Comprehensive Logging**: Detailed error reporting with context
- **Recovery Mechanisms**: Automatic retry logic for transient failures
- **Status Reporting**: Clear success/failure indicators

### Data Integrity Protection
- **Validation Checks**: Ensure data consistency during operations
- **Backup Mechanisms**: Preserve original state before modifications
- **Rollback Support**: Ability to undo failed operations
- **Audit Trails**: Complete logging of all modifications

### System Integration Errors
- **Dependency Resolution**: Handle missing modules gracefully
- **Path Resolution**: Manage file system access issues
- **Permission Handling**: Deal with access restriction problems
- **Resource Management**: Proper cleanup of temporary resources

## Performance Considerations

### Optimization Strategies
- **Selective Processing**: Only process modified files when possible
- **Batch Operations**: Group similar operations for efficiency
- **Caching**: Cache results for repeated operations
- **Async Operations**: Use asyncio for I/O-bound tasks

### Resource Management
- **Memory Usage**: Efficient handling of large codebases
- **File I/O**: Optimized file reading and writing
- **CPU Usage**: Minimal impact on system performance
- **Disk Space:": Efficient use of temporary storage

### Scalability Features
- **Large Codebases**: Handle projects with thousands of files
- **Deep Directory Structures**: Manage nested folder hierarchies
- **Multiple Languages**: Extensible for different file types
- **Concurrent Processing**: Parallel operation support

## Security Considerations

### Data Protection
- **Local Processing**: All operations performed locally without external data transmission
- **Permission Handling**: Respect file system access restrictions
- **Sensitive Data**: Automatic masking of sensitive information
- **Audit Logging**: Complete record of all operations

### Access Control
- **File System Permissions**: Operate within existing permission boundaries
- **Database Access**: Use appropriate database credentials and permissions
- **Configuration Security**: Secure handling of configuration files
- **Network Security**: No external network dependencies

## Maintenance and Updates

### Regular Maintenance
- **Script Updates**: Keep scripts current with system changes
- **Dependency Updates**: Maintain compatibility with updated libraries
- **Performance Optimization**: Regular performance reviews and improvements
- **Feature Enhancements**: Add new functionality based on user feedback

### Version Management
- **Semantic Versioning**: Consistent version numbering across scripts
- **Change Documentation**: Detailed changelog for each version
- **Backward Compatibility**: Maintain compatibility with existing workflows
- **Migration Support**: Smooth transitions between versions

## Future Development

### Planned Enhancements
- **Parallel Processing**: Multi-threaded operation for large codebases
- **Plugin Architecture**: Extensible system for custom analyzers
- **Web Interface**: Browser-based script management and execution
- **API Integration**: RESTful API for script automation

### Integration Opportunities
- **IDE Plugins**: Direct integration with development environments
- **CI/CD Platforms**: Native integration with build systems
- **Monitoring Systems**: Integration with system monitoring tools
- **Documentation Platforms**: Direct publishing to documentation systems

---

**Version**: 1.0  
**Last Updated**: 2025-10-10  
**Total Scripts**: 4 utilities  
**Combined Size**: ~30,000 lines of code  
**Maintained By**: Guardian Angel League Development Team
