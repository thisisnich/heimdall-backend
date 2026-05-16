"""
Brain Git Integration — Automatic git operations for brain vault.

Provides git sync for the brain vault:
  - Auto-commit after sync
  - Push to remote repository
  - Branch management
  - Conflict resolution
"""

import subprocess
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

BRAIN_VAULT_ROOT = Path("/opt/heimdall/brain-vault")


def _run_git_command(args: list, cwd: Path = BRAIN_VAULT_ROOT) -> subprocess.CompletedProcess:
    """Run a git command in the brain vault directory."""
    try:
        result = subprocess.run(
            ['git'] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e.stderr}")
        raise


def init_git_repo(remote_url: str = None) -> dict:
    """Initialize git repository in the brain vault."""
    if not BRAIN_VAULT_ROOT.exists():
        BRAIN_VAULT_ROOT.mkdir(parents=True, exist_ok=True)
    
    # Check if already initialized
    git_dir = BRAIN_VAULT_ROOT / ".git"
    if git_dir.exists():
        return {"status": "already_initialized", "path": str(BRAIN_VAULT_ROOT)}
    
    # Initialize
    _run_git_command(['init'])
    
    # Create .gitignore
    gitignore = BRAIN_VAULT_ROOT / ".gitignore"
    gitignore.write_text("""# Obsidian
.obsidian/
.trash/

# Python
__pycache__/
*.pyc
.pytest_cache/

# OS
.DS_Store
Thumbs.db
""")
    
    # Initial commit
    _run_git_command(['add', '.'])
    _run_git_command(['commit', '-m', 'Initial commit: Heimdall Brain Vault'])
    
    # Add remote if provided
    if remote_url:
        _run_git_command(['remote', 'add', 'origin', remote_url])
    
    logger.info(f"Git repository initialized at {BRAIN_VAULT_ROOT}")
    
    return {
        "status": "initialized",
        "path": str(BRAIN_VAULT_ROOT),
        "remote_url": remote_url
    }


def commit_changes(message: str = None) -> dict:
    """Commit changes to the brain vault."""
    if not (BRAIN_VAULT_ROOT / ".git").exists():
        return {"status": "error", "error": "Not a git repository"}
    
    # Stage all changes
    _run_git_command(['add', '.'])
    
    # Check if there are changes to commit
    result = _run_git_command(['status', '--porcelain'])
    if not result.stdout.strip():
        return {"status": "no_changes", "message": "No changes to commit"}
    
    # Commit with message
    if not message:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        message = f"Brain vault sync: {timestamp}"
    
    _run_git_command(['commit', '-m', message])
    
    # Get commit hash
    result = _run_git_command(['rev-parse', 'HEAD'])
    commit_hash = result.stdout.strip()
    
    logger.info(f"Committed changes: {commit_hash}")
    
    return {
        "status": "committed",
        "commit_hash": commit_hash,
        "message": message
    }


def push_to_remote(branch: str = "main") -> dict:
    """Push changes to remote repository."""
    if not (BRAIN_VAULT_ROOT / ".git").exists():
        return {"status": "error", "error": "Not a git repository"}
    
    try:
        result = _run_git_command(['push', 'origin', branch])
        
        logger.info(f"Pushed to remote: {branch}")
        
        return {
            "status": "pushed",
            "branch": branch
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Push failed: {e.stderr}")
        return {
            "status": "error",
            "error": str(e.stderr)
        }


def pull_from_remote(branch: str = "main") -> dict:
    """Pull changes from remote repository."""
    if not (BRAIN_VAULT_ROOT / ".git").exists():
        return {"status": "error", "error": "Not a git repository"}
    
    try:
        result = _run_git_command(['pull', 'origin', branch])
        
        logger.info(f"Pulled from remote: {branch}")
        
        return {
            "status": "pulled",
            "branch": branch
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Pull failed: {e.stderr}")
        return {
            "status": "error",
            "error": str(e.stderr)
        }


def get_git_status() -> dict:
    """Get current git status."""
    if not (BRAIN_VAULT_ROOT / ".git").exists():
        return {"status": "error", "error": "Not a git repository"}
    
    # Get branch
    result = _run_git_command(['branch', '--show-current'])
    branch = result.stdout.strip()
    
    # Get status
    result = _run_git_command(['status', '--porcelain'])
    changes = result.stdout.strip().split('\n') if result.stdout.strip() else []
    
    # Get last commit
    result = _run_git_command(['log', '-1', '--format=%H %s'])
    last_commit = result.stdout.strip()
    
    return {
        "status": "ok",
        "branch": branch,
        "changes": changes,
        "change_count": len(changes),
        "last_commit": last_commit
    }


def sync_and_push(message: str = None, branch: str = "main") -> dict:
    """Commit changes and push to remote."""
    # Commit
    commit_result = commit_changes(message)
    
    if commit_result["status"] == "no_changes":
        return commit_result
    
    if commit_result["status"] == "error":
        return commit_result
    
    # Push
    push_result = push_to_remote(branch)
    
    return {
        "commit": commit_result,
        "push": push_result,
        "status": "synced" if push_result["status"] == "pushed" else "partial"
    }
