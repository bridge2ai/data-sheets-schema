#!/usr/bin/env python3
"""
D4D Extraction Metadata Generator

Generates metadata records conforming to the d4d_extract_process.yaml LinkML schema.
Used by both the Claude API deterministic script and the D4D agent wrapper to emit
standardized provenance metadata for each extraction run.

Schema: src/schema_extract/d4d_extract_process.yaml
"""

import hashlib
import os
import platform
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    print("Error: pyyaml not installed. Install with: pip install pyyaml")
    sys.exit(1)


# Repository root (relative to this file)
REPO_ROOT = Path(__file__).parent.parent.parent


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def compute_content_sha256(content: str) -> str:
    """Compute SHA-256 hash of string content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def get_git_commit() -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def get_git_branch() -> str:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def generate_extraction_id() -> str:
    """Generate a unique extraction ID."""
    return str(uuid.uuid4())[:12]


class D4DExtractionMetadata:
    """
    Builder class for D4D extraction metadata conforming to d4d_extract_process.yaml schema.

    Usage:
        metadata = D4DExtractionMetadata()
        metadata.set_extraction_type("concatenated_claude_api")
        metadata.set_input_document(input_path, project_name)
        metadata.set_schema(schema_path)
        metadata.set_llm_model("anthropic", "claude-sonnet-4-5-20250929", temperature=0.0)
        metadata.set_prompts(prompts_dir, system_prompt_file, user_prompt_file)
        metadata.set_output(output_path, yaml_content)
        metadata.set_provenance("process_d4d_claude_API_temp0.py")

        # Save metadata
        metadata.save(metadata_output_path)
    """

    def __init__(self):
        self._extraction_id = generate_extraction_id()
        self._start_time = datetime.now()
        self._data: Dict[str, Any] = {
            "id": f"d4d-extraction-{self._extraction_id}",
            "description": None,
            "notes": [],
            "extraction_metadata": {
                "extraction_id": self._extraction_id,
                "extraction_type": None,
                "timestamp": self._start_time.isoformat(),
                "completed_at": None,
                "processing_time_seconds": None,
                "status": "in_progress"
            },
            "input_document": None,
            "datasheets_schema": None,
            "llm_model": None,
            "prompts": None,
            "output": None,
            "reproducibility": None,
            "provenance": None,
            "validation_results": None,
            "comparison": None
        }

    def set_description(self, description: str) -> "D4DExtractionMetadata":
        """Set extraction description."""
        self._data["description"] = description
        return self

    def add_note(self, note: str) -> "D4DExtractionMetadata":
        """Add a note to the extraction."""
        self._data["notes"].append(note)
        return self

    def set_extraction_type(self, extraction_type: str) -> "D4DExtractionMetadata":
        """
        Set the extraction type.

        Valid values:
        - individual_gpt5
        - individual_claude
        - concatenated_gpt5
        - concatenated_claude_api
        - concatenated_claude_assistant
        - manual_curation
        """
        self._data["extraction_metadata"]["extraction_type"] = extraction_type
        return self

    def set_input_document(
        self,
        file_path: Path,
        project: str,
        source_type: str = "single_file",
        source_files: Optional[List[Dict]] = None,
        encoding: str = "utf-8"
    ) -> "D4DExtractionMetadata":
        """
        Set input document information.

        Args:
            file_path: Path to the input file
            project: Project name (e.g., AI_READI, CHORUS, CM4AI, VOICE)
            source_type: single_file, concatenated, or url
            source_files: List of source file dicts if concatenated
            encoding: File encoding
        """
        file_path = Path(file_path)

        input_doc = {
            "filename": file_path.name,
            "file_path": str(file_path.relative_to(REPO_ROOT) if file_path.is_relative_to(REPO_ROOT) else file_path),
            "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
            "sha256_hash": compute_sha256(file_path) if file_path.exists() else "unknown",
            "project": project,
            "source_type": source_type,
            "encoding": encoding
        }

        if source_files:
            input_doc["source_files_count"] = len(source_files)
            input_doc["source_files"] = source_files

        self._data["input_document"] = input_doc
        return self

    def set_schema(
        self,
        schema_path: Path,
        version: str = "1.0.0",
        source: str = "local"
    ) -> "D4DExtractionMetadata":
        """
        Set schema information.

        Args:
            schema_path: Path to the schema file
            version: Schema version string
            source: local, github, or url
        """
        schema_path = Path(schema_path)

        self._data["datasheets_schema"] = {
            "version": version,
            "source": source,
            "path": str(schema_path.relative_to(REPO_ROOT) if schema_path.is_relative_to(REPO_ROOT) else schema_path),
            "sha256_hash": compute_sha256(schema_path) if schema_path.exists() else "unknown",
            "loaded_at": datetime.now().isoformat(),
            "git_commit": get_git_commit() if source == "local" else None
        }
        return self

    def set_llm_model(
        self,
        provider: str,
        model_version: str,
        temperature: float = 0.0,
        max_tokens: int = 16000,
        top_p: Optional[float] = None,
        random_seed: Optional[int] = None
    ) -> "D4DExtractionMetadata":
        """
        Set LLM model configuration.

        Args:
            provider: anthropic, openai, google, or local
            model_version: Specific model version (date-pinned for reproducibility)
            temperature: Sampling temperature (0.0 for determinism)
            max_tokens: Maximum tokens in response
            top_p: Top-p sampling parameter
            random_seed: Random seed if supported
        """
        self._data["llm_model"] = {
            "provider": provider,
            "model_name": f"{provider}:{model_version}",
            "model_version": model_version,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "random_seed": random_seed,
            "is_deterministic": temperature == 0.0
        }
        return self

    def set_prompts(
        self,
        prompts_directory: Path,
        system_prompt_file: str,
        user_prompt_file: str,
        additional_prompts: Optional[List[Dict]] = None
    ) -> "D4DExtractionMetadata":
        """
        Set prompt file information.

        Args:
            prompts_directory: Directory containing prompt files
            system_prompt_file: Name of system prompt file
            user_prompt_file: Name of user prompt template file
            additional_prompts: List of additional prompt file dicts
        """
        prompts_dir = Path(prompts_directory)
        system_path = prompts_dir / system_prompt_file
        user_path = prompts_dir / user_prompt_file

        self._data["prompts"] = {
            "prompts_directory": str(prompts_dir.relative_to(REPO_ROOT) if prompts_dir.is_relative_to(REPO_ROOT) else prompts_dir),
            "system_prompt": {
                "filename": system_prompt_file,
                "file_path": str(system_path.relative_to(REPO_ROOT) if system_path.is_relative_to(REPO_ROOT) else system_path),
                "sha256_hash": compute_sha256(system_path) if system_path.exists() else "unknown",
                "prompt_type": "system"
            },
            "user_prompt": {
                "filename": user_prompt_file,
                "file_path": str(user_path.relative_to(REPO_ROOT) if user_path.is_relative_to(REPO_ROOT) else user_path),
                "sha256_hash": compute_sha256(user_path) if user_path.exists() else "unknown",
                "prompt_type": "user"
            }
        }

        if additional_prompts:
            self._data["prompts"]["additional_prompts"] = additional_prompts

        return self

    def set_output(
        self,
        output_path: Path,
        content: str,
        format: str = "yaml",
        fields_populated: Optional[int] = None,
        total_fields: Optional[int] = None
    ) -> "D4DExtractionMetadata":
        """
        Set output document information.

        Args:
            output_path: Path to output file
            content: Output content (for hash computation)
            format: yaml, json, or jsonld
            fields_populated: Number of fields with values
            total_fields: Total number of schema fields
        """
        output_path = Path(output_path)

        self._data["output"] = {
            "filename": output_path.name,
            "file_path": str(output_path.relative_to(REPO_ROOT) if output_path.is_relative_to(REPO_ROOT) else output_path),
            "size_bytes": len(content.encode('utf-8')),
            "sha256_hash": compute_content_sha256(content),
            "format": format
        }

        if fields_populated is not None:
            self._data["output"]["fields_populated"] = fields_populated
        if total_fields is not None:
            self._data["output"]["total_fields"] = total_fields

        # Update metadata file path
        metadata_filename = output_path.stem + "_metadata.yaml"
        self._data["output"]["metadata_file"] = str(output_path.parent / metadata_filename)

        return self

    def set_reproducibility(
        self,
        command: str,
        env_vars: Optional[List[Dict]] = None,
        verification_command: Optional[str] = None
    ) -> "D4DExtractionMetadata":
        """
        Set reproducibility settings.

        Args:
            command: Command to reproduce extraction
            env_vars: List of environment variable dicts
            verification_command: Command to verify reproduction
        """
        is_deterministic = (
            self._data.get("llm_model", {}).get("is_deterministic", False)
        )

        self._data["reproducibility"] = {
            "command": command,
            "deterministic_settings": is_deterministic,
            "platform": platform.system(),
            "python_version": platform.python_version()
        }

        if env_vars:
            self._data["reproducibility"]["environment_variables"] = env_vars
        else:
            # Default required env vars based on provider
            provider = self._data.get("llm_model", {}).get("provider", "")
            if provider == "anthropic":
                self._data["reproducibility"]["environment_variables"] = [
                    {"name": "ANTHROPIC_API_KEY", "required": True, "sensitive": True,
                     "description": "Anthropic API key for Claude models"}
                ]
            elif provider == "openai":
                self._data["reproducibility"]["environment_variables"] = [
                    {"name": "OPENAI_API_KEY", "required": True, "sensitive": True,
                     "description": "OpenAI API key for GPT models"}
                ]

        if verification_command:
            self._data["reproducibility"]["verification_command"] = verification_command

        return self

    def set_provenance(
        self,
        performed_by: str,
        requested_by: Optional[str] = None,
        notes: Optional[str] = None,
        parent_extraction_id: Optional[str] = None
    ) -> "D4DExtractionMetadata":
        """
        Set provenance information.

        Args:
            performed_by: Script or tool that performed extraction
            requested_by: User or system that requested extraction
            notes: Additional provenance notes
            parent_extraction_id: ID of parent extraction if derivative
        """
        self._data["provenance"] = {
            "extraction_performed_by": performed_by,
            "extraction_requested_at": self._start_time.isoformat(),
            "git_commit": get_git_commit(),
            "git_branch": get_git_branch(),
            "git_repository": "https://github.com/bridge2ai/data-sheets-schema"
        }

        if requested_by:
            self._data["provenance"]["extraction_requested_by"] = requested_by
        if notes:
            self._data["provenance"]["notes"] = notes
        if parent_extraction_id:
            self._data["provenance"]["parent_extraction_id"] = parent_extraction_id

        return self

    def set_validation_results(
        self,
        validated: bool,
        passed: Optional[bool] = None,
        command: Optional[str] = None,
        errors: Optional[List[Dict]] = None,
        warnings: Optional[List[Dict]] = None
    ) -> "D4DExtractionMetadata":
        """
        Set validation results.

        Args:
            validated: Whether validation was performed
            passed: Whether validation passed
            command: Validation command used
            errors: List of error dicts
            warnings: List of warning dicts
        """
        self._data["validation_results"] = {
            "validated": validated,
            "validation_timestamp": datetime.now().isoformat()
        }

        if passed is not None:
            self._data["validation_results"]["validation_passed"] = passed
        if command:
            self._data["validation_results"]["validation_command"] = command
        if errors:
            self._data["validation_results"]["error_count"] = len(errors)
            self._data["validation_results"]["errors"] = errors
        else:
            self._data["validation_results"]["error_count"] = 0
        if warnings:
            self._data["validation_results"]["warning_count"] = len(warnings)
            self._data["validation_results"]["warnings"] = warnings
        else:
            self._data["validation_results"]["warning_count"] = 0

        return self

    def set_comparison(
        self,
        compared_to: str,
        comparison_type: str,
        identical: Optional[bool] = None,
        fields_diff: Optional[int] = None,
        completeness: Optional[float] = None,
        notes: Optional[str] = None
    ) -> "D4DExtractionMetadata":
        """
        Set comparison metrics.

        Args:
            compared_to: What this was compared to
            comparison_type: reproducibility, cross_method, cross_model, ground_truth
            identical: Whether output is identical to comparison target
            fields_diff: Number of differing fields
            completeness: Completeness score (0-1)
            notes: Comparison notes
        """
        self._data["comparison"] = {
            "compared_to": compared_to,
            "comparison_type": comparison_type
        }

        if identical is not None:
            self._data["comparison"]["identical_to_previous"] = identical
        if fields_diff is not None:
            self._data["comparison"]["fields_difference_count"] = fields_diff
        if completeness is not None:
            self._data["comparison"]["completeness_score"] = completeness
        if notes:
            self._data["comparison"]["comparison_notes"] = notes

        return self

    def set_api_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        elapsed_seconds: float
    ) -> "D4DExtractionMetadata":
        """
        Set API usage statistics (stored in notes for now).

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            elapsed_seconds: API call duration
        """
        # Store in notes since not in schema
        self.add_note(
            f"API usage: {input_tokens:,} input tokens, "
            f"{output_tokens:,} output tokens, "
            f"{elapsed_seconds:.1f}s elapsed"
        )
        return self

    def complete(self, status: str = "completed") -> "D4DExtractionMetadata":
        """
        Mark extraction as complete and calculate processing time.

        Args:
            status: completed, failed, or validation_failed
        """
        end_time = datetime.now()
        self._data["extraction_metadata"]["completed_at"] = end_time.isoformat()
        self._data["extraction_metadata"]["processing_time_seconds"] = (
            end_time - self._start_time
        ).total_seconds()
        self._data["extraction_metadata"]["status"] = status
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Return metadata as dictionary."""
        # Remove None values for cleaner output
        return self._clean_dict(self._data)

    def _clean_dict(self, d: Dict) -> Dict:
        """Recursively remove None values and empty lists from dict."""
        cleaned = {}
        for k, v in d.items():
            if v is None:
                continue
            if isinstance(v, dict):
                cleaned_sub = self._clean_dict(v)
                if cleaned_sub:  # Don't add empty dicts
                    cleaned[k] = cleaned_sub
            elif isinstance(v, list):
                if v:  # Don't add empty lists
                    cleaned[k] = v
            else:
                cleaned[k] = v
        return cleaned

    def save(self, output_path: Path) -> Path:
        """
        Save metadata to YAML file.

        Args:
            output_path: Path to save metadata file

        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                self.to_dict(),
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )

        return output_path


def create_extraction_metadata(
    extraction_type: str,
    input_path: Path,
    project: str,
    schema_path: Path,
    provider: str,
    model_version: str,
    prompts_dir: Path,
    system_prompt: str,
    user_prompt: str,
    output_path: Path,
    output_content: str,
    performed_by: str,
    temperature: float = 0.0,
    max_tokens: int = 16000,
    command: Optional[str] = None
) -> D4DExtractionMetadata:
    """
    Convenience function to create fully populated extraction metadata.

    Args:
        extraction_type: Type of extraction (see ExtractionTypeEnum)
        input_path: Path to input file
        project: Project name
        schema_path: Path to schema file
        provider: LLM provider
        model_version: Model version string
        prompts_dir: Directory containing prompts
        system_prompt: System prompt filename
        user_prompt: User prompt filename
        output_path: Path to output file
        output_content: Generated output content
        performed_by: Script/tool name
        temperature: LLM temperature
        max_tokens: Max tokens setting
        command: Reproduction command

    Returns:
        Populated D4DExtractionMetadata instance
    """
    metadata = D4DExtractionMetadata()

    metadata.set_extraction_type(extraction_type)
    metadata.set_input_document(input_path, project)
    metadata.set_schema(schema_path)
    metadata.set_llm_model(provider, model_version, temperature, max_tokens)
    metadata.set_prompts(prompts_dir, system_prompt, user_prompt)
    metadata.set_output(output_path, output_content)
    metadata.set_provenance(performed_by)

    if command:
        metadata.set_reproducibility(command)

    return metadata
