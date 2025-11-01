#!/usr/bin/env python3
"""
YAML rendering utilities for PDF and HTML documents.

This module provides functions to format YAML content for PDF and HTML documents.
"""

import yaml
from typing import Dict, Any, List, Optional


def format_yaml_for_html(data: Dict[str, Any], indent: int = 0) -> str:
    """
    Format YAML data as HTML with proper indentation and styling.
    
    Args:
        data: The YAML data to format
        indent: The current indentation level
        
    Returns:
        Formatted HTML representation of the YAML data
    """
    html = []
    indent_class = f"indent-{indent}"
    line_prefix = "&nbsp;" * (indent * 2)
    
    for key, value in data.items():
        # Format the key
        key_html = f'<span class="key">{key}</span>'
        
        if isinstance(value, dict):
            # Nested dictionary
            html.append(f'<div class="{indent_class}">{line_prefix}{key_html}:</div>')
            html.append(format_yaml_for_html(value, indent + 1))
        elif isinstance(value, list):
            # List value
            html.append(f'<div class="{indent_class}">{line_prefix}{key_html}:</div>')
            
            for item in value:
                if isinstance(item, dict):
                    # List of dictionaries
                    html.append(f'<div class="{indent_class + 1}">{line_prefix}&nbsp;&nbsp;- </div>')
                    html.append(format_yaml_for_html(item, indent + 2))
                else:
                    # Simple list item
                    html.append(f'<div class="{indent_class + 1}">{line_prefix}&nbsp;&nbsp;- <span class="value">{item}</span></div>')
        else:
            # Simple key-value - convert None to empty string for HTML
            if value is None:
                value = ""
            elif isinstance(value, str) and "\n" in value:
                # Multiline string
                html.append(f'<div class="{indent_class}">{line_prefix}{key_html}: <span class="multiline">></span></div>')
                for line in value.split("\n"):
                    html.append(f'<div class="{indent_class + 1}">{line_prefix}&nbsp;&nbsp;<span class="value">{line}</span></div>')
                continue
                
            html.append(f'<div class="{indent_class}">{line_prefix}{key_html}: <span class="value">{value}</span></div>')
    
    return "\n".join(html)


def format_yaml_for_pdf(data: Dict[str, Any], pdf_renderer, x_pos: float, y_pos: float, 
                       indent: int = 0, max_width: int = 180) -> float:
    """
    Format YAML data for PDF with proper indentation and styling.
    
    Args:
        data: The YAML data to format
        pdf_renderer: The PDF object to render to
        x_pos: The current x position
        y_pos: The current y position
        indent: The current indentation level
        max_width: The maximum width for text
        
    Returns:
        The new y position after rendering
    """
    # Set up indentation
    indent_size = 4
    x_indent = x_pos + (indent * indent_size)
    
    for key, value in data.items():
        # Set key font (bold)
        pdf_renderer.set_font("Arial", "B", 10)
        
        if isinstance(value, dict):
            # Nested dictionary
            pdf_renderer.text(x_indent, y_pos, f"{key}:")
            y_pos += 5
            y_pos = format_yaml_for_pdf(value, pdf_renderer, x_pos, y_pos, indent + 1, max_width)
        elif isinstance(value, list):
            # List value
            pdf_renderer.text(x_indent, y_pos, f"{key}:")
            y_pos += 5
            
            # Process each list item
            for item in value:
                if isinstance(item, dict):
                    # List of dictionaries
                    pdf_renderer.set_font("Arial", "", 10)
                    pdf_renderer.text(x_indent + indent_size, y_pos, "-")
                    y_pos += 5
                    y_pos = format_yaml_for_pdf(item, pdf_renderer, x_pos, y_pos, indent + 2, max_width)
                else:
                    # Simple list item
                    pdf_renderer.set_font("Arial", "", 10)
                    
                    # Handle text wrapping for long items
                    item_text = f"- {item}"
                    if len(item_text) * 2 > max_width:  # Approximate character width
                        # TODO: Implement proper text wrapping for PDF
                        lines = [item_text[i:i+max_width//2] for i in range(0, len(item_text), max_width//2)]
                        for i, line in enumerate(lines):
                            actual_indent = x_indent + indent_size
                            if i > 0:
                                actual_indent += 2  # Extra indent for wrapped lines
                            pdf_renderer.text(actual_indent, y_pos, line)
                            y_pos += 5
                    else:
                        pdf_renderer.text(x_indent + indent_size, y_pos, item_text)
                        y_pos += 5
        else:
            # Simple key-value
            pdf_renderer.text(x_indent, y_pos, f"{key}:")
            
            # Set value font (regular)
            pdf_renderer.set_font("Arial", "", 10)
            
            # Handle multiline strings and long values
            # Convert None to empty string for PDF
            if value is None:
                pdf_renderer.text(x_indent + len(key) + 3, y_pos, "")
                y_pos += 5
            elif isinstance(value, str) and "\n" in value:
                # Multiline string
                pdf_renderer.text(x_indent + len(key) + 3, y_pos, ">")
                y_pos += 5
                for line in value.split("\n"):
                    pdf_renderer.text(x_indent + indent_size, y_pos, line)
                    y_pos += 5
            else:
                # Simple value, handle long lines
                value_text = str(value)
                if len(value_text) * 2 > max_width - (x_indent + len(key) + 5):
                    pdf_renderer.text(x_indent + len(key) + 3, y_pos, value_text[:40] + "...")
                else:
                    pdf_renderer.text(x_indent + len(key) + 3, y_pos, value_text)
                y_pos += 5
    
    return y_pos


def get_yaml_css_styles() -> str:
    """
    Return CSS styles for YAML rendering in HTML.
    
    Returns:
        CSS styles as a string
    """
    return """
        .key { font-weight: bold; color: #2c3e50; }
        .value { color: #333; }
        .multiline { color: #7f8c8d; font-style: italic; }
        [class^="indent-"] { margin: 0; padding: 0; line-height: 1.5; font-family: monospace; white-space: pre; }
        .indent-0 { margin-left: 0; }
        .indent-1 { margin-left: 1em; }
        .indent-2 { margin-left: 2em; }
        .indent-3 { margin-left: 3em; }
        .indent-4 { margin-left: 4em; }
        .indent-5 { margin-left: 5em; }
        .yaml-block { 
            background: #f8f9fa; 
            border: 1px solid #ddd; 
            padding: 15px; 
            border-radius: 4px; 
            margin: 10px 0;
            overflow-x: auto;
        }
    """
    
    
def format_complex_value(value: Any) -> str:
    """
    Format complex YAML values as properly indented YAML.
    
    Args:
        value: The value to format
        
    Returns:
        Formatted YAML string
    """
    if isinstance(value, (dict, list)):
        return yaml.dump(value, default_flow_style=False, sort_keys=False)
    return str(value)