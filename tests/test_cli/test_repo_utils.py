#!/usr/bin/env python3
"""
Unit tests for CLI repo utility helpers.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import click

from data_sheets_schema.cli import _repo_utils


class TestRepoUtils(unittest.TestCase):
    """Test repository helper utilities."""

    def test_get_repo_root_finds_current_repository(self):
        repo_root = _repo_utils.get_repo_root()
        self.assertTrue((repo_root / "pyproject.toml").exists())

    def test_setup_repo_imports_adds_repo_and_claude_paths(self):
        repo_root = Path("/tmp/fake_repo")
        claude_scripts = repo_root / ".claude" / "agents" / "scripts"

        with patch("data_sheets_schema.cli._repo_utils.get_repo_root", return_value=repo_root), \
             patch.object(sys, "path", ["existing"]):
            with patch.object(Path, "exists", autospec=True) as exists_mock:
                exists_mock.side_effect = lambda path: path == claude_scripts
                _repo_utils.setup_repo_imports()
                updated_path = list(sys.path)

        self.assertEqual(updated_path[0], str(claude_scripts))
        self.assertEqual(updated_path[1], str(repo_root))

    def test_require_repo_context_wraps_runtime_error_in_click_exception(self):
        with patch("data_sheets_schema.cli._repo_utils.get_repo_root", side_effect=RuntimeError("not in repo")):
            with self.assertRaises(click.ClickException) as exc:
                _repo_utils.require_repo_context("d4d test")

        self.assertIn("d4d test requires a repository checkout", str(exc.exception))
        self.assertIn("not in repo", str(exc.exception))


if __name__ == "__main__":
    unittest.main()
