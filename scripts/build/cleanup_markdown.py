#!/usr/bin/env python3
"""
Markdown Linting Cleanup Script for Lucid Project

This script fixes common Markdown linting errors in .md files:
- MD009: Removes trailing spaces (no-trailing-spaces)
- MD012: Removes multiple consecutive blank lines (no-multiple-blanks)
- MD022: Adds blank lines around headings (blanks-around-headings)
- MD029: Fixes ordered list item prefixes (ol-prefix)
- MD031: Adds blank lines around fenced code blocks (blanks-around-fences)
- MD032: Adds blank lines around lists (blanks-around-lists)
- MD036: Converts emphasis to proper headings (no-emphasis-as-heading)
- MD037: Removes spaces inside emphasis markers (no-space-in-emphasis)
- MD040: Adds language specification to fenced code blocks (fenced-code-language)
- MD047: Ensures files end with single newline (single-trailing-newline)
- MD058: Adds blank lines around tables (blanks-around-tables)

Usage:
    python scripts/build/cleanup_markdown.py [--dry-run] [--verbose] [--path PATH]

Author: AI Assistant
Date: 2025-01-27
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Optional


class MarkdownCleaner:
    """Handles cleaning up Markdown files according to linting rules."""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.fixes_applied = 0
        self.files_processed = 0
        
        # Patterns for detection
        self.heading_pattern = re.compile(r'^(\s*#{1,6}\s+.+)$', re.MULTILINE)
        self.fenced_code_pattern = re.compile(r'^(\s*```[^`\n]*)$', re.MULTILINE)
        self.list_pattern = re.compile(r'^(\s*[-*+]\s+.+)$', re.MULTILINE)
        self.numbered_list_pattern = re.compile(r'^(\s*\d+\.\s+.+)$', re.MULTILINE)
        self.table_pattern = re.compile(r'^(\s*\|.*\|.*)$', re.MULTILINE)
        self.emphasis_pattern = re.compile(r'\*([^*\s]+.*?)\*|\b_([^_\s]+.*?)_\b', re.MULTILINE)
        self.emphasis_heading_pattern = re.compile(r'^(\s*)\*([^*\n]+)\*(\s*)$', re.MULTILINE)
        self.ordered_list_pattern = re.compile(r'^(\s*)(\d+)\.(\s+.+)$', re.MULTILINE)
        self.trailing_space_pattern = re.compile(r'[ \t]+$', re.MULTILINE)
        self.multiple_blank_lines_pattern = re.compile(r'\n\s*\n\s*\n', re.MULTILINE)
        
        # Languages to add for code blocks without language specification
        self.common_languages = {
            'python': ['py', 'python'],
            'bash': ['sh', 'bash', 'shell', 'powershell', 'ps1'],
            'yaml': ['yml', 'yaml'],
            'json': ['json'],
            'javascript': ['js', 'javascript'],
            'typescript': ['ts', 'typescript'],
            'dockerfile': ['dockerfile'],
            'docker-compose': ['docker-compose'],
            'markdown': ['md', 'markdown'],
            'sql': ['sql'],
            'html': ['html', 'htm'],
            'css': ['css'],
            'xml': ['xml'],
            'ini': ['ini', 'cfg', 'conf'],
            'toml': ['toml'],
            'rust': ['rs', 'rust'],
            'go': ['go', 'golang'],
            'java': ['java'],
            'cpp': ['cpp', 'cc', 'cxx'],
            'c': ['c'],
            'php': ['php'],
            'ruby': ['rb', 'ruby'],
            'perl': ['pl', 'perl'],
            'scala': ['scala'],
            'kotlin': ['kt', 'kotlin'],
            'swift': ['swift'],
            'text': ['txt', 'log', 'output']
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log messages with appropriate verbosity."""
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(f"[{level}] {message}")
    
    def detect_language_from_content(self, code_block: str) -> Optional[str]:
        """Try to detect programming language from code block content."""
        code_block = code_block.strip()
        
        # Check for shebang
        if code_block.startswith('#!'):
            shebang = code_block.split('\n')[0].lower()
            for lang, extensions in self.common_languages.items():
                for ext in extensions:
                    if ext in shebang:
                        return lang
        
        # Check for common patterns
        patterns = {
            'python': [r'import\s+\w+', r'def\s+\w+', r'class\s+\w+', r'from\s+\w+\s+import'],
            'bash': [r'#!/bin/bash', r'#!/bin/sh', r'echo\s+', r'export\s+\w+', r'cd\s+'],
            'powershell': [r'Get-ChildItem', r'Write-Host', r'Import-Module', r'\$\w+\s*='],
            'yaml': [r'^\s*\w+:\s*$', r'^\s*-\s+\w+:', r'^\s*version:\s*'],
            'json': [r'^\s*\{', r'^\s*\[', r'^\s*".*":\s*'],
            'dockerfile': [r'^FROM\s+', r'^RUN\s+', r'^COPY\s+', r'^WORKDIR\s+'],
            'docker-compose': [r'^version:\s*', r'^services:', r'^networks:', r'^volumes:'],
            'sql': [r'^SELECT\s+', r'^INSERT\s+INTO', r'^UPDATE\s+', r'^DELETE\s+FROM'],
            'javascript': [r'function\s+\w+', r'const\s+\w+', r'let\s+\w+', r'var\s+\w+'],
            'typescript': [r'interface\s+\w+', r'type\s+\w+', r'export\s+interface'],
            'html': [r'<html>', r'<head>', r'<body>', r'<!DOCTYPE'],
            'css': [r'^\s*\w+\s*\{', r'^\s*\.\w+', r'^\s*#\w+'],
            'xml': [r'<\?xml', r'<[a-zA-Z]+[^>]*>'],
            'ini': [r'^\s*\[.*\]', r'^\s*\w+\s*='],
            'toml': [r'^\s*\[.*\]', r'^\s*\w+\s*=\s*["\']'],
            'rust': [r'fn\s+\w+', r'let\s+\w+', r'use\s+\w+', r'struct\s+\w+'],
            'go': [r'package\s+\w+', r'func\s+\w+', r'import\s+\w+'],
            'java': [r'public\s+class\s+\w+', r'import\s+\w+', r'package\s+\w+'],
            'cpp': [r'#include\s*<', r'int\s+main\s*\(', r'std::'],
            'c': [r'#include\s*<', r'int\s+main\s*\(', r'printf\s*\('],
            'php': [r'<\?php', r'\$\w+', r'function\s+\w+'],
            'ruby': [r'def\s+\w+', r'class\s+\w+', r'require\s+'],
            'perl': [r'#!/usr/bin/perl', r'my\s+\$\w+', r'use\s+\w+'],
            'scala': [r'object\s+\w+', r'class\s+\w+', r'def\s+\w+'],
            'kotlin': [r'fun\s+\w+', r'class\s+\w+', r'import\s+\w+'],
            'swift': [r'func\s+\w+', r'class\s+\w+', r'import\s+\w+']
        }
        
        for lang, lang_patterns in patterns.items():
            for pattern in lang_patterns:
                if re.search(pattern, code_block, re.MULTILINE | re.IGNORECASE):
                    return lang
        
        return None
    
    def remove_trailing_spaces(self, content: str) -> str:
        """Remove trailing spaces from lines (MD009)."""
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            # Remove trailing spaces and tabs
            cleaned_line = line.rstrip()
            if line != cleaned_line:
                self.fixes_applied += 1
                self.log(f"Removed trailing spaces from line: {line.strip()}")
            new_lines.append(cleaned_line)
        
        return '\n'.join(new_lines)
    
    def remove_multiple_blank_lines(self, content: str) -> str:
        """Remove multiple consecutive blank lines (MD012)."""
        # Replace 3 or more consecutive newlines with 2 newlines
        cleaned_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        if cleaned_content != content:
            self.fixes_applied += 1
            self.log("Removed multiple consecutive blank lines")
        
        return cleaned_content
    
    def fix_ordered_list_prefixes(self, content: str) -> str:
        """Fix ordered list item prefixes to use 1. format (MD029)."""
        lines = content.split('\n')
        new_lines = []
        list_counter = 1
        
        for line in lines:
            # Check if line is an ordered list item
            match = re.match(r'^(\s*)(\d+)\.(\s+.+)$', line)
            if match:
                indent, number, rest = match.groups()
                new_line = f"{indent}1.{rest}"
                if line != new_line:
                    self.fixes_applied += 1
                    self.log(f"Fixed ordered list prefix: {line.strip()} -> {new_line.strip()}")
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def convert_emphasis_to_headings(self, content: str) -> str:
        """Convert emphasis used as headings to proper headings (MD036)."""
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            # Check if line is just emphasis (likely a heading)
            emphasis_match = re.match(r'^(\s*)\*([^*\n]+)\*(\s*)$', line)
            if emphasis_match:
                indent, text, trailing = emphasis_match.groups()
                # Convert to heading (determine level based on indentation)
                heading_level = min(6, max(1, len(indent) // 2 + 1))
                new_line = f"{indent}{'#' * heading_level} {text.strip()}"
                self.fixes_applied += 1
                self.log(f"Converted emphasis to heading: {line.strip()} -> {new_line.strip()}")
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def fix_emphasis_spacing(self, content: str) -> str:
        """Remove spaces inside emphasis markers (MD037)."""
        def fix_emphasis_match(match):
            full_match = match.group(0)
            if '*' in full_match:
                # Handle asterisk emphasis
                inner_text = match.group(1)
                if inner_text and inner_text[0] == ' ' and inner_text[-1] == ' ':
                    # Remove leading and trailing spaces
                    fixed_text = inner_text.strip()
                    self.fixes_applied += 1
                    self.log(f"Fixed emphasis spacing: {full_match} -> *{fixed_text}*")
                    return f"*{fixed_text}*"
            elif '_' in full_match:
                # Handle underscore emphasis
                inner_text = match.group(2)
                if inner_text and inner_text[0] == ' ' and inner_text[-1] == ' ':
                    # Remove leading and trailing spaces
                    fixed_text = inner_text.strip()
                    self.fixes_applied += 1
                    self.log(f"Fixed emphasis spacing: {full_match} -> _{fixed_text}_")
                    return f"_{fixed_text}_"
            return full_match
        
        # Fix spaces in emphasis markers
        cleaned_content = re.sub(r'\*([^*\s]+.*?)\*|\b_([^_\s]+.*?)_\b', fix_emphasis_match, content)
        
        return cleaned_content
    
    def add_blank_lines_around_tables(self, content: str) -> str:
        """Add blank lines around tables (MD058)."""
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            # Check if current line is a table row
            if re.match(r'^\s*\|.*\|.*$', line):
                # Add blank line before table (if not at start and previous line is not blank)
                if i > 0 and lines[i-1].strip() != '':
                    new_lines.append('')
                    self.fixes_applied += 1
                    self.log(f"Added blank line before table: {line.strip()}")
                
                new_lines.append(line)
                
                # Add blank line after table (if not at end and next line is not blank and not another table row)
                if (i < len(lines) - 1 and 
                    lines[i+1].strip() != '' and 
                    not re.match(r'^\s*\|.*\|.*$', lines[i+1])):
                    new_lines.append('')
                    self.fixes_applied += 1
                    self.log(f"Added blank line after table: {line.strip()}")
            else:
                new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def ensure_single_trailing_newline(self, content: str) -> str:
        """Ensure file ends with single newline (MD047)."""
        # Remove any trailing newlines
        cleaned_content = content.rstrip('\n')
        
        # Add single newline
        result = cleaned_content + '\n'
        
        if result != content:
            self.fixes_applied += 1
            self.log("Fixed trailing newline")
        
        return result

    def add_blank_lines_around_headings(self, content: str) -> str:
        """Add blank lines before and after headings (MD022)."""
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            # Check if current line is a heading
            if re.match(r'^\s*#{1,6}\s+', line):
                # Add blank line before heading (if not at start and previous line is not blank)
                if i > 0 and lines[i-1].strip() != '':
                    new_lines.append('')
                    self.fixes_applied += 1
                    self.log(f"Added blank line before heading: {line.strip()}")
                
                new_lines.append(line)
                
                # Add blank line after heading (if not at end and next line is not blank)
                if i < len(lines) - 1 and lines[i+1].strip() != '':
                    new_lines.append('')
                    self.fixes_applied += 1
                    self.log(f"Added blank line after heading: {line.strip()}")
            else:
                new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def add_blank_lines_around_fenced_code(self, content: str) -> str:
        """Add blank lines around fenced code blocks (MD031)."""
        lines = content.split('\n')
        new_lines = []
        in_code_block = False
        
        for i, line in enumerate(lines):
            # Check if current line is a fenced code block delimiter
            is_code_block_delimiter = re.match(r'^\s*```', line)
            
            if is_code_block_delimiter and not in_code_block:
                # Starting a code block
                in_code_block = True
                
                # Add blank line before code block (if not at start and previous line is not blank)
                if i > 0 and lines[i-1].strip() != '':
                    new_lines.append('')
                    self.fixes_applied += 1
                    self.log(f"Added blank line before code block: {line.strip()}")
                
                new_lines.append(line)
                
            elif is_code_block_delimiter and in_code_block:
                # Ending a code block
                in_code_block = False
                new_lines.append(line)
                
                # Add blank line after code block (if not at end and next line is not blank)
                if i < len(lines) - 1 and lines[i+1].strip() != '':
                    new_lines.append('')
                    self.fixes_applied += 1
                    self.log(f"Added blank line after code block: {line.strip()}")
                    
            else:
                # Regular line
                new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def add_blank_lines_around_lists(self, content: str) -> str:
        """Add blank lines around lists (MD032)."""
        lines = content.split('\n')
        new_lines = []
        in_list = False
        list_start_index = -1
        
        for i, line in enumerate(lines):
            # Check if current line is a list item
            is_list_item = (re.match(r'^\s*[-*+]\s+', line) or 
                          re.match(r'^\s*\d+\.\s+', line))
            
            if is_list_item and not in_list:
                # Starting a list
                in_list = True
                list_start_index = i
                
                # Add blank line before list (if not at start and previous line is not blank)
                if i > 0 and lines[i-1].strip() != '':
                    new_lines.append('')
                    self.fixes_applied += 1
                    self.log(f"Added blank line before list: {line.strip()}")
                
                new_lines.append(line)
                
            elif is_list_item and in_list:
                # Continuing a list
                new_lines.append(line)
                
            elif not is_list_item and in_list:
                # Ending a list
                in_list = False
                
                # Add blank line after list (if not at end and current line is not blank)
                if line.strip() != '':
                    new_lines.append('')
                    self.fixes_applied += 1
                    self.log(f"Added blank line after list ending at line {list_start_index}")
                
                new_lines.append(line)
                
            else:
                # Regular line
                new_lines.append(line)
        
        # Handle case where file ends with a list
        if in_list:
            # Add blank line after list if file ends with list
            new_lines.append('')
            self.fixes_applied += 1
            self.log(f"Added blank line after list at end of file")
        
        return '\n'.join(new_lines)
    
    def add_language_to_fenced_code(self, content: str) -> str:
        """Add language specification to fenced code blocks (MD040)."""
        def replace_code_block(match):
            code_block_line = match.group(1)
            
            # Check if language is already specified
            if '```' in code_block_line and len(code_block_line.strip()) > 3:
                return code_block_line
            
            # Get the code block content to detect language
            start_pos = match.end()
            end_pattern = re.compile(r'^\s*```\s*$', re.MULTILINE)
            end_match = end_pattern.search(content, start_pos)
            
            if end_match:
                code_content = content[start_pos:end_match.start()]
                detected_lang = self.detect_language_from_content(code_content)
                
                if detected_lang:
                    new_line = code_block_line.replace('```', f'```{detected_lang}')
                    self.fixes_applied += 1
                    self.log(f"Added language '{detected_lang}' to code block")
                    return new_line
            
            return code_block_line
        
        # Find all fenced code blocks without language specification
        pattern = re.compile(r'^(\s*```\s*)$', re.MULTILINE)
        return pattern.sub(replace_code_block, content)
    
    def clean_markdown_file(self, file_path: Path) -> bool:
        """Clean a single Markdown file."""
        try:
            self.log(f"Processing: {file_path}")
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Apply all fixes in the correct order
            cleaned_content = original_content
            cleaned_content = self.remove_trailing_spaces(cleaned_content)
            cleaned_content = self.fix_emphasis_spacing(cleaned_content)
            cleaned_content = self.convert_emphasis_to_headings(cleaned_content)
            cleaned_content = self.fix_ordered_list_prefixes(cleaned_content)
            cleaned_content = self.add_blank_lines_around_headings(cleaned_content)
            cleaned_content = self.add_blank_lines_around_fenced_code(cleaned_content)
            cleaned_content = self.add_blank_lines_around_lists(cleaned_content)
            cleaned_content = self.add_blank_lines_around_tables(cleaned_content)
            cleaned_content = self.add_language_to_fenced_code(cleaned_content)
            cleaned_content = self.remove_multiple_blank_lines(cleaned_content)
            cleaned_content = self.ensure_single_trailing_newline(cleaned_content)
            
            # Check if changes were made
            if cleaned_content != original_content:
                if not self.dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(cleaned_content)
                    self.log(f"[OK] Fixed {self.fixes_applied} issues in {file_path}")
                else:
                    self.log(f"[DRY] Would fix {self.fixes_applied} issues in {file_path} (dry run)")
                
                self.files_processed += 1
                return True
            else:
                self.log(f"[OK] No issues found in {file_path}")
                return False
                
        except Exception as e:
            self.log(f"[ERROR] Error processing {file_path}: {e}", "ERROR")
            return False
    
    def find_markdown_files(self, root_path: Path) -> List[Path]:
        """Find all Markdown files in the project, excluding certain directories."""
        markdown_files = []
        
        # Directories to exclude
        exclude_dirs = {
            '.git', '.venv', 'node_modules', '__pycache__', 
            '.pytest_cache', 'build', 'dist', '.docker'
        }
        
        for root, dirs, files in os.walk(root_path):
            # Remove excluded directories from search
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.md'):
                    markdown_files.append(Path(root) / file)
        
        return sorted(markdown_files)
    
    def cleanup_project(self, project_path: Path) -> Tuple[int, int]:
        """Clean up all Markdown files in the project."""
        self.log(f"Starting Markdown cleanup for project: {project_path}")
        
        markdown_files = self.find_markdown_files(project_path)
        self.log(f"Found {len(markdown_files)} Markdown files")
        
        fixed_files = 0
        for file_path in markdown_files:
            if self.clean_markdown_file(file_path):
                fixed_files += 1
        
        return fixed_files, len(markdown_files)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Clean up Markdown linting errors in Lucid project files"
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be fixed without making changes'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true', 
        help='Show detailed output'
    )
    parser.add_argument(
        '--path', '-p',
        type=str,
        default='.',
        help='Path to the project root (default: current directory)'
    )
    
    args = parser.parse_args()
    
    # Validate project path
    project_path = Path(args.path).resolve()
    if not project_path.exists():
        print(f"[ERROR] Project path does not exist: {project_path}")
        sys.exit(1)
    
    # Initialize cleaner
    cleaner = MarkdownCleaner(dry_run=args.dry_run, verbose=args.verbose)
    
    # Run cleanup
    try:
        fixed_files, total_files = cleaner.cleanup_project(project_path)
        
        print("\n" + "="*60)
        print("MARKDOWN CLEANUP SUMMARY")
        print("="*60)
        print(f"Total files processed: {total_files}")
        print(f"Files with fixes applied: {fixed_files}")
        print(f"Total fixes applied: {cleaner.fixes_applied}")
        
        if args.dry_run:
            print("\n[DRY RUN MODE] - No files were actually modified")
        else:
            print(f"\n[SUCCESS] Cleanup completed successfully!")
        
        print("\nFixed linting rules:")
        print("  - MD009: Removed trailing spaces")
        print("  - MD012: Removed multiple consecutive blank lines")
        print("  - MD022: Added blank lines around headings")
        print("  - MD029: Fixed ordered list item prefixes")
        print("  - MD031: Added blank lines around fenced code blocks")
        print("  - MD032: Added blank lines around lists")
        print("  - MD036: Converted emphasis to proper headings")
        print("  - MD037: Removed spaces inside emphasis markers")
        print("  - MD040: Added language specification to fenced code blocks")
        print("  - MD047: Ensured files end with single newline")
        print("  - MD058: Added blank lines around tables")
        
    except KeyboardInterrupt:
        print("\n[ERROR] Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
