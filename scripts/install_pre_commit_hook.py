#!/usr/bin/env python3
"""
Install pre-commit hook for StudyWise AI

This script installs a git pre-commit hook that runs validation before commits.
"""

import os
import stat
from pathlib import Path

def install_pre_commit_hook():
    """Install the pre-commit hook."""
    
    # Get the git hooks directory
    git_dir = Path(".git")
    if not git_dir.exists():
        print("❌ Not in a git repository")
        return False
    
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    
    pre_commit_path = hooks_dir / "pre-commit"
    
    # Pre-commit hook script
    hook_content = '''#!/bin/bash
# StudyWise AI Pre-Commit Hook
# Runs quick validation before allowing commits

echo "🔍 Running pre-commit validation..."

# Run quick validation
python scripts/pre_merge_validation.py --quick

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "✅ Pre-commit validation passed"
else
    echo "❌ Pre-commit validation failed"
    echo "💡 Run 'python scripts/pre_merge_validation.py' for detailed report"
    echo "💡 Use 'git commit --no-verify' to bypass (not recommended)"
fi

exit $exit_code
'''
    
    # Write the hook
    with open(pre_commit_path, 'w') as f:
        f.write(hook_content)
    
    # Make it executable
    current_permissions = os.stat(pre_commit_path)
    os.chmod(pre_commit_path, current_permissions.st_mode | stat.S_IEXEC)
    
    print(f"✅ Pre-commit hook installed at {pre_commit_path}")
    print("🔧 The hook will run validation before each commit")
    print("💡 Use 'git commit --no-verify' to bypass if needed")
    
    return True

if __name__ == "__main__":
    install_pre_commit_hook()