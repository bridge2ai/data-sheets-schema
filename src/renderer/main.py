#!/usr/bin/env python3
"""
Main module for rendering Datasheets for Datasets templates.

This script provides a command-line interface for rendering datasheet templates
in various formats (HTML, PDF, Markdown).
"""

import argparse
import os
import sys
from pathlib import Path

# Set default encoding to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from .template_renderer import TemplateRenderer
from .converters import TemplateConverter, DocxConverter

def main():
    """Main entry point for the renderer."""
    parser = argparse.ArgumentParser(
        description='Render Datasheets for Datasets templates in various formats.'
    )
    
    # Input options
    parser.add_argument(
        '--template', '-t',
        type=str,
        help='Path to template file (YAML or JSON)'
    )
    parser.add_argument(
        '--docx', '-d',
        type=str,
        help='Path to DOCX file or directory containing DOCX files'
    )
    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Recursively process DOCX files in subdirectories'
    )
    
    # Output options
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        help='Output directory for rendered files'
    )
    
    # Format options
    format_group = parser.add_argument_group('format options')
    format_group.add_argument(
        '--html', '-H',
        action='store_true',
        help='Render template as HTML'
    )
    format_group.add_argument(
        '--pdf', '-P',
        action='store_true',
        help='Render template as PDF'
    )
    format_group.add_argument(
        '--markdown', '-M',
        action='store_true',
        help='Render template as Markdown'
    )
    format_group.add_argument(
        '--all', '-A',
        action='store_true',
        help='Render template in all formats'
    )
    
    # Conversion options
    convert_group = parser.add_argument_group('conversion options')
    convert_group.add_argument(
        '--yaml2json',
        action='store_true',
        help='Convert YAML template to JSON'
    )
    convert_group.add_argument(
        '--json2yaml',
        action='store_true',
        help='Convert JSON template to YAML'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no format specified, default to all
    if not (args.html or args.pdf or args.markdown or args.all or 
            args.yaml2json or args.json2yaml):
        args.all = True
    
    # Initialize converter and renderer
    converter = TemplateConverter()
    renderer = TemplateRenderer(output_dir=args.output_dir)
    
    # Handle template file
    template_data = None
    if args.template:
        template_path = Path(args.template)
        if not template_path.exists():
            print(f"Error: Template file not found: {args.template}", file=sys.stderr)
            return 1
        
        if template_path.suffix.lower() == '.yaml' or template_path.suffix.lower() == '.yml':
            template_data = converter.load_yaml_template(template_path)
        elif template_path.suffix.lower() == '.json':
            template_data = converter.load_json_template(template_path)
        else:
            print(f"Error: Unsupported template format: {template_path.suffix}", file=sys.stderr)
            return 1
    
    # Handle conversions
    if args.yaml2json:
        if args.template and (template_path.suffix.lower() == '.yaml' or 
                             template_path.suffix.lower() == '.yml'):
            json_path = template_path.with_suffix('.json')
            if converter.yaml_to_json(template_path, json_path):
                print(f"Converted YAML to JSON: {json_path}")
        else:
            if converter.yaml_to_json():
                print(f"Converted YAML to JSON: {converter.json_template_path}")
    
    if args.json2yaml:
        if args.template and template_path.suffix.lower() == '.json':
            yaml_path = template_path.with_suffix('.yaml')
            if converter.json_to_yaml(template_path, yaml_path):
                print(f"Converted JSON to YAML: {yaml_path}")
        else:
            if converter.json_to_yaml():
                print(f"Converted JSON to YAML: {converter.yaml_template_path}")
    
    # Handle rendering
    render_html = args.html or args.all
    render_pdf = args.pdf or args.all
    render_markdown = args.markdown or args.all
    
    if render_html:
        html_path = renderer.render_html(template_data=template_data)
        if html_path:
            print(f"Rendered HTML: {html_path}")
    
    if render_pdf:
        pdf_path = renderer.render_pdf(template_data=template_data)
        if pdf_path:
            print(f"Rendered PDF: {pdf_path}")
    
    if render_markdown:
        md_path = renderer.render_markdown(template_data=template_data)
        if md_path:
            print(f"Rendered Markdown: {md_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())