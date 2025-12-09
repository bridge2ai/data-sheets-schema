#!/usr/bin/env python3
"""
Unified D4D Prompt Loader

This module provides a unified interface for loading D4D prompts that works with
both the Aurelian agent approach and Claude Code deterministic approach.

Features:
- Load prompts from external version-controlled files
- Support multiple prompt sets (shared, aurelian, claude)
- Schema injection with configurable source (local/github)
- Schema caching for performance
- SHA-256 hashing for provenance
- Metadata generation for reproducibility

Usage:
    loader = D4DPromptLoader(
        prompts_dir=Path("src/download/prompts"),
        prompt_set="shared",
        schema_source="local"  # Default per user requirement
    )

    system_prompt, metadata = loader.load_system_prompt()
    user_prompt = loader.load_user_prompt(mode="content", **kwargs)

Author: Claude Code
Version: 1.0.0
Last Updated: 2025-12-03
"""

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import warnings

try:
    import requests
except ImportError:
    requests = None  # Optional dependency


class D4DPromptLoader:
    """
    Unified prompt loader for D4D metadata extraction.

    Supports loading prompts from different prompt sets and schemas from
    different sources with full provenance tracking.
    """

    def __init__(
        self,
        prompts_dir: Optional[Path] = None,
        prompt_set: str = "shared",
        schema_source: str = "local",
        schema_path: Optional[Path] = None,
        cache_schema: bool = True
    ):
        """
        Initialize D4D prompt loader.

        Args:
            prompts_dir: Directory containing prompt files (defaults to src/download/prompts)
            prompt_set: Which prompt set to use: "shared", "aurelian", or "claude"
            schema_source: Where to load schema from: "local", "github", or custom path
            schema_path: Custom path to schema file (overrides default)
            cache_schema: Whether to cache schema after first load
        """
        # Set prompts directory
        if prompts_dir is None:
            # Auto-detect based on this file's location
            this_file = Path(__file__).resolve()
            self.prompts_dir = this_file.parent / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)

        if not self.prompts_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {self.prompts_dir}")

        # Configure prompt set
        self.prompt_set = prompt_set
        self.prompt_set_dir = self._get_prompt_set_dir()

        # Configure schema source
        self.schema_source = schema_source
        self.schema_path = schema_path
        self.cache_schema = cache_schema

        # Cache
        self._schema_content: Optional[str] = None
        self._schema_hash: Optional[str] = None
        self._prompt_metadata: dict[str, Any] = {}

    def _get_prompt_set_dir(self) -> Path:
        """Get the directory for the selected prompt set."""
        if self.prompt_set == "shared":
            return self.prompts_dir / "shared"
        elif self.prompt_set == "aurelian":
            return self.prompts_dir / "aurelian"
        elif self.prompt_set == "claude":
            return self.prompts_dir / "claude"
        else:
            raise ValueError(
                f"Unknown prompt_set: {self.prompt_set}. "
                "Must be 'shared', 'aurelian', or 'claude'"
            )

    def _get_default_schema_path(self) -> Path:
        """Get default local schema path."""
        # Navigate up from prompts dir to project root
        project_root = self.prompts_dir.parent.parent.parent
        schema_path = project_root / "src" / "data_sheets_schema" / "schema" / "data_sheets_schema_all.yaml"

        if not schema_path.exists():
            # Try alternative path structure
            schema_path = project_root / "src" / "data_sheets_schema" / "schema" / "data_sheets_schema.yaml"

        return schema_path

    def _load_prompt_file(self, filename: str) -> tuple[str, str]:
        """
        Load prompt from file and calculate its hash.

        Strips YAML frontmatter (between ---) if present.

        Args:
            filename: Name of prompt file to load

        Returns:
            Tuple of (prompt_content, sha256_hash)
        """
        filepath = self.prompt_set_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Prompt file not found: {filepath}")

        content = filepath.read_text(encoding='utf-8')

        # Remove YAML frontmatter (between --- delimiters) if present
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2].strip()

        # Calculate hash of the file
        file_hash = self._calculate_file_hash(filepath)

        return content, file_hash

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _calculate_string_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of a string."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _load_schema_local(self, path: Path) -> tuple[str, str]:
        """
        Load schema from local file.

        Returns:
            Tuple of (schema_content, sha256_hash)
        """
        if not path.exists():
            raise FileNotFoundError(f"Schema file not found: {path}")

        content = path.read_text(encoding='utf-8')
        file_hash = self._calculate_file_hash(path)

        return content, file_hash

    def _load_schema_github(self, url: Optional[str] = None) -> tuple[str, str]:
        """
        Load schema from GitHub.

        Args:
            url: GitHub raw URL (uses default if not provided)

        Returns:
            Tuple of (schema_content, sha256_hash)
        """
        if requests is None:
            raise ImportError(
                "requests library is required for GitHub schema loading. "
                "Install with: pip install requests"
            )

        if url is None:
            # Default GitHub URL
            url = (
                "https://raw.githubusercontent.com/bridge2ai/data-sheets-schema/"
                "main/src/data_sheets_schema/schema/data_sheets_schema.yaml"
            )

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            content = response.text

            # Calculate hash of content
            content_hash = self._calculate_string_hash(content)

            return content, content_hash
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to load schema from GitHub: {e}") from e

    def get_schema(self) -> str:
        """
        Get schema content (with caching).

        Returns:
            Schema content as string
        """
        # Return cached if available
        if self._schema_content is not None and self.cache_schema:
            return self._schema_content

        # Load schema based on source
        if self.schema_source == "local":
            schema_path = self.schema_path or self._get_default_schema_path()
            content, file_hash = self._load_schema_local(schema_path)
            self._schema_hash = file_hash
        elif self.schema_source == "github":
            content, content_hash = self._load_schema_github()
            self._schema_hash = content_hash
        else:
            # Treat as custom file path
            custom_path = Path(self.schema_source)
            if not custom_path.is_file():
                raise FileNotFoundError(
                    f"Custom schema_source '{self.schema_source}' does not correspond to a valid file path. "
                    f"Please check the path and try again."
                )
            content, custom_file_hash = self._load_schema_local(custom_path)
            self._schema_hash = custom_file_hash

        # Cache if enabled
        if self.cache_schema:
            self._schema_content = content

        return content

    def load_system_prompt(self) -> tuple[str, dict[str, Any]]:
        """
        Load system prompt with schema injected.

        Returns:
            Tuple of (formatted_prompt, metadata_dict)
        """
        # Load system prompt template
        template, template_hash = self._load_prompt_file("d4d_system_prompt.txt")

        # Get schema
        schema = self.get_schema()

        # Format template with schema
        try:
            formatted_prompt = template.format(schema=schema)
        except KeyError as e:
            raise ValueError(
                f"Prompt template missing required placeholder: {e}. "
                "Expected {schema} placeholder."
            ) from e

        # Build metadata
        metadata = {
            "prompt_set": self.prompt_set,
            "prompt_file": "d4d_system_prompt.txt",
            "prompt_hash": template_hash,
            "schema_source": self.schema_source,
            "schema_hash": self._schema_hash,
            "loaded_at": datetime.now(timezone.utc).isoformat()
        }

        # Store for get_metadata()
        self._prompt_metadata["system_prompt"] = metadata

        return formatted_prompt, metadata

    def load_user_prompt(
        self,
        mode: str = "content",
        **kwargs
    ) -> str:
        """
        Load and format user prompt.

        Args:
            mode: "content" or "url"
            **kwargs: Template variables to inject
                For content mode: project_name, input_filename, content
                For url mode: project_name, urls

        Returns:
            Formatted user prompt
        """
        # Select appropriate template file
        if mode == "content":
            filename = "d4d_user_prompt_content_mode.txt"
        elif mode == "url":
            filename = "d4d_user_prompt_url_mode.txt"
        else:
            raise ValueError(f"Unknown mode: {mode}. Must be 'content' or 'url'")

        # Load template
        template, template_hash = self._load_prompt_file(filename)

        # Format with provided variables
        try:
            formatted_prompt = template.format(**kwargs)
        except KeyError as e:
            raise ValueError(
                f"Missing required template variable: {e}. "
                f"Mode '{mode}' requires: {self._get_required_variables(mode)}"
            ) from e

        # Build metadata
        metadata = {
            "prompt_set": self.prompt_set,
            "prompt_file": filename,
            "prompt_hash": template_hash,
            "mode": mode,
            "template_variables": list(kwargs.keys()),
            "loaded_at": datetime.now(timezone.utc).isoformat()
        }

        # Store for get_metadata()
        self._prompt_metadata["user_prompt"] = metadata

        return formatted_prompt

    def _get_required_variables(self, mode: str) -> list[str]:
        """Get list of required template variables for a mode."""
        if mode == "content":
            return ["project_name", "input_filename", "content"]
        elif mode == "url":
            return ["project_name", "urls"]
        else:
            return []

    def get_metadata(self) -> dict[str, Any]:
        """
        Get complete provenance metadata for all loaded prompts.

        Returns:
            Dictionary with full metadata including git commit, environment, etc.
        """
        metadata = {
            "prompt_loader_version": "1.0.0",
            "prompt_set": self.prompt_set,
            "prompt_set_dir": str(self.prompt_set_dir),
            "schema_source": self.schema_source,
            "schema_hash": self._schema_hash,
            "prompts": self._prompt_metadata.copy(),
            "git_commit": self._get_git_commit(),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        return metadata

    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
                cwd=self.prompts_dir
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return None


# Convenience functions for backward compatibility

def load_prompt_file(prompts_dir: Path, filename: str) -> tuple[str, str]:
    """
    Legacy function for loading prompt files (backward compatibility).

    This matches the signature used in process_concatenated_d4d_claude.py.

    Args:
        prompts_dir: Directory containing prompt files
        filename: Name of prompt file

    Returns:
        Tuple of (prompt_content, sha256_hash)
    """
    warnings.warn(
        "load_prompt_file() is deprecated. Use D4DPromptLoader instead.",
        DeprecationWarning,
        stacklevel=2
    )

    filepath = prompts_dir / filename
    content = filepath.read_text(encoding='utf-8')

    # Remove YAML header if present
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            content = parts[2].strip()

    # Calculate hash
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    file_hash = sha256.hexdigest()

    return content, file_hash


def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate SHA-256 hash of a file (backward compatibility).

    Args:
        file_path: Path to file

    Returns:
        SHA-256 hash as hex string
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()
