#!/usr/bin/env python3
"""
Standalone D4D Agent Wrapper - Processes downloaded files and generates D4D YAML metadata
using the Anthropic Claude API directly without aurelian dependencies.
"""
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple
import argparse
import yaml
import requests
from pydantic_ai import Agent
from dataclasses import dataclass


@dataclass
class SimpleD4DConfig:
    """Simple configuration for D4D processing."""
    schema_url: str = "https://raw.githubusercontent.com/monarch-initiative/ontogpt/main/src/ontogpt/templates/data_sheets_schema.yaml"


class StandaloneD4DWrapper:
    """Standalone wrapper to process files with D4D agent and generate YAML metadata."""
    
    def __init__(self, input_dir: str = "downloads_by_column", output_dir: str = "data/extracted_by_column"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check for API key
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
            print("Please set your Anthropic API key:")
            print("export ANTHROPIC_API_KEY='your-api-key-here'")
            raise ValueError("Missing ANTHROPIC_API_KEY")
        
        # Load D4D schema
        self.schema = self.load_d4d_schema()
        
        # Create Claude-based D4D agent
        self.d4d_agent = Agent(
            model="anthropic:claude-3-5-sonnet-20241022",
            deps_type=SimpleD4DConfig,
            system_prompt=f"""
You are an expert data scientist specializing in extracting metadata from datasets following the "Datasheets for Datasets" schema.

Below is the complete datasheets for datasets schema:

{self.schema}

Your task is to analyze the provided content (which may be HTML, text, PDF, or JSON metadata) and extract all relevant dataset metadata to generate a complete YAML document that strictly follows the D4D schema above.

Focus on extracting:
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

Generate only valid YAML output without any additional commentary. Ensure all required fields are populated where information is available. If specific information is not available in the source, omit those fields rather than making assumptions.

The output must be a valid YAML document that starts with the dataset metadata, not wrapped in code blocks or explanations.
""",
            defer_model_check=True,
        )
    
    def load_d4d_schema(self) -> str:
        """Load the D4D schema from GitHub."""
        try:
            config = SimpleD4DConfig()
            response = requests.get(config.schema_url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"❌ Error loading D4D schema: {e}")
            raise
    
    def read_file_content(self, file_path: Path) -> str:
        """Read content from various file types."""
        try:
            if file_path.suffix == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return json.dumps(data, indent=2)
            elif file_path.suffix in ['.html', '.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Truncate very long content to avoid token limits
                    if len(content) > 50000:
                        content = content[:50000] + "\n\n... [Content truncated for length] ..."
                    return content
            elif file_path.suffix == '.pdf':
                return f"PDF file: {file_path.name}. This is a PDF document that should be analyzed for dataset information. Note: PDF content extraction not available in this context, please analyze based on the filename and any other available metadata."
            else:
                # Try to read as text
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            return f"Error reading file {file_path}: {str(e)}"
    
    def should_process_file(self, file_path: Path) -> bool:
        """Determine if a file should be processed by the D4D agent."""
        # Skip report files and summaries
        skip_patterns = [
            'organized_extraction_report',
            'organized_extraction_summary', 
            'extraction_report',
            'extraction_summary',
        ]
        
        filename = file_path.name.lower()
        return not any(pattern in filename for pattern in skip_patterns)
    
    async def process_file_with_agent(self, file_path: Path, column: str, output_path: Path) -> Tuple[bool, str]:
        """Process a single file with the D4D agent."""
        try:
            print(f"    📄 Processing: {file_path.name}")
            
            # Read file content
            content = self.read_file_content(file_path)
            
            if len(content) < 50:  # Skip very short files
                return False, "Content too short"
            
            # Prepare prompt for D4D agent
            prompt = f"""
Please analyze the following content and extract dataset metadata following the D4D schema.

Source file: {file_path.name}
Content type: {file_path.suffix}
Project category: {column}

Content to analyze:
{content}

Generate a complete D4D YAML document based on this content. Include as much relevant information as you can extract from the source material.
"""
            
            # Configure D4D agent
            config = SimpleD4DConfig()
            
            # Run the agent
            result = await self.d4d_agent.run(prompt, deps=config)
            
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
                    return False, "Generated content is not a valid YAML document"
            except yaml.YAMLError as e:
                return False, f"Invalid YAML generated: {e}"
            
            # Save YAML file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            
            print(f"      ✅ Generated: {output_path.name}")
            return True, "Success"
            
        except Exception as e:
            error_msg = str(e)
            print(f"      ❌ Failed: {error_msg}")
            return False, error_msg
    
    async def process_column(self, column_dir: Path) -> Dict:
        """Process all files in a column directory."""
        column_name = column_dir.name
        print(f"\n📂 Processing column: {column_name}")
        
        # Create output directory for this column
        column_output_dir = self.output_dir / column_name
        column_output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            'column': column_name,
            'processed': [],
            'skipped': [],
            'errors': []
        }
        
        # Get all files to process
        files_to_process = [f for f in column_dir.iterdir() 
                          if f.is_file() and self.should_process_file(f)]
        
        print(f"   Found {len(files_to_process)} files to process")
        
        # Process each file
        for file_path in files_to_process:
            # Generate output filename
            base_name = file_path.stem
            
            # Clean up filename - remove row suffixes for cleaner names
            if '_row' in base_name:
                base_name = base_name.split('_row')[0]
            
            output_filename = f"{base_name}_d4d.yaml"
            output_path = column_output_dir / output_filename
            
            # Skip if already exists
            if output_path.exists():
                print(f"    ⏭️  Skipping (exists): {file_path.name}")
                results['skipped'].append({
                    'file': str(file_path),
                    'reason': 'Already exists'
                })
                continue
            
            # Process with agent
            success, message = await self.process_file_with_agent(file_path, column_name, output_path)
            
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
    
    async def process_all_columns(self) -> Dict:
        """Process all column directories."""
        if not self.input_dir.exists():
            print(f"❌ Input directory not found: {self.input_dir}")
            return {}
        
        print(f"🚀 D4D Agent Wrapper - Processing files from: {self.input_dir}")
        print(f"📁 Output directory: {self.output_dir}")
        
        all_results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'input_dir': str(self.input_dir),
            'output_dir': str(self.output_dir),
            'columns': [],
            'summary': {
                'total_processed': 0,
                'total_errors': 0,
                'total_skipped': 0
            }
        }
        
        # Get all column directories
        column_dirs = [d for d in self.input_dir.iterdir() if d.is_dir()]
        
        if not column_dirs:
            print("❌ No column directories found")
            return all_results
        
        print(f"📂 Found {len(column_dirs)} columns to process")
        
        # Process each column
        for column_dir in sorted(column_dirs):
            results = await self.process_column(column_dir)
            all_results['columns'].append(results)
            
            # Update summary
            all_results['summary']['total_processed'] += len(results['processed'])
            all_results['summary']['total_errors'] += len(results['errors'])
            all_results['summary']['total_skipped'] += len(results['skipped'])
        
        # Save summary
        summary_file = self.output_dir / "d4d_processing_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        # Create markdown report
        self.create_report(all_results)
        
        return all_results
    
    def create_report(self, results: Dict):
        """Create a human-readable report."""
        report_file = self.output_dir / "d4d_processing_report.md"
        
        with open(report_file, 'w') as f:
            f.write("# D4D Agent Processing Report\n\n")
            f.write(f"Generated: {results['timestamp']}\n\n")
            
            # Summary
            f.write("## Summary\n\n")
            summary = results['summary']
            f.write(f"- **Files processed**: {summary['total_processed']}\n")
            f.write(f"- **Errors**: {summary['total_errors']}\n")
            f.write(f"- **Skipped**: {summary['total_skipped']}\n")
            
            # By column
            f.write("\n## Results by Column\n\n")
            
            for column_result in results['columns']:
                column = column_result['column']
                f.write(f"### {column}\n\n")
                
                # Processed files
                if column_result['processed']:
                    f.write("#### Successfully Processed\n\n")
                    for item in column_result['processed']:
                        input_file = Path(item['input_file']).name
                        output_file = Path(item['output_file']).name
                        f.write(f"- ✅ `{input_file}` → `{output_file}`\n")
                    f.write("\n")
                
                # Errors
                if column_result['errors']:
                    f.write("#### Errors\n\n")
                    for error in column_result['errors']:
                        file_name = Path(error['file']).name
                        f.write(f"- ❌ `{file_name}`: {error['error']}\n")
                    f.write("\n")
                
                # Skipped
                if column_result['skipped']:
                    f.write("#### Skipped\n\n")
                    for skipped in column_result['skipped']:
                        file_name = Path(skipped['file']).name
                        f.write(f"- ⏭️  `{file_name}`: {skipped['reason']}\n")
                    f.write("\n")
        
        print(f"\n📊 Report saved: {report_file}")


async def main():
    parser = argparse.ArgumentParser(
        description="Process downloaded files with D4D agent to generate YAML metadata",
        epilog="Example: python standalone_d4d_wrapper.py -i downloads_by_column -o data/extracted_by_column"
    )
    parser.add_argument("-i", "--input", default="downloads_by_column", 
                       help="Input directory with column-organized downloads")
    parser.add_argument("-o", "--output", default="data/extracted_by_column",
                       help="Output directory for D4D YAML files")
    parser.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    
    args = parser.parse_args()
    
    # Set API key if provided
    if args.api_key:
        os.environ["ANTHROPIC_API_KEY"] = args.api_key
    
    # Create and run wrapper
    try:
        wrapper = StandaloneD4DWrapper(args.input, args.output)
        results = await wrapper.process_all_columns()
        
        # Print final summary
        print("\n" + "="*60)
        print("D4D PROCESSING COMPLETE")
        print("="*60)
        summary = results['summary']
        print(f"✅ Files processed: {summary['total_processed']}")
        print(f"❌ Errors: {summary['total_errors']}")
        print(f"⏭️  Skipped: {summary['total_skipped']}")
        print(f"\n📁 Output directory: {Path(args.output).absolute()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)