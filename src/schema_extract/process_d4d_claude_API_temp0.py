#!/usr/bin/env python3
"""
Deterministic D4D YAML Generator using Claude Code Framework

This script generates Datasheet for Datasets (D4D) YAML files from concatenated
documents using Claude Sonnet 4.5 with deterministic settings (temperature=0.0).

Following the deterministic principles from DETERMINISM.md:
- Temperature: 0.0 (maximum determinism)
- Model: claude-sonnet-4-5-20250929 (date-pinned)
- Schema: Local version-controlled file
- Prompts: External version-controlled files
- Metadata: Comprehensive provenance tracking with SHA-256 hashes

Metadata conforms to: src/schema_extract/d4d_extract_process.yaml

Usage:
    python process_d4d_claude_API_temp0.py -i INPUT_FILE -o OUTPUT_FILE -p PROJECT
    python process_d4d_claude_API_temp0.py --all  # Process all projects

Requirements:
    - ANTHROPIC_API_KEY environment variable must be set
    - pip install anthropic pyyaml

Limitations:
    - Requires ANTHROPIC_API_KEY (API-based approach)
    - API costs apply per run
    - Network connectivity required
    - Rate limits may apply for batch processing

Alternative:
    - Use Claude Code assistant for direct synthesis (see DETERMINISM.md)
    - Manual approach provides same deterministic principles without API costs
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple

try:
    import anthropic
    import yaml
except ImportError:
    print("Error: Required packages not installed")
    print("Install with: pip install anthropic pyyaml")
    sys.exit(1)

# Import metadata generator (schema-conformant)
from d4d_extract_metadata import D4DExtractionMetadata, compute_sha256


# Deterministic model settings
MODEL_NAME = "claude-sonnet-4-5-20250929"
TEMPERATURE = 0.0
MAX_TOKENS = 16000

# Directory paths
REPO_ROOT = Path(__file__).parent.parent.parent
PROMPTS_DIR = REPO_ROOT / "src/download/prompts"
SCHEMA_FILE = REPO_ROOT / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
CONCAT_INPUT_DIR = REPO_ROOT / "data/preprocessed/concatenated"
OUTPUT_DIR = REPO_ROOT / "data/d4d_concatenated/claudecode"

# Prompt filenames
SYSTEM_PROMPT_FILE = "d4d_concatenated_system_prompt.txt"
USER_PROMPT_FILE = "d4d_concatenated_user_prompt.txt"

# Projects to process
PROJECTS = ["AI_READI", "CHORUS", "CM4AI", "VOICE"]


def read_file_with_fallback(file_path: Path) -> str:
    """Read file with encoding fallbacks (UTF-8 → UTF-8-sig → latin-1)."""
    encodings = ['utf-8', 'utf-8-sig', 'latin-1']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError(f"Could not read file {file_path} with any supported encoding")


def load_prompts() -> Tuple[str, str]:
    """Load system and user prompt templates from external files."""
    system_prompt_file = PROMPTS_DIR / "d4d_concatenated_system_prompt.txt"
    user_prompt_file = PROMPTS_DIR / "d4d_concatenated_user_prompt.txt"

    if not system_prompt_file.exists():
        raise FileNotFoundError(f"System prompt not found: {system_prompt_file}")
    if not user_prompt_file.exists():
        raise FileNotFoundError(f"User prompt not found: {user_prompt_file}")

    system_prompt = read_file_with_fallback(system_prompt_file)
    user_prompt_template = read_file_with_fallback(user_prompt_file)

    return system_prompt, user_prompt_template


def load_schema() -> str:
    """Load the D4D schema from local version-controlled file."""
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_FILE}")
    return read_file_with_fallback(SCHEMA_FILE)


def extract_yaml_from_response(response: str) -> str:
    """Extract YAML content from response, handling markdown code blocks."""
    # Remove markdown code blocks if present
    if "```yaml" in response:
        start = response.find("```yaml") + 7
        end = response.find("```", start)
        if end != -1:
            return response[start:end].strip()
    elif "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        if end != -1:
            return response[start:end].strip()
    return response.strip()


def validate_yaml(yaml_content: str) -> bool:
    """Validate that the content is valid YAML."""
    try:
        yaml.safe_load(yaml_content)
        return True
    except yaml.YAMLError as e:
        print(f"⚠️  YAML validation error: {e}")
        return False


def generate_d4d_yaml(
    input_file: Path,
    project_name: str,
    output_file: Path,
    api_key: str
) -> Tuple[str, D4DExtractionMetadata]:
    """
    Generate D4D YAML from concatenated input using Claude API.

    Returns:
        Tuple of (yaml_content, D4DExtractionMetadata)
    """
    print(f"\n{'='*80}")
    print(f"📄 Processing: {input_file.relative_to(REPO_ROOT)}")
    print(f"{'='*80}\n")

    # Initialize metadata tracker (schema-conformant)
    metadata = D4DExtractionMetadata()
    metadata.set_description(f"D4D extraction for {project_name} using Claude API (temp=0)")
    metadata.set_extraction_type("concatenated_claude_api")

    # Load schema and prompts
    print("📂 Loading prompts from external files...")
    system_prompt_template, user_prompt_template = load_prompts()

    print("📋 Loading local schema file...")
    schema_content = load_schema()

    # Set input document metadata
    metadata.set_input_document(
        file_path=input_file,
        project=project_name,
        source_type="concatenated"
    )

    # Compute input hash
    input_hash = compute_sha256(input_file)
    print(f"🔐 Input file SHA-256: {input_hash}")

    # Read input content
    input_content = read_file_with_fallback(input_file)
    print(f"📊 Input size: {len(input_content):,} characters\n")

    # Set schema metadata
    metadata.set_schema(SCHEMA_FILE, version="1.0.0", source="local")

    # Prepare prompts
    system_prompt = system_prompt_template.replace("{schema}", schema_content)
    user_prompt = user_prompt_template.replace("{project_name}", project_name)
    user_prompt = user_prompt.replace("{input_filename}", input_file.name)
    user_prompt = user_prompt.replace("{content}", input_content)

    # Set prompts metadata
    metadata.set_prompts(
        prompts_directory=PROMPTS_DIR,
        system_prompt_file=SYSTEM_PROMPT_FILE,
        user_prompt_file=USER_PROMPT_FILE
    )

    # Set LLM model metadata
    metadata.set_llm_model(
        provider="anthropic",
        model_version=MODEL_NAME,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS
    )

    # Initialize Claude client
    print(f"🤖 Initializing Claude API with temperature={TEMPERATURE}...")
    client = anthropic.Anthropic(api_key=api_key)

    # Call Claude API with deterministic settings
    print(f"🔄 Calling Claude API ({MODEL_NAME})...\n")

    try:
        message = client.messages.create(
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )

        print(f"✅ API call completed")
        print(f"📊 Usage - Input: {message.usage.input_tokens:,} tokens, "
              f"Output: {message.usage.output_tokens:,} tokens\n")

        # Track API usage in metadata notes
        metadata.set_api_usage(
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            elapsed_seconds=0  # Will be set by complete()
        )

        # Extract response
        response_text = message.content[0].text
        print(f"📏 Response length: {len(response_text):,} characters")

        # Extract YAML
        print("📝 Extracting YAML from response...")
        yaml_content = extract_yaml_from_response(response_text)

        # Validate YAML
        print("🔍 Validating YAML...")
        is_valid = validate_yaml(yaml_content)

        if is_valid:
            print("✅ Generated valid YAML\n")
            metadata.set_validation_results(validated=True, passed=True)
        else:
            print("⚠️  YAML may have validation issues\n")
            metadata.set_validation_results(validated=True, passed=False)

        # Set output metadata
        metadata.set_output(
            output_path=output_file,
            content=yaml_content,
            format="yaml"
        )

        # Set reproducibility metadata
        command = (
            f"python src/schema_extract/process_d4d_claude_API_temp0.py "
            f"-i {input_file.relative_to(REPO_ROOT)} "
            f"-o {output_file.relative_to(REPO_ROOT)} "
            f"-p {project_name}"
        )
        metadata.set_reproducibility(command=command)

        # Set provenance
        metadata.set_provenance(
            performed_by="process_d4d_claude_API_temp0.py",
            notes="Deterministic D4D extraction using Claude Sonnet 4.5 with temperature=0.0"
        )

        # Mark complete
        metadata.complete(status="completed")

        return yaml_content, metadata

    except anthropic.APIError as e:
        print(f"❌ API Error: {e}")
        metadata.complete(status="failed")
        metadata.add_note(f"API Error: {str(e)}")
        raise


def process_project(project: str, api_key: str) -> bool:
    """Process a single project."""
    input_file = CONCAT_INPUT_DIR / "sources" / f"{project}_sources_concatenated.txt"
    output_file = OUTPUT_DIR / f"{project}_d4d.yaml"
    metadata_file = OUTPUT_DIR / f"{project}_d4d_metadata.yaml"

    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        print(f"   Run 'make concat-docs INPUT_DIR=data/preprocessed/individual/{project} OUTPUT_FILE=data/preprocessed/concatenated/sources/{project}_sources_concatenated.txt' first")
        return False

    try:
        # Generate D4D YAML with schema-conformant metadata
        yaml_content, metadata = generate_d4d_yaml(input_file, project, output_file, api_key)

        # Save YAML output
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"💾 Saving YAML file...")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        print(f"   ✅ Saved to: {output_file.relative_to(REPO_ROOT)}")

        # Save schema-conformant metadata
        print(f"💾 Saving metadata file (d4d_extract_process schema)...")
        metadata.save(metadata_file)
        print(f"   ✅ Saved to: {metadata_file.relative_to(REPO_ROOT)}")

        print(f"\n✅ Successfully processed {project}")
        return True

    except Exception as e:
        print(f"\n❌ Error processing {project}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate D4D YAML files using deterministic Claude Code approach",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        help="Input concatenated file"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output D4D YAML file"
    )
    parser.add_argument(
        "-p", "--project",
        help="Project name (AI_READI, CHORUS, CM4AI, VOICE)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all projects"
    )

    args = parser.parse_args()

    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("\nOptions:")
        print("1. Set ANTHROPIC_API_KEY: export ANTHROPIC_API_KEY='your-key'")
        print("2. Use Claude Code assistant for direct synthesis (see DETERMINISM.md)")
        print("\nLimitations:")
        print("- API-based approach requires ANTHROPIC_API_KEY and incurs API costs")
        print("- Alternative: Claude Code assistant direct synthesis (no API key needed)")
        sys.exit(1)

    print("═" * 80)
    print("  Deterministic D4D Generator - Claude Code Framework")
    print("═" * 80)
    print(f"Model: {MODEL_NAME}")
    print(f"Temperature: {TEMPERATURE} (deterministic)")
    print(f"Max Tokens: {MAX_TOKENS}")
    print(f"Schema: {SCHEMA_FILE.relative_to(REPO_ROOT)}")
    print("═" * 80)

    if args.all:
        # Process all projects
        print("\n🔄 Processing all projects...\n")
        results = {}
        for project in PROJECTS:
            success = process_project(project, api_key)
            results[project] = success

        # Summary
        print("\n" + "═" * 80)
        print("  Summary")
        print("═" * 80)
        for project, success in results.items():
            status = "✅ Success" if success else "❌ Failed"
            print(f"{project:12s} - {status}")

        failed = sum(1 for s in results.values() if not s)
        if failed > 0:
            print(f"\n⚠️  {failed} project(s) failed")
            sys.exit(1)
        else:
            print(f"\n✅ All {len(PROJECTS)} projects processed successfully")

    elif args.input and args.output and args.project:
        # Process single file
        success = process_project(args.project, api_key)
        sys.exit(0 if success else 1)

    else:
        parser.print_help()
        print("\nExamples:")
        print("  # Process single project")
        print("  python src/schema_extract/process_d4d_claude_API_temp0.py \\")
        print("      -i data/preprocessed/concatenated/sources/AI_READI_sources_concatenated.txt \\")
        print("      -o data/d4d_concatenated/claudecode/AI_READI_d4d.yaml -p AI_READI")
        print("\n  # Process all projects")
        print("  python src/schema_extract/process_d4d_claude_API_temp0.py --all")
        print("\nMetadata output conforms to: src/schema_extract/d4d_extract_process.yaml")
        sys.exit(1)


if __name__ == "__main__":
    main()
