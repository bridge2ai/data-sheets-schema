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

Usage:
    python process_d4d_deterministic.py -i INPUT_FILE -o OUTPUT_FILE -p PROJECT
    python process_d4d_deterministic.py --all  # Process all projects

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
import hashlib
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    import anthropic
    import yaml
except ImportError:
    print("Error: Required packages not installed")
    print("Install with: pip install anthropic pyyaml")
    sys.exit(1)


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

# Projects to process
PROJECTS = ["AI_READI", "CHORUS", "CM4AI", "VOICE"]


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


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
    except subprocess.CalledProcessError:
        return "unknown"


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
    api_key: str
) -> Tuple[str, Dict]:
    """
    Generate D4D YAML from concatenated input using Claude API.

    Returns:
        Tuple of (yaml_content, metadata_dict)
    """
    print(f"\n{'='*80}")
    print(f"📄 Processing: {input_file.relative_to(REPO_ROOT)}")
    print(f"{'='*80}\n")

    # Load schema and prompts
    print("📂 Loading prompts from external files...")
    system_prompt_template, user_prompt_template = load_prompts()

    print("📋 Loading local schema file...")
    schema_content = load_schema()

    # Compute input hash
    input_hash = compute_sha256(input_file)
    print(f"🔐 Input file SHA-256: {input_hash}")

    # Read input content
    input_content = read_file_with_fallback(input_file)
    print(f"📊 Input size: {len(input_content):,} characters\n")

    # Prepare prompts
    system_prompt = system_prompt_template.replace("{schema}", schema_content)
    user_prompt = user_prompt_template.replace("{project_name}", project_name)
    user_prompt = user_prompt.replace("{input_filename}", input_file.name)
    user_prompt = user_prompt.replace("{content}", input_content)

    # Compute prompt hashes
    system_prompt_hash = hashlib.sha256(system_prompt.encode()).hexdigest()
    user_prompt_hash = hashlib.sha256(user_prompt.encode()).hexdigest()
    schema_hash = compute_sha256(SCHEMA_FILE)

    # Initialize Claude client
    print(f"🤖 Initializing Claude API with temperature={TEMPERATURE}...")
    client = anthropic.Anthropic(api_key=api_key)

    # Call Claude API with deterministic settings
    print(f"🔄 Calling Claude API ({MODEL_NAME})...\n")
    start_time = datetime.now()

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

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"✅ API call completed in {elapsed:.1f}s")
        print(f"📊 Usage - Input: {message.usage.input_tokens:,} tokens, "
              f"Output: {message.usage.output_tokens:,} tokens\n")

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
        else:
            print("⚠️  YAML may have validation issues\n")

        # Prepare metadata
        metadata = {
            "generation_info": {
                "tool": "process_d4d_deterministic.py",
                "timestamp": datetime.now().isoformat(),
                "git_commit": get_git_commit()
            },
            "model_settings": {
                "model": MODEL_NAME,
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS,
                "framework": "anthropic-python-sdk"
            },
            "input_files": {
                "concatenated_input": {
                    "path": str(input_file.relative_to(REPO_ROOT)),
                    "sha256": input_hash,
                    "size_chars": len(input_content)
                },
                "schema": {
                    "path": str(SCHEMA_FILE.relative_to(REPO_ROOT)),
                    "sha256": schema_hash
                },
                "system_prompt": {
                    "path": "src/download/prompts/d4d_concatenated_system_prompt.txt",
                    "sha256": hashlib.sha256(
                        read_file_with_fallback(
                            PROMPTS_DIR / "d4d_concatenated_system_prompt.txt"
                        ).encode()
                    ).hexdigest()
                },
                "user_prompt_template": {
                    "path": "src/download/prompts/d4d_concatenated_user_prompt.txt",
                    "sha256": hashlib.sha256(
                        read_file_with_fallback(
                            PROMPTS_DIR / "d4d_concatenated_user_prompt.txt"
                        ).encode()
                    ).hexdigest()
                }
            },
            "output_info": {
                "project": project_name,
                "valid_yaml": is_valid,
                "size_chars": len(yaml_content),
                "output_sha256": hashlib.sha256(yaml_content.encode()).hexdigest()
            },
            "api_usage": {
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
                "total_tokens": message.usage.input_tokens + message.usage.output_tokens,
                "elapsed_seconds": elapsed
            },
            "reproducibility": {
                "command": f"python src/download/process_d4d_deterministic.py "
                          f"-i {input_file.relative_to(REPO_ROOT)} "
                          f"-o data/d4d_concatenated/claudecode/{project_name}_d4d.yaml "
                          f"-p {project_name}",
                "notes": "Requires ANTHROPIC_API_KEY environment variable. "
                        "Temperature=0.0 ensures deterministic output."
            }
        }

        return yaml_content, metadata

    except anthropic.APIError as e:
        print(f"❌ API Error: {e}")
        raise


def process_project(project: str, api_key: str) -> bool:
    """Process a single project."""
    input_file = CONCAT_INPUT_DIR / f"{project}_concatenated.txt"
    output_file = OUTPUT_DIR / f"{project}_d4d.yaml"
    metadata_file = OUTPUT_DIR / f"{project}_d4d_metadata.yaml"

    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        print(f"   Run 'make concat-extracted PROJECT={project}' first")
        return False

    try:
        # Generate D4D YAML
        yaml_content, metadata = generate_d4d_yaml(input_file, project, api_key)

        # Save YAML output
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"💾 Saving YAML file...")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        print(f"   ✅ Saved to: {output_file.relative_to(REPO_ROOT)}")

        # Save metadata
        print(f"💾 Saving metadata file...")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)
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
        print("  python process_d4d_deterministic.py -i data/preprocessed/concatenated/AI_READI_concatenated.txt \\")
        print("      -o data/d4d_concatenated/claudecode/AI_READI_d4d.yaml -p AI_READI")
        print("\n  # Process all projects")
        print("  python process_d4d_deterministic.py --all")
        sys.exit(1)


if __name__ == "__main__":
    main()
