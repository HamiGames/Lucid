#!/usr/bin/env python3
"""
Dockerfile Copy Path Fixer

This script fixes Dockerfile COPY commands in the final stage to use /build/ as source
for distroless containers. It processes one Dockerfile at a time.

Pattern for final stage COPY commands:
    INCORRECT: COPY --from=builder --chown=user /usr/lib /app/lib
    CORRECT:   COPY --from=builder --chown=user /build/usr/lib /app/lib

Note: This script ONLY fixes final stage COPY commands. Builder stage COPY commands
should already be correctly implemented using ./<dir>/ patterns.

Usage:
    python scripts/build/distroless/fix_dockerfile_copy_paths.py <path/to/Dockerfile>
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional

# Local directories that should use /build/ pattern
LOCAL_DIRS = [
    '/usr',
    '/run',
    '/etc',
    '/var',
    '/bin',
    '/local',
    '/lib',
    '/opt',
    '/sbin',
    '/tmp'
]

# Regex patterns
FROM_PATTERN = re.compile(r'^\s*FROM\s+--platform=\$\w+\s+\S+(?:\s+AS\s+(\w+))?', re.IGNORECASE)
WORKDIR_PATTERN = re.compile(r'^\s*WORKDIR\s+(\S+)')
USER_PATTERN = re.compile(r'^\s*USER\s+(\S+)')
COPY_PATTERN = re.compile(
    r'^\s*COPY\s+(?:--from=(\S+)\s+)?(?:(--chown=\S+)\s+)?(\S+)\s+(\S+)',
    re.IGNORECASE
)


class DockerfileFixer:
    """Main class to fix Dockerfile COPY commands."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.lines: List[str] = []
        self.modifications = []
        self.load()

    def load(self):
        """Load and parse Dockerfile."""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            self.lines = f.readlines()

    def get_final_stage_start(self) -> Optional[int]:
        """Find the start of the final stage (last FROM with no AS name)."""
        final_stage_idx = None
        for i, line in enumerate(self.lines):
            from_match = FROM_PATTERN.match(line)
            if from_match:
                final_stage_idx = i
        return final_stage_idx

    def get_builder_name(self) -> Optional[str]:
        """Get the first builder stage name."""
        for line in self.lines:
            from_match = FROM_PATTERN.match(line)
            if from_match and from_match.group(1):
                return from_match.group(1)
        return None

    def get_final_user(self) -> Optional[str]:
        """Get the USER directive in final stage."""
        final_stage_start = self.get_final_stage_start()
        if final_stage_start is None:
            return None
        
        for i in range(final_stage_start, len(self.lines)):
            user_match = USER_PATTERN.match(self.lines[i])
            if user_match:
                user_spec = user_match.group(1)
                if ':' in user_spec:
                    user = user_spec.split(':', 1)[0]
                    group = user_spec.split(':', 1)[1]
                else:
                    user = user_spec
                    group = user_spec
                return f"{user}:{group}"
        return None

    def find_copies_to_fix(self) -> List[Tuple[int, dict]]:
        """Find final stage COPY commands that need fixing."""
        final_stage_start = self.get_final_stage_start()
        if final_stage_start is None:
            return []
        
        builder_name = self.get_builder_name()
        copies_to_fix = []
        
        for i in range(final_stage_start, len(self.lines)):
            copy_match = COPY_PATTERN.match(self.lines[i])
            if copy_match:
                from_stage = copy_match.group(1)
                chown = copy_match.group(2)
                source = copy_match.group(3)
                dest = copy_match.group(4)
                
                # Only fix COPY commands that:
                # 1. Have --from=<builder> (pointing to builder stage)
                # 2. Source is a local directory (starts with /usr, /etc, etc.)
                # 3. Source does NOT start with /build/
                if (from_stage and builder_name and 
                    source.startswith(tuple(LOCAL_DIRS)) and 
                    not source.startswith('/build/')):
                    
                    copies_to_fix.append((i, {
                        'from_stage': from_stage,
                        'chown': chown,
                        'source': source,
                        'dest': dest,
                        'original': self.lines[i]
                    }))
        
        return copies_to_fix

    def fix_copy_command(self, copy_info: dict, builder_name: str, user: str) -> str:
        """Generate fixed COPY command."""
        source = copy_info['source']
        dest = copy_info['dest']
        chown = copy_info['chown']
        from_stage = copy_info['from_stage']
        
        # Determine the /build/ source path
        build_source = f"/build{source}"
        
        # Use existing chown or user from stage
        if chown:
            final_chown = chown
        else:
            final_chown = f"--chown={user}"
        
        # Generate fixed COPY command
        return f"COPY {from_stage} {final_chown} {build_source} {dest}\n"

    def apply_fixes(self, builder_name: str, user: str, copies_to_fix: List[Tuple[int, dict]]) -> bool:
        """Apply fixes to Dockerfile."""
        if not copies_to_fix:
            return False
        
        # Fix in reverse order to maintain line numbers
        for line_num, copy_info in reversed(copies_to_fix):
            fixed = self.fix_copy_command(copy_info, builder_name, user)
            self.lines[line_num] = fixed
            self.modifications.append(f"Line {line_num + 1}: {copy_info['source']} -> {copy_info['dest']}")
        
        return True

    def save(self):
        """Save modified Dockerfile."""
        with open(self.filepath, 'w', encoding='utf-8') as f:
            f.writelines(self.lines)

    def report(self):
        """Print a report of the modifications."""
        if not self.modifications:
            print("No modifications made.")
        else:
            print(f"\nModified {self.filepath}:")
            for mod in self.modifications:
                print(f"  - {mod}")


def process_dockerfile(filepath: Path, dry_run: bool = False) -> bool:
    """Process a single Dockerfile."""
    print(f"\n{'='*60}")
    print(f"Processing: {filepath}")
    print(f"{'='*60}")
    
    fixer = DockerfileFixer(filepath)
    
    # Get builder name and final user
    builder_name = fixer.get_builder_name()
    final_user = fixer.get_final_user()
    
    if not builder_name:
        print("Error: No builder stage found (FROM ... AS <name>)")
        return False
    
    print(f"Builder stage: {builder_name}")
    print(f"Final stage USER: {final_user or 'not found'}")
    
    # Find COPY commands to fix
    copies_to_fix = fixer.find_copies_to_fix()
    
    if not copies_to_fix:
        print("\nNo COPY commands need fixing.")
        return True
    
    print(f"\nCOPY commands needing fix: {len(copies_to_fix)}")
    for line_num, copy_info in copies_to_fix:
        print(f"  - Line {line_num + 1}: {copy_info['source']} -> {copy_info['dest']}")
    
    # Apply fixes
    if not fixer.apply_fixes(builder_name, final_user or '65532:65532', copies_to_fix):
        return False
    
    if dry_run:
        print("\n[DRY RUN] Would make the following changes:")
        fixer.report()
        return True
    
    # Save changes
    fixer.save()
    print("\nOK Fixes applied successfully.")
    fixer.report()
    
    return True


def find_dockerfiles(base_dirs: List[Path]) -> List[Path]:
    """Find all Dockerfile.* and Dockerfile files in base directories."""
    dockerfiles = []
    
    for base_dir in base_dirs:
        if not base_dir.exists():
            continue
        
        for pattern in ['Dockerfile.*', 'Dockerfile']:
            dockerfiles.extend(base_dir.rglob(pattern))
    
    return sorted(dockerfiles)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Process a single Dockerfile:")
        print("    python scripts/build/distroless/fix_dockerfile_copy_paths.py <path/to/Dockerfile>")
        print("\n  Process all Dockerfiles in infrastructure directories:")
        print("    python scripts/build/distroless/fix_dockerfile_copy_paths.py --all [--dry-run]")
        print("\n  Process all Dockerfiles in specific directories:")
        print("    python scripts/build/distroless/fix_dockerfile_copy_paths.py --dirs <dir1> <dir2> ... [--dry-run]")
        sys.exit(1)
    
    dry_run = '--dry-run' in sys.argv
    
    if sys.argv[1] == '--all':
        # Process all Dockerfiles in infrastructure/docker/ and infrastructure/containers/
        repo_root = Path.cwd()
        base_dirs = [
            repo_root / 'infrastructure' / 'docker',
            repo_root / 'infrastructure' / 'containers'
        ]
        dockerfiles = find_dockerfiles(base_dirs)
        
        if not dockerfiles:
            print("No Dockerfiles found.")
            sys.exit(0)
        
        print(f"Found {len(dockerfiles)} Dockerfiles to process.")
        
        success_count = 0
        for filepath in dockerfiles:
            if process_dockerfile(filepath, dry_run):
                success_count += 1
        
        print(f"\n{'='*60}")
        print(f"Summary: {success_count}/{len(dockerfiles)} Dockerfiles processed successfully")
        print(f"{'='*60}")
        
    elif sys.argv[1] == '--dirs':
        # Process Dockerfiles in specified directories
        dirs_arg_idx = sys.argv.index('--dirs') + 1
        base_dirs = [Path(d) for d in sys.argv[dirs_arg_idx:] if not d.startswith('--')]
        
        dockerfiles = find_dockerfiles(base_dirs)
        
        if not dockerfiles:
            print("No Dockerfiles found in specified directories.")
            sys.exit(0)
        
        print(f"Found {len(dockerfiles)} Dockerfiles to process.")
        
        success_count = 0
        for filepath in dockerfiles:
            if process_dockerfile(filepath, dry_run):
                success_count += 1
        
        print(f"\n{'='*60}")
        print(f"Summary: {success_count}/{len(dockerfiles)} Dockerfiles processed successfully")
        print(f"{'='*60}")
        
    else:
        # Process a single Dockerfile
        filepath = Path(sys.argv[1])
        if not filepath.exists():
            print(f"Error: File not found: {filepath}")
            sys.exit(1)
        
        success = process_dockerfile(filepath, dry_run)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
