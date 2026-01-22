# Mermaid Diagram Creator & Validator Skill

This skill provides comprehensive support for creating and validating Mermaid diagrams in markdown files within the AI Voice Agent Platform project.

## Overview

The skill consists of:
- **SKILL.md**: Main skill documentation with usage instructions
- **scripts/**: Reusable scripts for diagram creation and validation
  - `validate_mermaid.sh`: Comprehensive validation and auto-fix script
  - `create_diagram_template.sh`: Template generator for common diagram types
  - `extract_mermaid_blocks.py`: Python utility for extracting and analyzing mermaid blocks

## Installation Requirements

### Required Dependencies
- **Node.js and npm**: Required for Mermaid CLI installation and operation

### Automatic Installation
The skill automatically installs the Mermaid CLI (`@mermaid-js/mermaid-cli`) globally if not found. No manual installation is required - just ensure Node.js and npm are available on your system.

**What gets installed automatically:**
- `@mermaid-js/mermaid-cli` - Mermaid command-line interface for diagram validation

**Verification:**
```bash
# Check if Node.js and npm are available
node --version && npm --version

# The skill will install and verify mmdc automatically
./scripts/validate_mermaid.sh --help
```

## Usage Examples

### Creating Diagram Templates

Generate templates for common diagram types:

```bash
# Create a flowchart template
./scripts/create_diagram_template.sh flowchart

# Create a sequence diagram template
./scripts/create_diagram_template.sh sequence

# Create an ER diagram template
./scripts/create_diagram_template.sh er
```

### Validating Diagrams

Validate all diagrams in a markdown file:

```bash
# Validate a specific file
./scripts/validate_mermaid.sh docs/README.md

# Validate all markdown files in a directory
./scripts/validate_mermaid.sh docs/
```

### Extracting and Analyzing Diagrams

Use the Python utility for advanced diagram analysis:

```bash
# List all mermaid blocks with line numbers
python3 scripts/extract_mermaid_blocks.py file.md --list

# Validate diagram syntax
python3 scripts/extract_mermaid_blocks.py file.md --validate

# Extract diagrams to separate files
python3 scripts/extract_mermaid_blocks.py file.md --extract output_dir

# Count total diagrams
python3 scripts/extract_mermaid_blocks.py file.md --count
```

## Integration with Development Workflow

### Pre-commit Validation
Consider adding mermaid validation to your pre-commit hooks:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: validate-mermaid
        name: Validate Mermaid Diagrams
        entry: ./scripts/validate_mermaid.sh
        language: system
        files: \.md$
        pass_filenames: false
```

### Documentation Standards
When working with documentation:

1. **Create diagrams** using the template generator
2. **Validate immediately** after creation/editing
3. **Fix any issues** found by the validator
4. **Commit only validated diagrams**

## Supported Diagram Types

- **flowchart/graph**: Process flows, decision trees, system architectures
- **sequenceDiagram**: Actor interactions over time
- **classDiagram**: OOP class relationships and inheritance
- **erDiagram**: Entity-relationship database schemas
- **stateDiagram**: State machines and transitions
- **gantt**: Project timelines and schedules
- **pie**: Data visualization charts
- **journey**: User experience flows
- **gitgraph**: Git branching diagrams
- **mindmap**: Mind mapping diagrams

## Error Correction

The validation script automatically attempts to fix common syntax errors:

- Missing or incorrect arrow types (`->`, `-->`, `==>`, etc.)
- Unbalanced brackets `[]`, braces `{}`, parentheses `()`
- Invalid node names and IDs
- Common keyword typos
- Malformed connection syntax

## File Structure

```
.claude/skills/mermaid-diagram-creator/
├── SKILL.md                    # Main skill documentation
├── README.md                   # This file
└── scripts/
    ├── validate_mermaid.sh     # Bash validation script
    ├── create_diagram_template.sh  # Template generator
    └── extract_mermaid_blocks.py   # Python extraction utility
```

## Troubleshooting

### Common Issues

1. **"npm not found"**: Ensure Node.js and npm are installed
   ```bash
   # Install Node.js (varies by system)
   # macOS with Homebrew:
   brew install node

   # Ubuntu/Debian:
   curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
   sudo apt-get install -y nodejs
   ```

2. **Permission denied**: Make scripts executable
   ```bash
   chmod +x scripts/*.sh
   ```

3. **Python not found**: Ensure Python 3 is available
   ```bash
   python3 --version
   ```

4. **Installation fails**: The skill will automatically retry or provide manual installation instructions

### Validation Errors

- **"No valid diagram type found"**: Ensure diagram starts with a valid type (flowchart, sequenceDiagram, etc.)
- **"Unmatched brackets"**: Check for missing closing brackets `]`, braces `}`, or parentheses `)`
- **"Invalid node names"**: Node IDs should be alphanumeric with underscores, no spaces

## Contributing

When extending this skill:

1. Update SKILL.md with new functionality
2. Add comprehensive documentation
3. Test scripts thoroughly
4. Follow the existing code style and patterns

## Related Skills

This skill complements other documentation skills:
- `doc-coauthoring`: For general documentation writing
- `frontend-design`: For UI/UX diagram creation
- `pptx`: For presentation diagrams
