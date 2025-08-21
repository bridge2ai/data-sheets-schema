#!/usr/bin/env python3
"""
Batch processing script for converting DOCX files to structured templates.

This script processes all DOCX files in a specified directory, converting them
to YAML and JSON templates, and optionally rendering them as HTML, PDF, etc.
"""

import os
import sys
import argparse
from pathlib import Path

# Set default encoding to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from .converters import DocxConverter
from .template_renderer import TemplateRenderer


def main():
    """Main entry point for batch processing."""
    parser = argparse.ArgumentParser(
        description='Batch process DOCX files to structured templates.'
    )
    
    # Input options
    parser.add_argument(
        'input_dir',
        help='Directory containing DOCX files'
    )
    
    # Output options
    parser.add_argument(
        '--output-dir', '-o',
        help='Output directory for generated files'
    )
    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Recursively process DOCX files in subdirectories'
    )
    
    # Format options
    parser.add_argument(
        '--yaml', '-y',
        action='store_true',
        help='Generate YAML templates'
    )
    parser.add_argument(
        '--json', '-j',
        action='store_true',
        help='Generate JSON templates'
    )
    parser.add_argument(
        '--html', '-H',
        action='store_true',
        help='Render HTML files'
    )
    parser.add_argument(
        '--pdf', '-P',
        action='store_true',
        help='Render PDF files'
    )
    parser.add_argument(
        '--markdown', '-M',
        action='store_true',
        help='Render Markdown files'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no format specified, default to YAML
    if not (args.yaml or args.json or args.html or args.pdf or args.markdown):
        args.yaml = True
    
    # Initialize converter and renderer
    docx_converter = DocxConverter(output_dir=args.output_dir)
    renderer = TemplateRenderer(output_dir=args.output_dir)
    
    # Process DOCX files
    yaml_paths = []
    json_paths = []
    
    # First generate YAML templates
    if args.yaml:
        print(f"Processing DOCX files in {args.input_dir} to YAML...")
        yaml_paths = docx_converter.process_docx_directory(
            args.input_dir, 
            output_format='yaml',
            recursive=args.recursive
        )
        print(f"Generated {len(yaml_paths)} YAML templates.")
    
    # Then generate JSON templates
    if args.json:
        print(f"Processing DOCX files in {args.input_dir} to JSON...")
        json_paths = docx_converter.process_docx_directory(
            args.input_dir, 
            output_format='json',
            recursive=args.recursive
        )
        print(f"Generated {len(json_paths)} JSON templates.")
    
    # Render templates
    if args.html or args.pdf or args.markdown:
        # Combine paths
        template_paths = yaml_paths + json_paths
        if not template_paths:
            # If no templates were generated, generate YAML templates first
            yaml_paths = docx_converter.process_docx_directory(
                args.input_dir, 
                output_format='yaml',
                recursive=args.recursive
            )
            template_paths = yaml_paths
        
        # Process each template
        for template_path in template_paths:
            template_path = Path(template_path)
            print(f"Rendering template: {template_path}")
            
            # Determine template type
            if template_path.suffix.lower() == '.yaml' or template_path.suffix.lower() == '.yml':
                from .converters.yaml_template_converter import TemplateConverter
                converter = TemplateConverter()
                template_data = converter.load_yaml_template(template_path)
            elif template_path.suffix.lower() == '.json':
                from .converters.yaml_template_converter import TemplateConverter
                converter = TemplateConverter()
                template_data = converter.load_json_template(template_path)
            else:
                print(f"Unsupported template format: {template_path.suffix}")
                continue
            
            # Create output path prefix
            output_prefix = Path(args.output_dir) if args.output_dir else Path(template_path).parent
            output_prefix = output_prefix / template_path.stem
            
            # Render HTML
            if args.html:
                html_path = f"{output_prefix}.html"
                renderer.render_html(html_path, template_data)
                print(f"Generated HTML: {html_path}")
            
            # Render PDF
            if args.pdf:
                pdf_path = f"{output_prefix}.pdf"
                renderer.render_pdf(pdf_path, template_data)
                print(f"Generated PDF: {pdf_path}")
            
            # Render Markdown
            if args.markdown:
                md_path = f"{output_prefix}.md"
                renderer.render_markdown(md_path, template_data)
                print(f"Generated Markdown: {md_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())