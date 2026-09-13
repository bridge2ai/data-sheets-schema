"""
Utility functions for repo-based CLI operations.

NOTE: The current CLI implementation relies on repository-local paths
(src/, .claude/) that are not included in the installed package.
This module provides helpers to detect and handle this gracefully.

TODO: Restructure code to be fully installable outside repo checkout.
"""

import sys
from pathlib import Path


def get_repo_root() -> Path:
    """
    Get repository root directory.

    Returns:
        Path to repository root

    Raises:
        RuntimeError: If not running in a repository checkout
    """
    # The same decision as `resources.resource_root` (#1501, #1588): the
    # working directory when it is a checkout of this project, else the
    # checkout the package is imported from — never an arbitrary ancestor,
    # so a wheel installed in a user's project venv does not adopt that
    # project as the root (#1577).
    from data_sheets_schema.resources import CHECKOUT_ROOT, cwd_checkout
    here = cwd_checkout()
    if here is not None:
        return here
    if CHECKOUT_ROOT is not None:
        return CHECKOUT_ROOT

    raise RuntimeError(
        "This command requires a repository checkout.\n"
        "The d4d CLI currently relies on repository-local code paths.\n"
        "Please run from within the data-sheets-schema repository."
    )


def setup_repo_imports():
    """
    Add repository paths to sys.path for importing repo-local modules.

    This is a temporary workaround until the code is properly packaged.

    Raises:
        RuntimeError: If not running in a repository checkout
    """
    repo_root = get_repo_root()

    # Add repo root to path (for src/ imports)
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Add .claude/agents/scripts for RO-Crate functionality
    claude_scripts = repo_root / ".claude" / "agents" / "scripts"
    if claude_scripts.exists() and str(claude_scripts) not in sys.path:
        sys.path.insert(0, str(claude_scripts))


def require_repo_context(command_name: str = "this command"):
    """
    Verify we're running in a repository context.

    Args:
        command_name: Name of the command for error messages

    Raises:
        click.ClickException: If not in repository context
    """
    try:
        get_repo_root()
    except RuntimeError as e:
        import click
        from data_sheets_schema.resources import ResourceRootError
        if isinstance(e, ResourceRootError):
            raise                            # already a click error, and the reason is the whole message (#1730)
        raise click.ClickException(
            f"{command_name} requires a repository checkout.\n"
            f"The d4d CLI currently relies on repository-local code.\n"
            f"Please run from within the data-sheets-schema repository.\n\n"
            f"Error: {e}"
        )
