#!/usr/bin/env python3
"""
Process individual preprocessed files to generate D4D YAML metadata using GPT-5.

This script processes individual text files from data/preprocessed/individual/
and generates D4D YAML metadata for each file using GPT-5.

Usage:
    # Process all files in a project directory
    python process_individual_d4d_gpt5.py -i data/preprocessed/individual/AI_READI -o data/d4d_individual/gpt5/AI_READI

    # Process all projects
    python process_individual_d4d_gpt5.py --all-projects
"""

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
import yaml
from pydantic_ai import Agent
from dataclasses import dataclass


@dataclass
class SimpleD4DConfig:
    """Simple configuration for D4D processing."""
    schema_url: str = "https://raw.githubusercontent.com/bridge2ai/data-sheets-schema/main/src/data_sheets_schema/schema/data_sheets_schema.yaml"


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def load_schema() -> str:
    """Load the D4D schema from GitHub."""
    try:
        config = SimpleD4DConfig()
        response = requests.get(config.schema_url, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"❌ Error loading D4D schema: {e}")
        raise


def read_file_content(file_path: Path) -> str:
    """Read content from various file types."""
    try:
        if file_path.suffix == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return json.dumps(data, indent=2)
        elif file_path.suffix in ['.txt', '.html', '.md']:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Truncate very long content
                if len(content) > 50000:
                    content = content[:50000] + "\n\n... [Content truncated for length] ..."
                return content
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"


async def process_single_file(
    input_file: Path,
    output_file: Path,
    project: str,
    schema: str,
    agent: Agent
) -> tuple[bool, str]:
    """
    Process a single file with GPT-5 to generate D4D YAML.

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        print(f"  📄 Processing: {input_file.name}")

        # Read file content
        content = read_file_content(input_file)

        if len(content) < 50:
            return False, "Content too short"

        # Prepare prompt
        prompt = f"""
Please analyze the following content and extract dataset metadata following the D4D schema.

Source file: {input_file.name}
Content type: {input_file.suffix}
Project: {project}

Content to analyze:
{content}

Generate a complete D4D YAML document based on this content. Include as much relevant information as you can extract from the source material. The output must be valid YAML without any markdown formatting or code blocks.
"""

        # Run the agent
        config = SimpleD4DConfig()
        result = await agent.run(prompt, deps=config)

        # Extract YAML from result
        yaml_content = result.output.strip()

        # Clean up the output - remove any markdown formatting
        if yaml_content.startswith('```yaml'):
            yaml_content = yaml_content[7:]
        if yaml_content.startswith('```'):
            yaml_content = yaml_content[3:]
        if yaml_content.endswith('```'):
            yaml_content = yaml_content[:-3]
        yaml_content = yaml_content.strip()

        # Validate YAML
        try:
            parsed_yaml = yaml.safe_load(yaml_content)
            if not isinstance(parsed_yaml, dict):
                # Save debug file
                debug_file = output_file.parent / f"{output_file.stem}_debug.txt"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(yaml_content)
                return False, f"Generated content is not a valid YAML document (saved to {debug_file.name})"
        except yaml.YAMLError as e:
            # Save debug file
            debug_file = output_file.parent / f"{output_file.stem}_debug.txt"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            return False, f"Invalid YAML generated: {e} (saved to {debug_file.name})"

        # Save YAML file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)

        print(f"    ✅ Generated: {output_file.name}")
        return True, "Success"

    except Exception as e:
        error_msg = str(e)
        print(f"    ❌ Failed: {error_msg}")
        return False, error_msg


async def process_project_directory(
    input_dir: Path,
    output_dir: Path,
    project: str,
    schema: str
) -> dict:
    """
    Process all files in a project directory.

    Returns:
        Dictionary with processing statistics
    """
    print(f"\n📂 Processing project: {project}")
    print(f"   Input: {input_dir}")
    print(f"   Output: {output_dir}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        raise ValueError("Missing OPENAI_API_KEY")

    # Create GPT-5-based D4D agent
    d4d_agent = Agent(
        model="openai:gpt-5",
        deps_type=SimpleD4DConfig,
        system_prompt=f"""
You are an expert data scientist specializing in extracting metadata from datasets.
You will be provided with a schema that describes the metadata structure for datasets,
and content describing a dataset.
Your task is to extract all relevant metadata from the provided content and output it in
YAML format, strictly following the provided schema. Generate only the YAML document.
Do not respond with any additional commentary. Try to ensure that required fields are
present, but only populate items that you are sure about. Ensure that output is valid
YAML.

Below is the complete datasheets for datasets schema:

{schema}

You should extract all the relevant metadata from the provided content and output a single
YAML document describing the dataset, exactly conforming to the above schema.
The output must be valid YAML with all required fields filled in where information is available.

IMPORTANT: Output ONLY the YAML content. Do NOT wrap it in markdown code blocks or add any
additional text before or after the YAML.
""",
        defer_model_check=True,
    )

    results = {
        'project': project,
        'processed': [],
        'skipped': [],
        'errors': []
    }

    # Get all files to process
    files_to_process = []
    for file_path in input_dir.iterdir():
        if file_path.is_file() and file_path.suffix in ['.txt', '.json', '.html', '.md']:
            files_to_process.append(file_path)

    print(f"   Found {len(files_to_process)} files to process")

    if not files_to_process:
        print("   ⚠️  No files found to process")
        return results

    # Process each file
    for file_path in sorted(files_to_process):
        # Generate output filename
        base_name = file_path.stem

        # Clean up filename - remove row suffixes for cleaner names
        if '_row' in base_name:
            base_name = base_name.split('_row')[0]

        output_filename = f"{base_name}_d4d.yaml"
        output_path = output_dir / output_filename

        # Skip if already exists
        if output_path.exists():
            print(f"  ⏭️  Skipping (exists): {file_path.name}")
            results['skipped'].append({
                'file': str(file_path),
                'reason': 'Already exists'
            })
            continue

        # Process with agent
        success, message = await process_single_file(
            file_path, output_path, project, schema, d4d_agent
        )

        if success:
            results['processed'].append({
                'input_file': str(file_path),
                'output_file': str(output_path),
                'status': 'success'
            })
        else:
            results['errors'].append({
                'file': str(file_path),
                'error': message
            })

        # Small delay to be respectful to API
        await asyncio.sleep(1)

    return results


async def process_all_projects(base_input_dir: Path, base_output_dir: Path):
    """Process all projects."""
    projects = ['AI_READI', 'CHORUS', 'CM4AI', 'VOICE']

    print("🚀 Processing all projects with GPT-5...")

    all_results = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'base_input_dir': str(base_input_dir),
        'base_output_dir': str(base_output_dir),
        'projects': [],
        'summary': {
            'total_processed': 0,
            'total_errors': 0,
            'total_skipped': 0
        }
    }

    # Load schema once
    print("\n📥 Loading D4D schema...")
    schema = load_schema()
    print("✅ Schema loaded")

    for project in projects:
        input_dir = base_input_dir / project
        output_dir = base_output_dir / project

        if not input_dir.exists():
            print(f"\n⚠️  Skipping {project}: input directory not found")
            continue

        results = await process_project_directory(input_dir, output_dir, project, schema)
        all_results['projects'].append(results)

        # Update summary
        all_results['summary']['total_processed'] += len(results['processed'])
        all_results['summary']['total_errors'] += len(results['errors'])
        all_results['summary']['total_skipped'] += len(results['skipped'])

    # Save summary
    base_output_dir.mkdir(parents=True, exist_ok=True)
    summary_file = base_output_dir / "individual_d4d_processing_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    # Print final summary
    print("\n" + "="*60)
    print("INDIVIDUAL D4D PROCESSING COMPLETE (GPT-5)")
    print("="*60)
    summary = all_results['summary']
    print(f"✅ Files processed: {summary['total_processed']}")
    print(f"❌ Errors: {summary['total_errors']}")
    print(f"⏭️  Skipped: {summary['total_skipped']}")
    print(f"\n📁 Output directory: {base_output_dir.absolute()}")
    print(f"📊 Summary saved: {summary_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process individual preprocessed files to generate D4D YAML metadata using GPT-5"
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        help="Input directory with preprocessed files (e.g., data/preprocessed/individual/AI_READI)"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output directory for D4D YAML files (e.g., data/d4d_individual/gpt5/AI_READI)"
    )
    parser.add_argument(
        "-p", "--project",
        type=str,
        help="Project name (AI_READI, CHORUS, CM4AI, VOICE)"
    )
    parser.add_argument(
        "--all-projects",
        action="store_true",
        help="Process all projects (uses default paths)"
    )

    args = parser.parse_args()

    if args.all_projects:
        # Use default paths for all projects
        # Get the project root directory (parent of src/)
        project_root = Path(__file__).parent.parent.parent
        base_input_dir = project_root / "data" / "preprocessed" / "individual"
        base_output_dir = project_root / "data" / "d4d_individual" / "gpt5"

        asyncio.run(process_all_projects(base_input_dir, base_output_dir))

    elif args.input and args.output:
        # Process single directory
        if not args.input.exists():
            print(f"❌ Error: Input directory not found: {args.input}")
            sys.exit(1)

        project = args.project or args.input.name

        print(f"🚀 Processing {project} with GPT-5...")

        # Load schema
        print("\n📥 Loading D4D schema...")
        schema = load_schema()
        print("✅ Schema loaded")

        results = asyncio.run(process_project_directory(
            args.input, args.output, project, schema
        ))

        # Print summary
        print("\n" + "="*60)
        print("PROCESSING COMPLETE")
        print("="*60)
        print(f"✅ Files processed: {len(results['processed'])}")
        print(f"❌ Errors: {len(results['errors'])}")
        print(f"⏭️  Skipped: {len(results['skipped'])}")
        print(f"\n📁 Output directory: {args.output.absolute()}")

        if results['errors']:
            print("\n❌ Errors:")
            for error in results['errors']:
                print(f"   - {Path(error['file']).name}: {error['error']}")

    else:
        parser.print_help()
        print("\nError: Either --all-projects OR both -i and -o must be specified")
        sys.exit(1)


if __name__ == "__main__":
    main()
