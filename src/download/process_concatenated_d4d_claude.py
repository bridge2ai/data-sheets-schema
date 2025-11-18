#!/usr/bin/env python3
"""
Deterministic Claude-based D4D extraction from concatenated documents with metadata generation.

This script processes concatenated documents (multiple D4D YAMLs or documentation files merged together)
and generates comprehensive D4D YAML files using Claude 3.5 Sonnet with deterministic settings.

Features:
- Temperature=0.0 for reproducible outputs
- Prompts loaded from external version-controlled files
- Local schema file (version-controlled)
- Comprehensive metadata YAML generation
- SHA-256 hashing of inputs, prompts, and schema
- Git commit tracking for provenance

Usage:
    python process_concatenated_d4d_claude.py -i input.txt -o output_d4d.yaml
    python process_concatenated_d4d_claude.py -i data/preprocessed/concatenated/AI_READI_concatenated.txt

Author: Claude Code
Version: 1.0.0
Last Updated: 2025-11-15
"""

import argparse
import asyncio
import hashlib
import os
import platform
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from aurelian.agents.d4d.d4d_config import D4DConfig
except ImportError:
    # Fallback for different import structures
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "aurelian" / "src"))
    from aurelian.agents.d4d.d4d_config import D4DConfig


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_git_commit() -> Optional[str]:
    """Get current git commit hash."""
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
    content = filepath.read_text(encoding='utf-8')

    # Remove YAML header (between ---) if present
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            content = parts[2].strip()

    # Calculate hash
    file_hash = calculate_file_hash(filepath)

    return content, file_hash


class DeterministicConcatenatedD4DProcessor:
    """
    Deterministic processor for extracting D4D metadata from concatenated documents using Claude.

    Ensures reproducibility through:
    - Temperature=0.0
    - Pinned model version
    - Local schema file
    - External prompt files with hash tracking
    - Comprehensive metadata generation
    """

    def __init__(self, model: str = "anthropic:claude-sonnet-4-5-20250929"):
        """
        Initialize processor with deterministic settings.

        Args:
            model: Model identifier (default: Claude Sonnet 4.5 date-pinned)
        """
        self.model = model
        self.project_root = Path(__file__).parent.parent.parent
        self.prompts_dir = self.project_root / "src" / "download" / "prompts"
        self.schema_path = self.project_root / "src" / "data_sheets_schema" / "schema" / "data_sheets_schema_all.yaml"

        # Load prompts from external files
        print("📂 Loading prompts from external files...")
        self.system_prompt_template, self.system_prompt_hash = load_prompt_file(
            self.prompts_dir, "d4d_concatenated_system_prompt.txt"
        )
        self.user_prompt_template, self.user_prompt_hash = load_prompt_file(
            self.prompts_dir, "d4d_concatenated_user_prompt.txt"
        )

        # Load schema
        print("📋 Loading local schema file...")
        self.schema_content = self.schema_path.read_text(encoding='utf-8')
        self.schema_hash = calculate_file_hash(self.schema_path)

        # Create system prompt with schema
        self.system_prompt = self.system_prompt_template.format(schema=self.schema_content)

        # Initialize D4D agent with deterministic settings
        print(f"🤖 Initializing Claude agent with temperature=0.0...")
        self.d4d_agent = Agent(
            model=self.model,
            deps_type=D4DConfig,
            system_prompt=self.system_prompt,
            model_settings={
                "temperature": 0.0,  # Maximum determinism
                "max_tokens": 16000,
            },
            defer_model_check=True,
        )

    def read_concatenated_file(self, file_path: Path) -> str:
        """
        Read concatenated document with encoding fallbacks.

        Args:
            file_path: Path to concatenated file

        Returns:
            File content as string
        """
        encodings = ['utf-8', 'utf-8-sig', 'latin-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Could not decode file {file_path} with any encoding")

    def generate_metadata(
        self,
        input_file: Path,
        output_file: Path,
        project_name: Optional[str],
        processing_time: float,
        input_hash: str,
        extraction_id: str
    ) -> dict:
        """
        Generate comprehensive metadata for D4D extraction.

        Args:
            input_file: Input concatenated file
            output_file: Output D4D YAML file
            project_name: Project name
            processing_time: Time taken to process
            input_hash: SHA-256 hash of input file
            extraction_id: Unique extraction ID

        Returns:
            Metadata dictionary
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        git_commit = get_git_commit()

        # Count source files if table of contents is present
        try:
            content = self.read_concatenated_file(input_file)
            source_files_count = content.count("File:") if "File:" in content else None
        except Exception:
            source_files_count = None

        metadata = {
            "extraction_metadata": {
                "timestamp": timestamp,
                "extraction_id": extraction_id,
                "extraction_type": "concatenated_claude_code",
                "processing_time_seconds": round(processing_time, 2)
            },
            "input_document": {
                "filename": input_file.name,
                "relative_path": str(input_file.relative_to(self.project_root)),
                "format": input_file.suffix.lstrip('.') or "txt",
                "size_bytes": input_file.stat().st_size,
                "sha256_hash": input_hash,
                "project": project_name or "unknown",
            },
            "output_document": {
                "filename": output_file.name,
                "relative_path": str(output_file.relative_to(self.project_root)),
                "format": "yaml"
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
                "implementation": "claude_code",
                "wrapper": "process_concatenated_d4d_claude.py",
                "wrapper_version": "1.0.0"
            },
            "llm_model": {
                "provider": "anthropic",
                "model_name": self.model,
                "model_version": "claude-sonnet-4-5-20250929",
                "temperature": 0.0,
                "max_tokens": 16000
            },
            "prompts": {
                "system_prompt_file": "prompts/d4d_concatenated_system_prompt.txt",
                "system_prompt_hash": self.system_prompt_hash,
                "user_prompt_file": "prompts/d4d_concatenated_user_prompt.txt",
                "user_prompt_hash": self.user_prompt_hash
            },
            "processing_environment": {
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "processor_architecture": platform.machine()
            },
            "reproducibility": {
                "command": f"make extract-d4d-concat-claude PROJECT={project_name or 'PROJECT'}",
                "environment_variables": {
                    "ANTHROPIC_API_KEY": "required"
                },
                "random_seed": None,
                "deterministic_settings": True
            },
            "provenance": {
                "extraction_performed_by": "process_concatenated_d4d_claude",
                "extraction_requested_at": timestamp,
                "git_commit": git_commit,
                "notes": "Deterministic D4D extraction from concatenated documents using Claude Sonnet 4.5 with temperature=0.0"
            }
        }

        # Add source file count if available
        if source_files_count is not None:
            metadata["input_document"]["source_files_count"] = source_files_count

        return metadata

    def save_metadata(self, metadata: dict, output_file: Path) -> None:
        """
        Save metadata to YAML file.

        Args:
            metadata: Metadata dictionary
            output_file: Path to save metadata (will have _metadata.yaml suffix)
        """
        metadata_file = output_file.parent / f"{output_file.stem}_metadata.yaml"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        print(f"💾 Metadata saved: {metadata_file}")

    def add_yaml_header(self, yaml_content: str, project_name: Optional[str], metadata_file: str) -> str:
        """
        Add header comments to D4D YAML.

        Args:
            yaml_content: Original YAML content
            project_name: Project name
            metadata_file: Metadata filename

        Returns:
            YAML with header comments
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        header = f"""# D4D extracted from concatenated documents
# Project: {project_name or 'Unknown'}
# Model: Claude Sonnet 4.5 (temperature=0.0)
# Schema: data_sheets_schema_all.yaml
# Generated: {timestamp}
# Metadata: See {metadata_file}

"""
        return header + yaml_content

    async def process_concatenated_file(
        self,
        input_file: Path,
        output_file: Optional[Path] = None,
        project_name: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Process a concatenated file with Claude D4D agent.

        Args:
            input_file: Path to concatenated input file
            output_file: Path to output D4D YAML file (default: {input_stem}_d4d.yaml)
            project_name: Optional project/column name for context

        Returns:
            Tuple of (success, message)
        """
        try:
            print(f"\n{'='*80}")
            print(f"📄 Processing: {input_file}")
            print(f"{'='*80}\n")

            start_time = time.time()

            # Read concatenated content
            content = self.read_concatenated_file(input_file)

            if len(content) < 100:  # Skip very short files
                return False, "Content too short"

            # Calculate input hash
            input_hash = calculate_file_hash(input_file)
            print(f"🔐 Input file SHA-256: {input_hash}")

            # Determine output file
            if output_file is None:
                output_file = input_file.parent / f"{input_file.stem.replace('_concatenated', '')}_d4d.yaml"

            # Generate unique extraction ID
            extraction_id = str(uuid.uuid4())[:12]

            # Prepare user prompt
            user_prompt = self.user_prompt_template.format(
                project_name=project_name or "Unknown",
                input_filename=input_file.name,
                content=content
            )

            # Configure D4D agent
            config = D4DConfig()

            print(f"🤖 Running Claude with temperature=0.0...")
            print(f"📊 Input size: {len(content):,} characters\n")

            # Run agent
            result = await self.d4d_agent.run(user_prompt, deps=config)

            processing_time = time.time() - start_time

            # Extract YAML from response
            response_text = result.data

            # Clean up response - remove markdown code blocks if present
            if "```yaml" in response_text:
                yaml_content = response_text.split("```yaml")[1].split("```")[0].strip()
            elif "```" in response_text:
                yaml_content = response_text.split("```")[1].split("```")[0].strip()
            else:
                yaml_content = response_text.strip()

            # Validate YAML syntax
            try:
                yaml.safe_load(yaml_content)
            except yaml.YAMLError as e:
                print(f"❌ YAML validation error: {e}")
                return False, f"Invalid YAML: {e}"

            # Generate metadata
            metadata = self.generate_metadata(
                input_file=input_file,
                output_file=output_file,
                project_name=project_name,
                processing_time=processing_time,
                input_hash=input_hash,
                extraction_id=extraction_id
            )

            # Add YAML header
            yaml_with_header = self.add_yaml_header(
                yaml_content,
                project_name,
                f"{output_file.stem}_metadata.yaml"
            )

            # Save D4D YAML
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(yaml_with_header)

            # Save metadata
            self.save_metadata(metadata, output_file)

            print(f"\n✅ Success!")
            print(f"   Output: {output_file}")
            print(f"   Size: {len(yaml_content):,} characters")
            print(f"   Processing time: {processing_time:.1f}s")
            print(f"   Extraction ID: {extraction_id}\n")

            return True, "Success"

        except Exception as e:
            print(f"\n❌ Error processing {input_file}: {e}\n")
            import traceback
            traceback.print_exc()
            return False, str(e)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Deterministic Claude-based D4D extraction from concatenated documents"
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        required=True,
        help="Input concatenated file path"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output D4D YAML file path (default: {input_stem}_d4d.yaml)"
    )
    parser.add_argument(
        "-p", "--project",
        type=str,
        help="Project name (AI_READI, CHORUS, CM4AI, VOICE)"
    )
    parser.add_argument(
        "-m", "--model",
        type=str,
        default="anthropic:claude-sonnet-4-5-20250929",
        help="Model to use (default: claude-sonnet-4-5-20250929)"
    )

    args = parser.parse_args()

    # Initialize processor
    processor = DeterministicConcatenatedD4DProcessor(model=args.model)

    # Process file
    success, message = await processor.process_concatenated_file(
        input_file=args.input,
        output_file=args.output,
        project_name=args.project
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
