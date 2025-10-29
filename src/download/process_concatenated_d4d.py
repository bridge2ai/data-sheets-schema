#!/usr/bin/env python3
"""
Process Concatenated D4D Documents - Run D4D agent on concatenated documents

This script processes concatenated documents (created by concatenate_documents.py)
and generates D4D YAML metadata using the Anthropic Claude-based D4D agent.
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional
import argparse
import yaml

# Add the aurelian src directory to path for D4D agent imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "aurelian" / "src"))

try:
    from pydantic_ai import Agent
    from aurelian.agents.d4d.d4d_config import D4DConfig
    from aurelian.agents.d4d.d4d_tools import get_full_schema
except ImportError as e:
    print(f"Error importing D4D agent components: {e}")
    print("Make sure you have installed the aurelian dependencies and the path is correct.")
    sys.exit(1)


class ConcatenatedD4DProcessor:
    """Process concatenated documents with D4D agent."""

    def __init__(self, model: str = "anthropic:claude-3-5-sonnet-20241022"):
        """
        Initialize the processor.

        Args:
            model: Model to use for D4D agent (default: claude-3-5-sonnet-20241022)
        """
        self.model = model

        # Check for API key
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
            print("Please set your Anthropic API key:")
            print("export ANTHROPIC_API_KEY='your-api-key-here'")
            sys.exit(1)

        # Create Claude-based D4D agent
        self.d4d_agent = Agent(
            model=self.model,
            deps_type=D4DConfig,
            system_prompt="""
You are an expert data scientist specializing in extracting metadata from datasets following the "Datasheets for Datasets" schema.

Below is the complete datasheets for datasets schema:

{schema}

Your task is to analyze the provided concatenated document which contains multiple related dataset documentation files that have been merged together. Extract all relevant dataset metadata to generate a complete YAML document that strictly follows the D4D schema above.

The input may contain:
- Multiple YAML files that are already in D4D format (synthesize these into a single comprehensive document)
- Text documentation about the dataset
- Metadata files
- Multiple perspectives on the same dataset

Focus on extracting and synthesizing:
- Dataset identity (id, name, title, description)
- Creators and contributors with affiliations
- Purpose and intended uses
- Data composition and structure
- Collection methodology and timeframe
- Preprocessing and cleaning steps
- Distribution information and formats
- Licensing and terms of use
- Maintenance information
- Access requirements and restrictions
- Funding and grants
- Ethics and human subjects considerations

When multiple D4D YAML files are present in the input:
1. Merge complementary information from all files
2. Prefer more detailed/specific information over generic
3. Keep the most comprehensive descriptions
4. Combine all relevant metadata sections

Generate only valid YAML output without any additional commentary. Ensure all required fields are populated where information is available. If specific information is not available in the source, omit those fields rather than making assumptions.
""",
            defer_model_check=True,
        )

        # Add schema loading
        @self.d4d_agent.system_prompt
        async def add_schema(ctx) -> str:
            """Add the full schema to the system prompt."""
            schema = await get_full_schema(ctx)
            return schema

    def read_concatenated_file(self, file_path: Path) -> str:
        """
        Read concatenated document.

        Args:
            file_path: Path to concatenated file

        Returns:
            File content as string
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Fall back to UTF-8 with BOM signature removal
            try:
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    return f.read()
            except UnicodeDecodeError:
                # Fall back to latin-1
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()

    async def process_concatenated_file(
        self,
        input_file: Path,
        output_file: Optional[Path] = None,
        project_name: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Process a concatenated file with D4D agent.

        Args:
            input_file: Path to concatenated input file
            output_file: Path to output D4D YAML file (default: input_file with _d4d.yaml)
            project_name: Optional project/column name for context

        Returns:
            Tuple of (success, message)
        """
        try:
            print(f"📄 Processing: {input_file}")

            # Read concatenated content
            content = self.read_concatenated_file(input_file)

            if len(content) < 100:  # Skip very short files
                return False, "Content too short"

            # Determine output file
            if output_file is None:
                output_file = input_file.parent / f"{input_file.stem}_synthesized.yaml"

            # Prepare prompt for D4D agent
            prompt = f"""
Please analyze the following concatenated document and synthesize a comprehensive D4D YAML document.

This concatenated document contains multiple files related to the same dataset project.
"""
            if project_name:
                prompt += f"\nProject: {project_name}\n"

            prompt += f"""
Source file: {input_file.name}

Concatenated content to analyze:
{content}

Generate a single, comprehensive D4D YAML document that synthesizes all the information from the concatenated files above. Merge complementary information and create the most complete dataset documentation possible.
"""

            # Configure D4D agent
            config = D4DConfig()

            print(f"   🤖 Running D4D agent (model: {self.model})...")
            start_time = time.time()

            # Run the agent
            result = await self.d4d_agent.run(prompt, deps=config)

            elapsed = time.time() - start_time
            print(f"   ⏱️  Agent completed in {elapsed:.1f}s")

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
                parsed = yaml.safe_load(yaml_content)
                print(f"   ✅ Generated valid YAML")
            except yaml.YAMLError as e:
                return False, f"Invalid YAML generated: {e}"

            # Save YAML file
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(yaml_content)

            print(f"   💾 Saved to: {output_file}")
            return True, "Success"

        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Failed: {error_msg}")
            return False, error_msg

    async def process_directory(
        self,
        input_dir: Path,
        output_dir: Optional[Path] = None,
        pattern: str = "*_d4d.txt"
    ) -> dict:
        """
        Process all concatenated files in a directory.

        Args:
            input_dir: Directory containing concatenated files
            output_dir: Directory for output files (default: input_dir)
            pattern: Glob pattern for files to process

        Returns:
            Dictionary with processing statistics
        """
        if output_dir is None:
            output_dir = input_dir

        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n🚀 Processing concatenated D4D documents")
        print(f"📁 Input directory: {input_dir}")
        print(f"📁 Output directory: {output_dir}")
        print(f"🔍 Pattern: {pattern}\n")

        # Find files to process
        files = list(input_dir.glob(pattern))
        files.sort()  # Process in consistent order

        if not files:
            print(f"❌ No files found matching pattern: {pattern}")
            return {
                'total_files': 0,
                'processed': [],
                'errors': []
            }

        print(f"Found {len(files)} files to process\n")

        results = {
            'total_files': len(files),
            'processed': [],
            'errors': [],
            'start_time': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        # Process each file
        for i, input_file in enumerate(files, 1):
            print(f"[{i}/{len(files)}] {input_file.name}")

            # Extract project name from filename (e.g., AI_READI from AI_READI_d4d.txt)
            project_name = input_file.stem.replace('_d4d', '')

            # Generate output filename
            output_file = output_dir / f"{project_name}_synthesized.yaml"

            # Skip if already exists
            if output_file.exists():
                print(f"   ⏭️  Skipping (already exists): {output_file.name}\n")
                continue

            # Process file
            success, message = await self.process_concatenated_file(
                input_file,
                output_file,
                project_name
            )

            if success:
                results['processed'].append({
                    'input_file': str(input_file),
                    'output_file': str(output_file),
                    'project': project_name
                })
            else:
                results['errors'].append({
                    'file': str(input_file),
                    'error': message
                })

            print()  # Blank line between files

            # Small delay to be respectful to API
            if i < len(files):
                await asyncio.sleep(2)

        # Print summary
        print("=" * 60)
        print("PROCESSING COMPLETE")
        print("=" * 60)
        print(f"✅ Successfully processed: {len(results['processed'])}")
        print(f"❌ Errors: {len(results['errors'])}")
        print(f"📁 Output directory: {output_dir}")

        if results['errors']:
            print("\nErrors:")
            for error in results['errors']:
                print(f"  - {Path(error['file']).name}: {error['error']}")

        return results


async def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Process concatenated D4D documents with D4D agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single concatenated file
  python process_concatenated_d4d.py -i data/concatenated/AI_READI_d4d.txt

  # Process with custom output location
  python process_concatenated_d4d.py -i data/concatenated/AI_READI_d4d.txt -o output/ai_readi.yaml

  # Process all concatenated files in a directory
  python process_concatenated_d4d.py -d data/concatenated

  # Use a different model
  python process_concatenated_d4d.py -i data/concatenated/AI_READI_d4d.txt -m "anthropic:claude-3-opus-20240229"
        """
    )

    parser.add_argument(
        '-i', '--input',
        type=Path,
        help='Input concatenated file to process'
    )

    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output D4D YAML file (default: input_file_synthesized.yaml)'
    )

    parser.add_argument(
        '-d', '--directory',
        type=Path,
        help='Process all files in directory (alternative to -i)'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        help='Output directory when using --directory (default: same as input directory)'
    )

    parser.add_argument(
        '-p', '--pattern',
        default='*_d4d.txt',
        help='Glob pattern for files when using --directory (default: *_d4d.txt)'
    )

    parser.add_argument(
        '-m', '--model',
        default='anthropic:claude-3-5-sonnet-20241022',
        help='Model to use for D4D agent (default: claude-3-5-sonnet-20241022)'
    )

    parser.add_argument(
        '--project',
        help='Project name for context (auto-detected from filename if not specified)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.input and not args.directory:
        parser.error("Either --input or --directory must be specified")

    if args.input and args.directory:
        parser.error("Cannot specify both --input and --directory")

    # Create processor
    processor = ConcatenatedD4DProcessor(model=args.model)

    try:
        if args.input:
            # Process single file
            if not args.input.exists():
                print(f"❌ Error: Input file not found: {args.input}")
                return 1

            success, message = await processor.process_concatenated_file(
                args.input,
                args.output,
                args.project
            )

            return 0 if success else 1

        else:
            # Process directory
            if not args.directory.exists():
                print(f"❌ Error: Input directory not found: {args.directory}")
                return 1

            results = await processor.process_directory(
                args.directory,
                args.output_dir,
                args.pattern
            )

            return 0 if len(results['errors']) == 0 else 1

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
