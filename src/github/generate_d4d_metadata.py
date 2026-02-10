#!/usr/bin/env python3
"""
Generate comprehensive metadata for D4D datasheets created by GitHub Assistant.

This script creates metadata YAML files that match the structure used by the
deterministic Claude Code agent (process_concatenated_d4d_claude.py), enabling
scientific comparison between methods.

Features:
- SHA-256 hashing of inputs, schema, and prompts
- Git commit tracking for provenance
- Comprehensive extraction metadata
- Compatible with batch extraction metadata structure
- Configuration-driven from d4d_assistant_deterministic_config.yaml

Usage:
    # Generate metadata for a D4D YAML file
    python src/github/generate_d4d_metadata.py \
        --d4d-file data/sheets_d4dassistant/mydataset_d4d.yaml \
        --input-sources url1 url2 url3 \
        --dataset-name mydataset

    # With file-based inputs
    python src/github/generate_d4d_metadata.py \
        --d4d-file data/sheets_d4dassistant/mydataset_d4d.yaml \
        --input-dir data/sheets_d4dassistant/inputs/mydataset \
        --dataset-name mydataset

Author: Claude Code
Version: 1.0.0
Last Updated: 2025-02-10
"""

import argparse
import hashlib
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import yaml


def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate SHA-256 hash of a file.

    Args:
        file_path: Path to file

    Returns:
        SHA-256 hash as hexadecimal string
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def calculate_string_hash(content: str) -> str:
    """
    Calculate SHA-256 hash of a string.

    Args:
        content: String content

    Returns:
        SHA-256 hash as hexadecimal string
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def calculate_url_hash(url: str) -> str:
    """
    Calculate SHA-256 hash of a URL.

    Args:
        url: URL string

    Returns:
        SHA-256 hash as hexadecimal string
    """
    return hashlib.sha256(url.encode('utf-8')).hexdigest()


def get_git_commit() -> Optional[str]:
    """
    Get current git commit hash.

    Returns:
        Commit hash or None if not in git repository
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


def load_config(config_path: Path) -> dict:
    """
    Load deterministic configuration.

    Args:
        config_path: Path to config YAML file

    Returns:
        Configuration dictionary
    """
    if not config_path.exists():
        print(f"Warning: Config file not found: {config_path}")
        return {}

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_prompt_file(prompts_dir: Path, filename: str) -> tuple[str, str]:
    """
    Load prompt from file and calculate its hash.

    Args:
        prompts_dir: Directory containing prompt files
        filename: Name of prompt file

    Returns:
        Tuple of (prompt_content, sha256_hash)
    """
    filepath = prompts_dir / filename
    if not filepath.exists():
        print(f"Warning: Prompt file not found: {filepath}")
        return "", "unknown"

    content = filepath.read_text(encoding='utf-8')

    # Remove YAML header (between ---) if present
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            content = parts[2].strip()

    # Calculate hash
    file_hash = calculate_file_hash(filepath)

    return content, file_hash


class D4DMetadataGenerator:
    """
    Generator for comprehensive D4D extraction metadata.

    Ensures compatibility with batch extraction metadata structure.
    """

    def __init__(self, project_root: Optional[Path] = None, config: Optional[dict] = None):
        """
        Initialize metadata generator.

        Args:
            project_root: Project root directory (default: auto-detect)
            config: Configuration dictionary (default: load from file)
        """
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.prompts_dir = self.project_root / "src" / "download" / "prompts"
        self.schema_path = self.project_root / "src" / "data_sheets_schema" / "schema" / "data_sheets_schema_all.yaml"
        self.config_path = self.project_root / ".github" / "workflows" / "d4d_assistant_deterministic_config.yaml"

        # Load configuration
        self.config = config or load_config(self.config_path)

        # Extract model settings
        model_config = self.config.get('model', {})
        self.model_name = model_config.get('name', 'claude-sonnet-4-5-20250929')
        self.temperature = model_config.get('temperature', 0.0)
        self.max_tokens = model_config.get('max_tokens', 16000)

        # Load prompts if config specifies them
        prompt_config = self.config.get('prompts', {})
        system_prompt_file = prompt_config.get('system_prompt_file', 'd4d_concatenated_system_prompt.txt')
        user_prompt_file = prompt_config.get('user_prompt_file', 'd4d_concatenated_user_prompt.txt')

        # Extract just filename if full path provided
        system_prompt_file = Path(system_prompt_file).name
        user_prompt_file = Path(user_prompt_file).name

        self.system_prompt_content, self.system_prompt_hash = load_prompt_file(
            self.prompts_dir, system_prompt_file
        )
        self.user_prompt_content, self.user_prompt_hash = load_prompt_file(
            self.prompts_dir, user_prompt_file
        )

        # Load schema
        if self.schema_path.exists():
            self.schema_hash = calculate_file_hash(self.schema_path)
        else:
            print(f"Warning: Schema file not found: {self.schema_path}")
            self.schema_hash = "unknown"

    def generate_metadata(
        self,
        d4d_file: Path,
        dataset_name: str,
        input_sources: Optional[List[str]] = None,
        input_dir: Optional[Path] = None,
        processing_time: Optional[float] = None,
        extraction_id: Optional[str] = None,
        issue_number: Optional[int] = None,
        pr_number: Optional[int] = None
    ) -> dict:
        """
        Generate comprehensive metadata for D4D extraction.

        Args:
            d4d_file: Path to output D4D YAML file
            dataset_name: Dataset name/identifier
            input_sources: List of input URLs (URL mode)
            input_dir: Directory containing input files (file mode)
            processing_time: Time taken to process (seconds)
            extraction_id: Unique extraction ID
            issue_number: GitHub issue number that triggered extraction
            pr_number: GitHub PR number created for extraction

        Returns:
            Metadata dictionary matching batch extraction structure
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        git_commit = get_git_commit()

        # Determine input mode and calculate hashes
        input_mode = "unknown"
        input_documents = []

        if input_dir and input_dir.exists():
            # File-based mode
            input_mode = "file"
            for file_path in sorted(input_dir.glob('*')):
                if file_path.is_file():
                    input_documents.append({
                        "filename": file_path.name,
                        "relative_path": str(file_path.relative_to(self.project_root)),
                        "format": file_path.suffix.lstrip('.') or "txt",
                        "size_bytes": file_path.stat().st_size,
                        "sha256_hash": calculate_file_hash(file_path)
                    })
        elif input_sources:
            # URL-based mode
            input_mode = "url"
            for url in input_sources:
                input_documents.append({
                    "url": url,
                    "sha256_hash": calculate_url_hash(url),
                    "format": "fetched"
                })

        # Build metadata structure matching process_concatenated_d4d_claude.py
        metadata = {
            "extraction_metadata": {
                "timestamp": timestamp,
                "extraction_id": extraction_id or "github-assistant",
                "extraction_type": "github_assistant_claude_code",
                "processing_time_seconds": round(processing_time, 2) if processing_time else None,
                "input_mode": input_mode,
                "github_context": {
                    "issue_number": issue_number,
                    "pr_number": pr_number,
                    "assistant_name": "d4dassistant"
                }
            },
            "input_documents": input_documents if input_documents else [{
                "format": "unknown",
                "note": "Input sources not tracked"
            }],
            "output_document": {
                "filename": d4d_file.name,
                "relative_path": str(d4d_file.relative_to(self.project_root)) if d4d_file.exists() else str(d4d_file),
                "format": "yaml",
                "dataset_name": dataset_name
            },
            "datasheets_schema": {
                "version": "1.0.0",
                "source": "local",
                "path": str(self.schema_path.relative_to(self.project_root)),
                "sha256_hash": self.schema_hash,
                "loaded_at": timestamp
            },
            "d4d_agent": {
                "version": "1.0.0",
                "implementation": "github_assistant",
                "wrapper": "dragon-ai-agent/run-claude-obo",
                "wrapper_version": "v1.0.2",
                "metadata_generator": "src/github/generate_d4d_metadata.py",
                "metadata_generator_version": "1.0.0"
            },
            "llm_model": {
                "provider": "anthropic",
                "model_name": self.model_name,
                "model_version": self.model_name,  # Date-pinned model
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            },
            "prompts": {
                "system_prompt_file": "src/download/prompts/d4d_concatenated_system_prompt.txt",
                "system_prompt_hash": self.system_prompt_hash,
                "user_prompt_file": "src/download/prompts/d4d_concatenated_user_prompt.txt",
                "user_prompt_hash": self.user_prompt_hash,
                "instructions_file": ".github/workflows/d4d_assistant_create.md"
            },
            "processing_environment": {
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "processor_architecture": platform.machine(),
                "github_actions": os.getenv('GITHUB_ACTIONS', 'false') == 'true'
            },
            "reproducibility": {
                "command": f"@d4dassistant create D4D datasheet for {dataset_name}",
                "environment_variables": {
                    "ANTHROPIC_API_KEY": "required"
                },
                "random_seed": None,
                "deterministic_settings": True,
                "config_file": str(self.config_path.relative_to(self.project_root))
            },
            "provenance": {
                "extraction_performed_by": "github_d4d_assistant",
                "extraction_requested_at": timestamp,
                "git_commit": git_commit,
                "notes": f"Deterministic D4D extraction by GitHub Assistant using Claude Sonnet 4.5 (temperature={self.temperature})"
            }
        }

        return metadata

    def save_metadata(self, metadata: dict, output_file: Path) -> Path:
        """
        Save metadata to YAML file.

        Args:
            metadata: Metadata dictionary
            output_file: Path to D4D YAML file (metadata will be saved alongside)

        Returns:
            Path to saved metadata file
        """
        metadata_file = output_file.parent / f"{output_file.stem}_metadata.yaml"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)

        with open(metadata_file, 'w', encoding='utf-8') as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        return metadata_file


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate comprehensive metadata for GitHub Assistant D4D extractions"
    )
    parser.add_argument(
        "--d4d-file",
        type=Path,
        required=True,
        help="Path to output D4D YAML file"
    )
    parser.add_argument(
        "--dataset-name",
        type=str,
        required=True,
        help="Dataset name/identifier"
    )
    parser.add_argument(
        "--input-sources",
        nargs="+",
        help="List of input URLs (URL mode)"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="Directory containing input files (file mode)"
    )
    parser.add_argument(
        "--processing-time",
        type=float,
        help="Processing time in seconds"
    )
    parser.add_argument(
        "--extraction-id",
        type=str,
        help="Unique extraction ID"
    )
    parser.add_argument(
        "--issue-number",
        type=int,
        help="GitHub issue number"
    )
    parser.add_argument(
        "--pr-number",
        type=int,
        help="GitHub PR number"
    )

    args = parser.parse_args()

    # Initialize generator
    generator = D4DMetadataGenerator()

    # Generate metadata
    print("📋 Generating D4D extraction metadata...")
    metadata = generator.generate_metadata(
        d4d_file=args.d4d_file,
        dataset_name=args.dataset_name,
        input_sources=args.input_sources,
        input_dir=args.input_dir,
        processing_time=args.processing_time,
        extraction_id=args.extraction_id,
        issue_number=args.issue_number,
        pr_number=args.pr_number
    )

    # Save metadata
    metadata_file = generator.save_metadata(metadata, args.d4d_file)
    print(f"✅ Metadata saved: {metadata_file}")

    # Print summary
    print("\n📊 Metadata Summary:")
    print(f"   Extraction type: {metadata['extraction_metadata']['extraction_type']}")
    print(f"   Input mode: {metadata['extraction_metadata']['input_mode']}")
    print(f"   Model: {metadata['llm_model']['model_name']}")
    print(f"   Temperature: {metadata['llm_model']['temperature']}")
    print(f"   Schema hash: {metadata['datasheets_schema']['sha256_hash'][:16]}...")
    print(f"   System prompt hash: {metadata['prompts']['system_prompt_hash'][:16]}...")
    print(f"   User prompt hash: {metadata['prompts']['user_prompt_hash'][:16]}...")
    if metadata['provenance']['git_commit']:
        print(f"   Git commit: {metadata['provenance']['git_commit'][:12]}")

    sys.exit(0)


if __name__ == "__main__":
    main()
