#!/usr/bin/env python3
"""
Mermaid Block Extractor

This script extracts mermaid code blocks from markdown files and provides
utilities for working with mermaid diagrams in documentation.

Usage:
    python extract_mermaid_blocks.py <markdown-file> [options]

Options:
    --list          List all mermaid blocks with line numbers
    --extract       Extract blocks to separate files
    --validate      Validate syntax of extracted blocks
    --count         Count total mermaid blocks
    --help          Show this help message
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional


class MermaidExtractor:
    """Extract and work with mermaid code blocks from markdown files."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not self.file_path.suffix.lower() == '.md':
            raise ValueError(f"Not a markdown file: {file_path}")

    def extract_blocks(self) -> List[Tuple[int, str]]:
        """
        Extract all mermaid code blocks from the markdown file.

        Returns:
            List of tuples containing (line_number, block_content)
        """
        with open(self.file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        blocks = []
        in_block = False
        block_start = 0
        current_block = []

        for i, line in enumerate(lines, 1):
            line = line.rstrip()

            if line.strip() == '```mermaid':
                in_block = True
                block_start = i
                current_block = []
            elif line.strip() == '```' and in_block:
                in_block = False
                if current_block:
                    block_content = '\n'.join(current_block).strip()
                    blocks.append((block_start, block_content))
            elif in_block:
                current_block.append(line)

        return blocks

    def list_blocks(self) -> None:
        """List all mermaid blocks with their line numbers."""
        blocks = self.extract_blocks()

        if not blocks:
            print(f"No mermaid blocks found in {self.file_path}")
            return

        print(f"Found {len(blocks)} mermaid block(s) in {self.file_path}:")
        print("-" * 50)

        for i, (line_num, content) in enumerate(blocks, 1):
            # Get first few lines for preview
            lines = content.split('\n')[:3]
            preview = ' '.join(lines).strip()
            if len(preview) > 60:
                preview = preview[:57] + "..."

            print(f"Block {i}: Line {line_num}")
            print(f"  Preview: {preview}")
            print()

    def extract_to_files(self, output_dir: Optional[str] = None) -> None:
        """Extract mermaid blocks to separate .mmd files."""
        if output_dir is None:
            output_dir = self.file_path.stem + "_diagrams"
        else:
            output_dir = Path(output_dir)

        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        blocks = self.extract_blocks()

        if not blocks:
            print(f"No mermaid blocks found in {self.file_path}")
            return

        print(f"Extracting {len(blocks)} diagram(s) to {output_dir}/")

        for i, (line_num, content) in enumerate(blocks, 1):
            filename = f"diagram_{i:02d}_line_{line_num}.mmd"
            output_file = output_dir / filename

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"  ✓ {filename}")

        print(f"\nExtraction complete. Files saved to {output_dir}/")

    def count_blocks(self) -> int:
        """Count total number of mermaid blocks."""
        return len(self.extract_blocks())

    def validate_blocks(self) -> List[Tuple[int, bool, str]]:
        """
        Validate mermaid blocks using basic syntax checks.

        Returns:
            List of tuples: (line_number, is_valid, error_message)
        """
        blocks = self.extract_blocks()
        results = []

        for line_num, content in blocks:
            is_valid, error_msg = self._validate_mermaid_syntax(content)
            results.append((line_num, is_valid, error_msg))

        return results

    def _validate_mermaid_syntax(self, content: str) -> Tuple[bool, str]:
        """
        Perform basic mermaid syntax validation.

        This is a simple validator that checks for common issues.
        For full validation, use the mermaid CLI.
        """
        lines = content.strip().split('\n')
        if not lines:
            return False, "Empty diagram"

        # Check for diagram type declaration
        first_line = lines[0].strip()
        valid_types = [
            'flowchart', 'graph', 'sequenceDiagram', 'classDiagram',
            'erDiagram', 'stateDiagram', 'gantt', 'pie', 'journey',
            'gitgraph', 'mindmap'
        ]

        diagram_type_found = False
        for line in lines[:5]:  # Check first few lines
            line = line.strip()
            for valid_type in valid_types:
                if line.lower().startswith(valid_type.lower()):
                    diagram_type_found = True
                    break
            if diagram_type_found:
                break

        if not diagram_type_found:
            return False, "No valid diagram type declaration found"

        # Check for basic syntax issues
        bracket_stack = []
        brace_stack = []
        paren_stack = []

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('%%'):
                continue

            # Check brackets
            for char in line:
                if char == '[':
                    bracket_stack.append((char, line_num))
                elif char == ']':
                    if not bracket_stack or bracket_stack[-1][0] != '[':
                        return False, f"Unmatched closing bracket at line {line_num}"
                    bracket_stack.pop()
                elif char == '{':
                    brace_stack.append((char, line_num))
                elif char == '}':
                    if not brace_stack or brace_stack[-1][0] != '{':
                        return False, f"Unmatched closing brace at line {line_num}"
                    brace_stack.pop()
                elif char == '(':
                    paren_stack.append((char, line_num))
                elif char == ')':
                    if not paren_stack or paren_stack[-1][0] != '(':
                        return False, f"Unmatched closing parenthesis at line {line_num}"
                    paren_stack.pop()

        # Check for unmatched opening brackets
        if bracket_stack:
            char, line_num = bracket_stack[-1]
            return False, f"Unmatched opening bracket at line {line_num}"
        if brace_stack:
            char, line_num = brace_stack[-1]
            return False, f"Unmatched opening brace at line {line_num}"
        if paren_stack:
            char, line_num = paren_stack[-1]
            return False, f"Unmatched opening parenthesis at line {line_num}"

        return True, ""


def main():
    parser = argparse.ArgumentParser(
        description="Extract and work with mermaid code blocks from markdown files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('file', help='Markdown file to process')
    parser.add_argument('--list', action='store_true',
                       help='List all mermaid blocks with line numbers')
    parser.add_argument('--extract', nargs='?', const='.',
                       help='Extract blocks to separate files (optional: output directory)')
    parser.add_argument('--validate', action='store_true',
                       help='Validate syntax of mermaid blocks')
    parser.add_argument('--count', action='store_true',
                       help='Count total mermaid blocks')

    args = parser.parse_args()

    if not any([args.list, args.extract, args.validate, args.count]):
        args.list = True  # Default action

    try:
        extractor = MermaidExtractor(args.file)

        if args.count:
            count = extractor.count_blocks()
            print(f"Total mermaid blocks: {count}")

        if args.list:
            extractor.list_blocks()

        if args.extract is not None:
            extractor.extract_to_files(args.extract)

        if args.validate:
            results = extractor.validate_blocks()
            print("Validation Results:")
            print("-" * 30)

            all_valid = True
            for line_num, is_valid, error_msg in results:
                status = "✓ VALID" if is_valid else "✗ INVALID"
                print(f"Block at line {line_num}: {status}")
                if not is_valid:
                    print(f"  Error: {error_msg}")
                    all_valid = False

            print("-" * 30)
            if all_valid:
                print("✓ All blocks passed basic validation")
            else:
                print("✗ Some blocks have validation errors")
                sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
