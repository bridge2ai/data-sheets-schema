#!/usr/bin/env python3
"""
Claude Max D4D Processor - Manual workflow for Claude Pro/Max users

This script prepares files for manual processing with Claude Pro/Max by:
1. Validating downloads and relevance 
2. Creating formatted prompts for each file
3. Generating a processing workflow
4. Providing templates for YAML output

Usage:
python claude_max_d4d_processor.py

Then copy-paste the generated prompts into Claude Pro/Max and save responses as YAML files.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
import requests
from dataclasses import dataclass

@dataclass
class ValidationResult:
    success: bool
    message: str
    details: Dict

class ClaudeMaxD4DProcessor:
    """Manual D4D processor for Claude Pro/Max users."""
    
    def __init__(self, input_dir: str = "downloads_by_column", output_dir: str = "data/claude_max_extractions"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Project keywords for content validation
        self.project_keywords = {
            'AI_READI': ['ai-readi', 'aireadi', 'artificial intelligence ready', 'diabetes', 'salutogenic', 'fairhub'],
            'CHORUS': ['chorus', 'clinical health outcomes research', 'informatics', 'aim ahead', 'bridge2ai'],
            'CM4AI': ['cm4ai', 'computational microscopy', 'microscopy', 'imaging', 'cellular', 'dataverse'],
            'VOICE': ['voice', 'b2ai-voice', 'bridge2ai voice', 'vocal', 'speech', 'physionet', 'health data nexus']
        }
        
        # Load D4D schema
        self.schema = self.load_d4d_schema()
        
    def load_d4d_schema(self) -> str:
        """Load the D4D schema from GitHub."""
        try:
            schema_url = "https://raw.githubusercontent.com/monarch-initiative/ontogpt/main/src/ontogpt/templates/data_sheets_schema.yaml"
            response = requests.get(schema_url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"❌ Error loading D4D schema: {e}")
            return "# D4D schema could not be loaded"
    
    def validate_download_success(self, file_path: Path) -> ValidationResult:
        """Validate that a download was successful."""
        try:
            if not file_path.exists():
                return ValidationResult(False, "File does not exist", {})
            
            file_size = file_path.stat().st_size
            if file_size < 100:
                return ValidationResult(False, f"File too small ({file_size} bytes)", {})
            
            # Read and check content
            content = self.read_file_content(file_path)
            if len(content) < 50:
                return ValidationResult(False, "Content too short", {})
            
            # Check for error indicators
            error_indicators = ['error 404', 'not found', 'access denied', 'forbidden', 'internal server error']
            content_lower = content.lower()
            for error in error_indicators:
                if error in content_lower:
                    return ValidationResult(False, f"Content contains error: {error}", {})
            
            return ValidationResult(True, "Download successful", {'file_size': file_size, 'content_length': len(content)})
            
        except Exception as e:
            return ValidationResult(False, f"Error validating file: {str(e)}", {})
    
    def validate_project_relevance(self, file_path: Path, column: str, content: str) -> ValidationResult:
        """Validate project relevance."""
        try:
            keywords = self.project_keywords.get(column, [])
            content_lower = content.lower()
            
            found_keywords = []
            relevance_score = 0
            
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    found_keywords.append(keyword)
                    relevance_score += 1
            
            # URL-based validation
            filename = file_path.name.lower()
            url_relevance = {
                'AI_READI': ['aireadi', 'fairhub'],
                'CHORUS': ['aim-ahead', 'chorus'],
                'CM4AI': ['dataverse', 'cm4ai'],
                'VOICE': ['physionet', 'voice', 'b2ai-voice', 'healthnexus']
            }
            
            url_keywords = url_relevance.get(column, [])
            for url_keyword in url_keywords:
                if url_keyword in filename:
                    relevance_score += 3
            
            is_relevant = relevance_score >= 1
            details = {
                'keywords_found': found_keywords,
                'relevance_score': relevance_score
            }
            
            message = f"Relevance score: {relevance_score}" if is_relevant else "Limited relevance"
            return ValidationResult(is_relevant, message, details)
            
        except Exception as e:
            return ValidationResult(False, f"Error validating relevance: {str(e)}", {})
    
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
                    if len(content) > 20000:
                        content = content[:20000] + "\n\n... [Content truncated for Claude Pro/Max] ..."
                    return content
            elif file_path.suffix == '.pdf':
                return f"PDF file: {file_path.name}. This is a PDF document about datasets - please analyze the filename and context for metadata extraction."
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            return f"Error reading file {file_path}: {str(e)}"
    
    def should_process_file(self, file_path: Path) -> bool:
        """Determine if a file should be processed."""
        skip_patterns = [
            'organized_extraction_report',
            'organized_extraction_summary', 
            'extraction_report',
            'extraction_summary',
        ]
        
        filename = file_path.name.lower()
        return not any(pattern in filename for pattern in skip_patterns)
    
    def select_preferred_file(self, files_list: List[Path]) -> List[Path]:
        """Select preferred file formats: txt > html > pdf for the same base content."""
        file_groups = {}
        
        for file_path in files_list:
            base_name = file_path.stem
            if '_row' in base_name:
                base_name = base_name.split('_row')[0]
            
            if base_name not in file_groups:
                file_groups[base_name] = []
            file_groups[base_name].append(file_path)
        
        preferred_files = []
        format_priority = {'.txt': 1, '.html': 2, '.pdf': 3, '.json': 4}
        
        for base_name, group_files in file_groups.items():
            if len(group_files) == 1:
                preferred_files.extend(group_files)
            else:
                sorted_files = sorted(group_files, key=lambda f: format_priority.get(f.suffix, 999))
                preferred_files.append(sorted_files[0])
        
        return preferred_files
    
    def create_claude_prompt(self, file_path: Path, column: str, content: str, validation_info: Dict) -> str:
        """Create a formatted prompt for Claude Pro/Max."""
        prompt = f"""I need you to analyze the following content and extract dataset metadata following the "Datasheets for Datasets" (D4D) schema.

**Source Information:**
- File: {file_path.name}
- Project Column: {column}
- File Type: {file_path.suffix}
- Validation: {"✅ Relevant" if validation_info.get('relevance_success', False) else "⚠️ Limited relevance"}

**Instructions:**
1. Analyze the content below and extract all available dataset metadata
2. Format the output as valid YAML following the D4D schema structure
3. Include these key sections if information is available:
   - id, name, title, description
   - creators (with names, affiliations, roles)
   - purposes and intended uses
   - instances (data types, counts, representations)
   - collection_mechanisms and timeframes
   - preprocessing_strategies and cleaning
   - distribution_formats and access
   - ethical_reviews and consent
   - license_and_use_terms
   - maintainers and funding

**D4D Schema Reference:**
```yaml
# Key D4D fields (use as template):
id: dataset-identifier
name: Dataset Name
title: "Full Dataset Title"
description: "Detailed description..."

creators:
  - name: "Author Name"
    affiliation: "Institution"
    role: "Principal Investigator"

purposes:
  response: "Why was this dataset created..."

instances:
  representation: "What the data represents"
  data_type: "Type of data (text, images, etc.)"
  counts: 1000

collection_mechanisms:
  description: "How data was collected..."

# Add other relevant sections...
```

**Content to Analyze:**
```
{content[:15000]}{"" if len(content) <= 15000 else "\\n\\n... [Content truncated for length] ..."}
```

**Output Instructions:**
- Provide ONLY valid YAML output (no explanations or markdown formatting)
- Start directly with the YAML content
- If specific information isn't available, omit those fields rather than guessing
- Focus on extracting concrete, factual information from the source material"""

        return prompt
    
    def process_column(self, column_dir: Path) -> Dict:
        """Process all files in a column directory."""
        column_name = column_dir.name
        print(f"\n📂 Processing column: {column_name}")
        
        # Create output directory
        column_output_dir = self.output_dir / column_name
        column_output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            'column': column_name,
            'valid_files': [],
            'invalid_files': [],
            'prompts_created': 0
        }
        
        # Get preferred files
        all_files = [f for f in column_dir.iterdir() if f.is_file() and self.should_process_file(f)]
        files_to_process = self.select_preferred_file(all_files)
        
        print(f"   Found {len(files_to_process)} files to process")
        
        # Process each file
        for i, file_path in enumerate(files_to_process, 1):
            print(f"\n   📋 [{i}/{len(files_to_process)}] Validating: {file_path.name}")
            
            # Validate download
            download_result = self.validate_download_success(file_path)
            if not download_result.success:
                print(f"      Download: ❌ {download_result.message}")
                results['invalid_files'].append({
                    'file': str(file_path),
                    'reason': download_result.message
                })
                continue
            
            print(f"      Download: ✅ {download_result.message}")
            
            # Validate relevance
            content = self.read_file_content(file_path)
            relevance_result = self.validate_project_relevance(file_path, column_name, content)
            
            if relevance_result.success:
                print(f"      Relevance: ✅ {relevance_result.message}")
            else:
                print(f"      Relevance: ⚠️ {relevance_result.message}")
            
            # Create prompt file
            validation_info = {
                'download_success': download_result.success,
                'relevance_success': relevance_result.success,
                'relevance_score': relevance_result.details.get('relevance_score', 0)
            }
            
            prompt = self.create_claude_prompt(file_path, column_name, content, validation_info)
            
            # Save prompt
            base_name = file_path.stem.split('_row')[0] if '_row' in file_path.stem else file_path.stem
            prompt_filename = f"{base_name}_prompt.txt"
            prompt_path = column_output_dir / prompt_filename
            
            with open(prompt_path, 'w', encoding='utf-8') as f:
                f.write(prompt)
            
            # Create template YAML file
            yaml_template = f"""# CLAUDE MAX PROCESSING TEMPLATE
# Source: {file_path.name}
# Column: {column_name}
# Generated: Please replace this with Claude Max output

# Instructions:
# 1. Copy the prompt from {prompt_filename}
# 2. Paste it into Claude Pro/Max
# 3. Copy Claude's YAML response
# 4. Replace this template with the response
# 5. Save this file

# Template structure (remove this section after processing):
id: your-dataset-id
name: Dataset Name
title: "Full Dataset Title"
description: "Dataset description..."

# Add the complete D4D metadata here...
"""
            
            yaml_filename = f"{base_name}_d4d.yaml"
            yaml_path = column_output_dir / yaml_filename
            
            with open(yaml_path, 'w', encoding='utf-8') as f:
                f.write(yaml_template)
            
            results['valid_files'].append({
                'input_file': str(file_path),
                'prompt_file': str(prompt_path),
                'yaml_template': str(yaml_path),
                'validation': validation_info
            })
            results['prompts_created'] += 1
            
            print(f"      ✅ Created: {prompt_filename} & {yaml_filename}")
        
        return results
    
    def process_all_columns(self) -> Dict:
        """Process all column directories."""
        if not self.input_dir.exists():
            print(f"❌ Input directory not found: {self.input_dir}")
            return {}
        
        print(f"🚀 Claude Max D4D Processor - Processing files from: {self.input_dir}")
        print(f"📁 Output directory: {self.output_dir}")
        
        all_results = {
            'input_dir': str(self.input_dir),
            'output_dir': str(self.output_dir),
            'columns': [],
            'total_prompts': 0,
            'total_valid_files': 0,
            'total_invalid_files': 0
        }
        
        # Get column directories
        column_dirs = [d for d in self.input_dir.iterdir() if d.is_dir()]
        
        if not column_dirs:
            print("❌ No column directories found")
            return all_results
        
        print(f"📂 Found {len(column_dirs)} columns to process")
        
        # Process each column
        for column_dir in sorted(column_dirs):
            results = self.process_column(column_dir)
            all_results['columns'].append(results)
            all_results['total_prompts'] += results['prompts_created']
            all_results['total_valid_files'] += len(results['valid_files'])
            all_results['total_invalid_files'] += len(results['invalid_files'])
        
        # Create processing instructions
        self.create_processing_instructions(all_results)
        
        return all_results
    
    def create_processing_instructions(self, results: Dict):
        """Create detailed processing instructions."""
        instructions_file = self.output_dir / "CLAUDE_MAX_PROCESSING_INSTRUCTIONS.md"
        
        with open(instructions_file, 'w') as f:
            f.write("# Claude Pro/Max D4D Processing Instructions\n\n")
            f.write(f"Generated from: {results['input_dir']}\\n")
            f.write(f"Total prompts created: {results['total_prompts']}\\n\\n")
            
            f.write("## Overview\n\n")
            f.write("This folder contains prompts and templates for manual processing with Claude Pro/Max.\\n")
            f.write("Each validated file has been prepared with a formatted prompt and YAML template.\\n\\n")
            
            f.write("## Processing Workflow\n\n")
            f.write("For each file you want to process:\\n\\n")
            f.write("1. **Open the prompt file** (ends with `_prompt.txt`)\\n")
            f.write("2. **Copy the entire prompt** to your clipboard\\n")
            f.write("3. **Paste into Claude Pro/Max** and send the message\\n")
            f.write("4. **Copy Claude's YAML response**\\n")
            f.write("5. **Open the template file** (ends with `_d4d.yaml`)\\n")
            f.write("6. **Replace the template content** with Claude's response\\n")
            f.write("7. **Save the file**\\n\\n")
            
            f.write("## Files by Column\\n\\n")
            
            for column_result in results['columns']:
                column = column_result['column']
                f.write(f"### {column}\\n\\n")
                f.write(f"**Valid files**: {len(column_result['valid_files'])}\\n")
                f.write(f"**Invalid files**: {len(column_result['invalid_files'])}\\n\\n")
                
                if column_result['valid_files']:
                    f.write("#### Files to Process\\n\\n")
                    for i, file_info in enumerate(column_result['valid_files'], 1):
                        input_name = Path(file_info['input_file']).name
                        prompt_name = Path(file_info['prompt_file']).name
                        yaml_name = Path(file_info['yaml_template']).name
                        validation = file_info['validation']
                        
                        f.write(f"{i}. **{input_name}**\\n")
                        f.write(f"   - Prompt: `{column}/{prompt_name}`\\n")
                        f.write(f"   - Template: `{column}/{yaml_name}`\\n")
                        f.write(f"   - Relevance: {'✅' if validation['relevance_success'] else '⚠️'} Score: {validation.get('relevance_score', 0)}\\n\\n")
                
                if column_result['invalid_files']:
                    f.write("#### Skipped Files\\n\\n")
                    for invalid in column_result['invalid_files']:
                        file_name = Path(invalid['file']).name
                        f.write(f"- ❌ `{file_name}`: {invalid['reason']}\\n")
                    f.write("\\n")
            
            f.write("## Tips\\n\\n")
            f.write("- Process files with higher relevance scores first\\n")
            f.write("- Claude Pro/Max may have message limits - break up very long prompts if needed\\n")
            f.write("- Review the generated YAML for completeness and accuracy\\n")
            f.write("- Keep the validation headers in the YAML files for reference\\n")
        
        print(f"\\n📋 Processing instructions saved: {instructions_file}")


def main():
    processor = ClaudeMaxD4DProcessor()
    results = processor.process_all_columns()
    
    print("\\n" + "="*60)
    print("CLAUDE MAX D4D PROCESSING SETUP COMPLETE")
    print("="*60)
    print(f"✅ Prompts created: {results['total_prompts']}")
    print(f"📄 Valid files: {results['total_valid_files']}")
    print(f"❌ Invalid files: {results['total_invalid_files']}")
    print(f"\\n📁 Output directory: {Path(results['output_dir']).absolute()}")
    print("\\n📋 Next steps:")
    print("1. Open CLAUDE_MAX_PROCESSING_INSTRUCTIONS.md")
    print("2. Follow the workflow to process each file with Claude Pro/Max")
    print("3. Replace templates with Claude's YAML responses")

if __name__ == "__main__":
    main()