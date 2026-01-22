#!/bin/bash

# Mermaid Diagram Validator and Auto-Fixer
# This script validates mermaid diagrams in markdown files and attempts to fix common syntax errors

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if mmdc (mermaid CLI) is installed, install if missing
check_mmdc() {
    if ! command -v mmdc &> /dev/null; then
        echo -e "${YELLOW}Mermaid CLI (mmdc) not found. Installing globally...${NC}"

        # Check if npm is available
        if ! command -v npm &> /dev/null; then
            echo -e "${RED}Error: npm is not installed. Please install Node.js and npm first.${NC}"
            exit 1
        fi

        # Install mermaid CLI globally
        echo -e "${BLUE}Running: npm install -g @mermaid-js/mermaid-cli${NC}"
        if npm install -g @mermaid-js/mermaid-cli; then
            echo -e "${GREEN}✓ Mermaid CLI installed successfully${NC}"

            # Verify installation
            if command -v mmdc &> /dev/null; then
                echo -e "${GREEN}✓ mmdc command is now available${NC}"
            else
                echo -e "${RED}Error: Installation completed but mmdc command not found in PATH${NC}"
                echo -e "${YELLOW}You may need to restart your terminal or update your PATH${NC}"
                exit 1
            fi
        else
            echo -e "${RED}Error: Failed to install Mermaid CLI${NC}"
            echo -e "${YELLOW}Try installing manually: npm install -g @mermaid-js/mermaid-cli${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✓ Mermaid CLI found${NC}"
    fi
}

# Extract mermaid code blocks from markdown file
extract_mermaid_blocks() {
    local file="$1"
    local temp_dir="$2"

    # Use awk to extract mermaid code blocks
    awk '
    BEGIN { in_block = 0; block_num = 0 }
    /^```mermaid$/ { in_block = 1; block_num++; print "=== BLOCK " block_num " ===" > "'$temp_dir'/blocks.txt"; next }
    /^```$/ && in_block { in_block = 0; print "" >> "'$temp_dir'/blocks.txt"; next }
    in_block { print >> "'$temp_dir'/blocks.txt" }
    ' "$file"
}

# Validate a single mermaid diagram
validate_diagram() {
    local diagram_file="$1"
    local output_file="/tmp/mermaid-validation-$(basename "$diagram_file" .mmd).svg"

    echo -e "${BLUE}Validating diagram: $diagram_file${NC}"

    # Run mermaid CLI validation
    if mmdc -i "$diagram_file" -o "$output_file" 2>&1; then
        echo -e "${GREEN}✓ Diagram is valid${NC}"
        rm -f "$output_file"
        return 0
    else
        local error_output
        error_output=$(mmdc -i "$diagram_file" -o "$output_file" 2>&1)
        echo -e "${RED}✗ Diagram has errors:${NC}"
        echo "$error_output"
        rm -f "$output_file"
        return 1
    fi
}

# Attempt to fix common mermaid syntax errors
fix_mermaid_syntax() {
    local input_file="$1"
    local output_file="$2"

    echo -e "${YELLOW}Attempting to fix common syntax errors...${NC}"

    # Read the input file
    local content
    content=$(cat "$input_file")

    # Apply fixes
    content=$(echo "$content" | sed 's/->>/-->>/g')  # Fix sequence diagram arrows
    content=$(echo "$content" | sed 's/->/-->/g')    # Fix other arrows
    content=$(echo "$content" | sed 's/<-/<--/g')    # Fix reverse arrows

    # Fix unbalanced brackets (simple cases)
    content=$(echo "$content" | sed 's/\[ \([^]]*\)$/[\1]/g')  # Fix missing closing brackets
    content=$(echo "$content" | sed 's/^\([^[]*\) \]/[\1]/g')  # Fix missing opening brackets

    # Fix common typos in keywords
    content=$(echo "$content" | sed 's/flowchart/flowchart/gI')
    content=$(echo "$content" | sed 's/sequencediagram/sequenceDiagram/gI')
    content=$(echo "$content" | sed 's/erdiagram/erDiagram/gI')
    content=$(echo "$content" | sed 's/classdiagram/classDiagram/gI')
    content=$(echo "$content" | sed 's/statediagram/stateDiagram/gI')

    # Write fixed content
    echo "$content" > "$output_file"
}

# Process a markdown file
process_markdown_file() {
    local file="$1"
    local temp_dir
    temp_dir=$(mktemp -d)

    echo -e "${BLUE}Processing file: $file${NC}"

    # Extract mermaid blocks
    extract_mermaid_blocks "$file" "$temp_dir"

    if [ ! -f "$temp_dir/blocks.txt" ] || [ ! -s "$temp_dir/blocks.txt" ]; then
        echo -e "${YELLOW}No mermaid diagrams found in $file${NC}"
        rm -rf "$temp_dir"
        return 0
    fi

    local has_errors=false
    local block_num=1

    # Process each block
    while IFS= read -r line; do
        if [[ $line =~ ===\ BLOCK\ ([0-9]+)\ === ]]; then
            current_block="${BASH_REMATCH[1]}"
            block_file="$temp_dir/block_$current_block.mmd"
            : > "$block_file"  # Create empty file
        elif [[ -n $line ]] && [[ -n $current_block ]]; then
            echo "$line" >> "$block_file"
        fi
    done < "$temp_dir/blocks.txt"

    # Validate each diagram
    for block_file in "$temp_dir"/block_*.mmd; do
        if [ -f "$block_file" ]; then
            echo -e "${BLUE}Validating diagram $block_num in $file${NC}"

            if ! validate_diagram "$block_file"; then
                has_errors=true

                # Attempt to fix
                fixed_file="$temp_dir/fixed_$(basename "$block_file")"
                fix_mermaid_syntax "$block_file" "$fixed_file"

                if validate_diagram "$fixed_file"; then
                    echo -e "${GREEN}✓ Diagram fixed successfully${NC}"
                    # TODO: Could optionally update the original file here
                else
                    echo -e "${RED}✗ Could not automatically fix diagram${NC}"
                fi
            fi

            ((block_num++))
        fi
    done

    # Cleanup
    rm -rf "$temp_dir"

    if $has_errors; then
        return 1
    else
        return 0
    fi
}

# Process directory recursively
process_directory() {
    local dir="$1"
    local has_errors=false

    echo -e "${BLUE}Processing directory: $dir${NC}"

    while IFS= read -r -d '' file; do
        if [[ $file =~ \.md$ ]]; then
            if ! process_markdown_file "$file"; then
                has_errors=true
            fi
        fi
    done < <(find "$dir" -name "*.md" -type f -print0)

    if $has_errors; then
        return 1
    else
        return 0
    fi
}

# Main function
main() {
    check_mmdc

    if [ $# -eq 0 ]; then
        echo -e "${RED}Usage: $0 <markdown-file-or-directory>${NC}"
        echo -e "${YELLOW}Examples:${NC}"
        echo "  $0 docs/README.md"
        echo "  $0 docs/"
        exit 1
    fi

    local target="$1"
    local exit_code=0

    if [ -f "$target" ]; then
        if [[ $target =~ \.md$ ]]; then
            if ! process_markdown_file "$target"; then
                exit_code=1
            fi
        else
            echo -e "${RED}Error: $target is not a markdown file${NC}"
            exit_code=1
        fi
    elif [ -d "$target" ]; then
        if ! process_directory "$target"; then
            exit_code=1
        fi
    else
        echo -e "${RED}Error: $target does not exist${NC}"
        exit_code=1
    fi

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ All mermaid diagrams validated successfully${NC}"
    else
        echo -e "${RED}✗ Some diagrams have validation errors${NC}"
    fi

    exit $exit_code
}

main "$@"
