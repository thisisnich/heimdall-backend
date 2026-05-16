"""
Setup Heimdall Brain Vault with Git Integration.

This script initializes the brain vault directory structure,
sets up git repository, and configures remote for pushing.

Usage:
    python setup_brain_vault.py --remote https://github.com/user/heimdall-brain.git
"""

import argparse
import sys
from pathlib import Path

from atlas.core.brain_vault_writer import _ensure_vault, BRAIN_VAULT_ROOT
from atlas.core.brain_git import init_git_repo


def main():
    parser = argparse.ArgumentParser(description="Setup Heimdall Brain Vault with Git")
    parser.add_argument(
        "--remote",
        type=str,
        help="Git remote URL (e.g., https://github.com/user/heimdall-brain.git)"
    )
    parser.add_argument(
        "--vault-path",
        type=str,
        default=str(BRAIN_VAULT_ROOT),
        help=f"Vault path (default: {BRAIN_VAULT_ROOT})"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Heimdall Brain Vault Setup")
    print("=" * 60)
    print(f"Vault Path: {args.vault_path}")
    print(f"Remote URL: {args.remote or 'Not specified'}")
    print("=" * 60)
    
    # Ensure vault directory structure
    print("\n1. Creating vault directory structure...")
    _ensure_vault()
    print("   ✓ Vault structure created")
    
    # Initialize git repository
    print("\n2. Initializing git repository...")
    git_result = init_git_repo(args.remote)
    
    if git_result["status"] == "already_initialized":
        print("   ⚠ Git repository already exists")
    elif git_result["status"] == "initialized":
        print("   ✓ Git repository initialized")
        if args.remote:
            print(f"   ✓ Remote configured: {args.remote}")
    
    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    
    print("\nNext steps:")
    print("1. Open the vault in Obsidian:")
    print(f"   obsidian://open?vault={args.vault_path}")
    print(f"\n2. Sync brain to vault:")
    print("   curl -X POST http://localhost:8000/brain/vault/sync")
    print(f"\n3. Sync and push to git:")
    print("   curl -X POST 'http://localhost:8000/brain/vault/sync?push_to_git=true'")
    
    print("\nAPI Endpoints:")
    print("  POST /brain/vault/sync           - Sync brain to vault")
    print("  POST /brain/vault/sync/memories  - Sync memories only")
    print("  POST /brain/vault/sync/notes     - Sync notes only")
    print("  GET  /brain/vault/status         - Get vault status")
    print("  POST /brain/vault/git/init       - Initialize git")
    print("  POST /brain/vault/git/commit     - Commit changes")
    print("  POST /brain/vault/git/push       - Push to remote")
    print("  POST /brain/vault/git/sync       - Commit and push")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
