#!/usr/bin/env python3
"""
Fix failed D4D extractions by regenerating them with improved YAML validation.
"""
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Dict
import yaml
import hashlib
from datetime import datetime
import platform
import sys

# Add aurelian src to path
sys.path.insert(0, str(Path(__file__).parent / "aurelian" / "src"))

from pydantic_ai import Agent
from dataclasses import dataclass


@dataclass
class SimpleD4DConfig:
    """Simple configuration for D4D processing."""
    schema_url: str = "https://raw.githubusercontent.com/monarch-initiative/ontogpt/main/src/ontogpt/templates/data_sheets_schema.yaml"


class FailedExtractionFixer:
    """Fix failed D4D extractions with improved YAML handling."""
    
    def __init__(self):
        # Create GPT-5-based D4D agent with improved prompting
        self.d4d_agent = Agent(
            model="openai:gpt-5",
            deps_type=SimpleD4DConfig,
            system_prompt="""
You are an expert data scientist specializing in extracting metadata from datasets following the "Datasheets for Datasets" schema.

CRITICAL: You must generate ONLY valid YAML. Pay special attention to:
- Proper YAML syntax with correct indentation
- Use quotes around values containing colons, special characters, or line breaks
- Avoid bare colons (:) in text values
- Use proper list formatting with dashes (-)

Your task is to analyze the provided content and extract dataset metadata to generate a complete YAML document that strictly follows the D4D schema.

Generate only valid YAML output without any additional commentary, explanations, or markdown formatting.
The output must be a valid YAML document that starts immediately without code blocks.
""",
            defer_model_check=True,
        )
    
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
                    # Truncate very long content
                    if len(content) > 50000:
                        content = content[:50000] + "\n\n... [Content truncated for length] ..."
                    return content
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            return f"Error reading file {file_path}: {str(e)}"
    
    def generate_extraction_metadata(self, input_file: Path, output_file: Path, 
                                    column: str, config: SimpleD4DConfig) -> Dict:
        """Generate comprehensive metadata for the D4D extraction process."""
        
        # Calculate file hash for provenance
        with open(input_file, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        metadata = {
            'extraction_metadata': {
                'timestamp': datetime.now().isoformat() + 'Z',
                'extraction_id': hashlib.sha256(f"{input_file.name}{datetime.now().isoformat()}".encode()).hexdigest()[:12],
                'extraction_type': 'failed_extraction_retry',
            },
            'input_document': {
                'filename': input_file.name,
                'relative_path': str(input_file.relative_to(Path.cwd())) if input_file.is_relative_to(Path.cwd()) else input_file.name,
                'format': input_file.suffix[1:] if input_file.suffix else 'unknown',
                'size_bytes': input_file.stat().st_size,
                'sha256_hash': file_hash,
                'project_column': column,
            },
            'output_document': {
                'filename': output_file.name,
                'relative_path': str(output_file.relative_to(Path.cwd())) if output_file.is_relative_to(Path.cwd()) else output_file.name,
                'format': 'yaml',
            },
            'datasheets_schema': {
                'version': '1.0.0',
                'url': config.schema_url,
                'retrieved_at': datetime.now().isoformat() + 'Z',
            },
            'd4d_agent': {
                'version': '1.0.0',
                'implementation': 'pydantic_ai',
                'wrapper': 'fix_failed_extractions.py',
                'wrapper_version': '1.0.0',
            },
            'llm_model': {
                'provider': 'openai',
                'model_name': 'openai:gpt-5',
                'model_version': 'gpt-5',
                'temperature': None,
                'max_tokens': None,
            },
            'processing_environment': {
                'platform': platform.system(),
                'python_version': sys.version.split()[0],
                'processor_architecture': platform.machine(),
            },
            'reproducibility': {
                'command': 'python fix_failed_extractions.py',
                'environment_variables': {
                    'OPENAI_API_KEY': 'required' if os.getenv('OPENAI_API_KEY') else 'not_set',
                },
                'notes': 'Retry of failed extraction with improved YAML validation',
            },
        }
        
        return metadata
    
    async def process_single_file(self, input_file: Path, output_file: Path, 
                                 column: str) -> bool:
        """Process a single failed file."""
        try:
            print(f"🔄 Retrying: {input_file.name}")
            
            # Read file content
            content = self.read_file_content(input_file)
            
            if len(content) < 50:
                print(f"❌ Content too short: {input_file.name}")
                return False
            
            # Prepare improved prompt for D4D agent
            prompt = f"""
Extract dataset metadata following the D4D schema from this content.

Source: {input_file.name}
Project: {column}

Content:
{content}

Generate a valid D4D YAML document. Be extra careful with YAML syntax:
- Quote any text values containing colons
- Use proper indentation
- Follow YAML list formatting
- Ensure all fields are properly nested
"""
            
            # Configure D4D agent
            config = SimpleD4DConfig()
            
            # Run the agent
            result = await self.d4d_agent.run(prompt, deps=config)
            
            # Extract YAML from result
            yaml_content = result.output.strip()
            
            # Clean up the output
            if yaml_content.startswith('```yaml'):
                yaml_content = yaml_content[7:]
            if yaml_content.startswith('```'):
                yaml_content = yaml_content[3:]
            if yaml_content.endswith('```'):
                yaml_content = yaml_content[:-3]
            yaml_content = yaml_content.strip()
            
            # Validate YAML with multiple attempts
            for attempt in range(3):
                try:
                    parsed_yaml = yaml.safe_load(yaml_content)
                    if isinstance(parsed_yaml, dict):
                        break
                    else:
                        raise yaml.YAMLError("Generated content is not a valid YAML document")
                except yaml.YAMLError as e:
                    print(f"⚠️  YAML validation failed (attempt {attempt + 1}): {e}")
                    if attempt == 2:  # Last attempt
                        print(f"❌ Failed to generate valid YAML after 3 attempts")
                        return False
                    
                    # Retry with even more specific prompt
                    prompt = f"""
You must generate ONLY valid YAML for this dataset:

Source: {input_file.name}
Project: {column}

Content: {content[:1000]}...

CRITICAL YAML REQUIREMENTS:
- Use quotes around ALL string values that contain colons, commas, or special characters
- Proper indentation with spaces only
- No bare colons in text
- Valid YAML structure

Generate valid D4D YAML:
"""
                    result = await self.d4d_agent.run(prompt, deps=config)
                    yaml_content = result.output.strip()
                    
                    # Clean again
                    if yaml_content.startswith('```yaml'):
                        yaml_content = yaml_content[7:]
                    if yaml_content.startswith('```'):
                        yaml_content = yaml_content[3:]
                    if yaml_content.endswith('```'):
                        yaml_content = yaml_content[:-3]
                    yaml_content = yaml_content.strip()
            
            # Add header comment
            header = f"""# D4D Metadata extracted from: {input_file.name}
# Column: {column}
# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')} (Retry)
# Status: Fixed failed extraction

"""
            
            # Save YAML file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(header + yaml_content)
            
            # Generate and save metadata
            metadata_filename = output_file.stem + '_metadata.yaml'
            metadata_output_path = output_file.parent / metadata_filename
            metadata_content = self.generate_extraction_metadata(
                input_file, output_file, column, config
            )
            
            with open(metadata_output_path, 'w', encoding='utf-8') as f:
                yaml.dump(metadata_content, f, default_flow_style=False, sort_keys=False, width=120)
            
            print(f"✅ Generated: {output_file.name}")
            print(f"📋 Metadata: {metadata_output_path.name}")
            return True
            
        except Exception as e:
            print(f"❌ Error processing {input_file.name}: {e}")
            return False


async def main():
    """Fix the two failed extractions."""
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        return
    
    fixer = FailedExtractionFixer()
    
    # Define the failed files to fix
    failed_files = [
        {
            'input': Path('../downloads_by_column/AI_READI/fairhub_row13.json'),
            'output': Path('../data/extracted_by_column/AI_READI/fairhub_d4d.yaml'),
            'column': 'AI_READI'
        },
        {
            'input': Path('../downloads_by_column/VOICE/physionet_b2ai-voice_1.1_row14.txt'),
            'output': Path('../data/extracted_by_column/VOICE/physionet_b2ai-voice_1.1_d4d.yaml'),
            'column': 'VOICE'
        }
    ]
    
    print("🚀 Fixing failed D4D extractions...")
    
    success_count = 0
    for file_info in failed_files:
        input_file = file_info['input']
        output_file = file_info['output']
        column = file_info['column']
        
        # Create output directory
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Process the file
        if await fixer.process_single_file(input_file, output_file, column):
            success_count += 1
    
    print(f"\n📊 Summary: {success_count}/{len(failed_files)} files fixed successfully")


if __name__ == "__main__":
    asyncio.run(main())