#!/usr/bin/env python3
"""
Template renderer for Datasheets schema.

This module provides utilities to render datasheet templates in various output formats
(HTML, PDF, etc.).
"""

import os
import json
import yaml
from pathlib import Path
import logging
from jinja2 import Environment, FileSystemLoader
import markdown
from weasyprint import HTML

from .converters import TemplateConverter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TemplateRenderer:
    """Render datasheet templates in various output formats."""
    
    def __init__(self, template_dir=None, output_dir=None):
        """
        Initialize the renderer with template and output directories.
        
        Args:
            template_dir: Directory containing template files. If None, uses default location.
            output_dir: Directory for output files. If None, uses default location.
        """
        # Set up template converter
        self.converter = TemplateConverter(template_dir)
        
        # Set up directories
        if output_dir is None:
            # Default to output directory relative to this file
            self.output_dir = Path(os.path.dirname(os.path.abspath(__file__))) / '..' / 'output'
        else:
            self.output_dir = Path(output_dir)
            
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Set up Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')),
            autoescape=True
        )
        
    def _create_jinja_template(self, template_name):
        """
        Create a Jinja2 template.
        
        Args:
            template_name: Name of the template file.
            
        Returns:
            jinja2.Template: Jinja2 template object
        """
        try:
            return self.jinja_env.get_template(template_name)
        except Exception as e:
            logger.error(f"Error loading Jinja2 template {template_name}: {e}")
            return None
    
    def render_html(self, output_path=None, template_data=None):
        """
        Render datasheet template as HTML.
        
        Args:
            output_path: Path for output HTML file. If None, uses default.
            template_data: Template data dictionary. If None, loads from default.
            
        Returns:
            str: Path to the generated HTML file or None if error
        """
        if output_path is None:
            output_path = self.output_dir / 'datasheet_template.html'
            
        if template_data is None:
            # Try to load JSON template first, then YAML if JSON not available
            template_data = self.converter.load_json_template()
            if template_data is None:
                template_data = self.converter.load_yaml_template()
                if template_data is None:
                    logger.error("No template data found.")
                    return None
        
        try:
            # Load Jinja2 template
            jinja_template = self._create_jinja_template('datasheet_template.html.j2')
            if jinja_template is None:
                return None
                
            # Render HTML
            html_content = jinja_template.render(
                template=template_data,
                title="Datasheet Template"
            )
            
            # Write HTML to file with utf-8 encoding
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            logger.info(f"Successfully rendered HTML template: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Error rendering HTML template: {e}")
            return None
            
    def render_pdf(self, output_path=None, template_data=None, html_path=None):
        """
        Render datasheet template as PDF.
        
        Args:
            output_path: Path for output PDF file. If None, uses default.
            template_data: Template data dictionary. If None, loads from default.
            html_path: Path to HTML file to convert. If None, generates HTML first.
            
        Returns:
            str: Path to the generated PDF file or None if error
        """
        if output_path is None:
            output_path = self.output_dir / 'datasheet_template.pdf'
            
        try:
            # Generate HTML if not provided
            if html_path is None:
                html_path = self.render_html(template_data=template_data)
                if html_path is None:
                    return None
            
            # Convert HTML to PDF
            HTML(html_path).write_pdf(output_path)
            
            logger.info(f"Successfully rendered PDF template: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Error rendering PDF template: {e}")
            return None
    
    def render_markdown(self, output_path=None, template_data=None):
        """
        Render datasheet template as Markdown.
        
        Args:
            output_path: Path for output Markdown file. If None, uses default.
            template_data: Template data dictionary. If None, loads from default.
            
        Returns:
            str: Path to the generated Markdown file or None if error
        """
        if output_path is None:
            output_path = self.output_dir / 'datasheet_template.md'
            
        if template_data is None:
            # Try to load JSON template first, then YAML if JSON not available
            template_data = self.converter.load_json_template()
            if template_data is None:
                template_data = self.converter.load_yaml_template()
                if template_data is None:
                    logger.error("No template data found.")
                    return None
        
        try:
            # Load Jinja2 template
            jinja_template = self._create_jinja_template('datasheet_template.md.j2')
            if jinja_template is None:
                return None
                
            # Render Markdown
            md_content = jinja_template.render(
                template=template_data,
                title="Datasheet Template"
            )
            
            # Write Markdown to file with utf-8 encoding
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
                
            logger.info(f"Successfully rendered Markdown template: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Error rendering Markdown template: {e}")
            return None

# Example usage
if __name__ == "__main__":
    renderer = TemplateRenderer()
    
    # Render in various formats
    html_path = renderer.render_html()
    pdf_path = renderer.render_pdf(html_path=html_path)
    md_path = renderer.render_markdown()
    
    print(f"HTML: {html_path}")
    print(f"PDF: {pdf_path}")
    print(f"Markdown: {md_path}")