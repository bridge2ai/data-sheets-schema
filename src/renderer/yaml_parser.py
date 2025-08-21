#!/usr/bin/env python3
"""
YAML parser for docx files.

This module provides functions to extract and parse YAML-formatted
content from docx files.
"""

import re
import yaml
from typing import Dict, Any, List, Optional, Tuple


def extract_yaml_from_text(text: str) -> Dict[str, Any]:
    """
    Extract and parse YAML-like content from text.
    
    Args:
        text: Text content that might contain YAML-formatted data
        
    Returns:
        Dict containing parsed YAML content
    """
    # Clean up the text
    lines = text.split('\n')
    cleaned_lines = []
    
    # Process lines to handle indentation and structure
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        
        # Add line
        cleaned_lines.append(line)
    
    # Join back into text and parse
    cleaned_text = '\n'.join(cleaned_lines)
    
    try:
        # Try to parse as YAML
        yaml_data = yaml.safe_load(cleaned_text)
        if isinstance(yaml_data, dict):
            return yaml_data
    except Exception:
        pass
    
    # If the above failed, try a more manual approach
    return parse_yaml_structure(cleaned_lines)


def parse_yaml_structure(lines: List[str]) -> Dict[str, Any]:
    """
    Parse YAML-like structure manually from lines.
    
    Args:
        lines: List of text lines to parse
        
    Returns:
        Dict containing parsed content
    """
    result = {}
    current_key = None
    current_indent = 0
    list_context = {}  # key -> indent level
    indentation_map = {}  # indent level -> parent key
    parent_map = {}  # key -> parent key
    block_text_map = {}  # key -> (is_collecting, indent_level, collected_text)
    
    # Find where the YAML-like content starts, usually after "Dataset:"
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip() == "Dataset:":
            start_idx = i + 1
            break
    
    for i in range(start_idx, len(lines)):
        line = lines[i]
        if not line.strip():  # Skip empty lines
            continue
        
        # Calculate indentation
        indent = len(line) - len(line.lstrip())
        content = line.strip()
        
        # Handle block text markers (>)
        if content.endswith('>'):
            key = content[:-1].strip()
            if ':' in key:
                key, _ = key.split(':', 1)
                key = key.strip()
                block_text_map[key] = (True, indent, [])
                current_key = key
                continue
        
        # Process block text
        if current_key in block_text_map and block_text_map[current_key][0]:
            expected_indent = block_text_map[current_key][1] + 2  # Expect additional indent
            if indent >= expected_indent:
                # Still collecting block text
                block_text_map[current_key][2].append(line.strip())
                continue
            else:
                # End of block text
                result[current_key] = '\n'.join(block_text_map[current_key][2])
                block_text_map[current_key] = (False, 0, [])
        
        # Check if this is a list item
        if content.startswith('- '):
            value = content[2:].strip()
            
            # If this is a nested structure like "- key: value"
            if ':' in value and not value.endswith(':'):
                key, nested_value = value.split(':', 1)
                key = key.strip()
                nested_value = nested_value.strip()
                
                # Special handling for "- key: value" list items
                if current_key:
                    if current_key not in result:
                        result[current_key] = []
                    
                    # Handle list of dicts
                    if isinstance(result[current_key], list):
                        # Check if we need to add a new dict or update the last one
                        if not result[current_key] or not isinstance(result[current_key][-1], dict):
                            result[current_key].append({})
                        
                        result[current_key][-1][key] = nested_value
                
            else:
                # Regular list item
                if indent in indentation_map:
                    parent_key = indentation_map[indent]
                    if parent_key not in result:
                        result[parent_key] = []
                    
                    if isinstance(result[parent_key], list):
                        result[parent_key].append(value)
                else:
                    # This is a top-level list item without a clear parent
                    result.setdefault('items', []).append(value)
            
            continue
        
        # Handle key-value pair
        if ':' in content and not content.endswith(':'):
            key, value = content.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            # Update indentation map
            indentation_map[indent] = key
            
            if value:  # Direct key-value
                result[key] = value
            else:  # Key with nested values to follow
                result[key] = {}
                current_key = key
                current_indent = indent
        elif content.endswith(':'):  # Section marker
            key = content[:-1].strip()
            indentation_map[indent] = key
            result[key] = {}
            current_key = key
            current_indent = indent
    
    # Process any remaining block text
    for key, (is_collecting, _, text_lines) in block_text_map.items():
        if is_collecting and text_lines:
            result[key] = '\n'.join(text_lines)
    
    return result


def convert_yaml_to_structured_text(yaml_data: Dict[str, Any], indent: int = 0) -> str:
    """
    Convert YAML data to structured text representation.
    
    Args:
        yaml_data: Parsed YAML data
        indent: Current indentation level
        
    Returns:
        Formatted text representation
    """
    lines = []
    indent_str = ' ' * indent
    
    for key, value in yaml_data.items():
        if isinstance(value, dict):
            lines.append(f"{indent_str}{key}:")
            lines.append(convert_yaml_to_structured_text(value, indent + 2))
        elif isinstance(value, list):
            lines.append(f"{indent_str}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{indent_str}  - ")
                    lines.append(convert_yaml_to_structured_text(item, indent + 4))
                else:
                    lines.append(f"{indent_str}  - {item}")
        else:
            if '\n' in str(value):
                lines.append(f"{indent_str}{key}: >")
                for line in str(value).split('\n'):
                    lines.append(f"{indent_str}  {line}")
            else:
                lines.append(f"{indent_str}{key}: {value}")
    
    return '\n'.join(lines)


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
    indent_class = f"indent-{str(indent)}"  # Convert to string explicitly
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
                    next_indent_class = f"indent-{str(indent + 1)}"  # Convert to string explicitly
                    html.append(f'<div class="{next_indent_class}">{line_prefix}&nbsp;&nbsp;- </div>')
                    html.append(format_yaml_for_html(item, indent + 2))
                else:
                    # Simple list item
                    next_indent_class = f"indent-{str(indent + 1)}"  # Convert to string explicitly
                    html.append(f'<div class="{next_indent_class}">{line_prefix}&nbsp;&nbsp;- <span class="value">{item}</span></div>')
        else:
            # Simple key-value
            if value is None:
                value = ""
            elif isinstance(value, str) and "\n" in value:
                # Multiline string
                html.append(f'<div class="{indent_class}">{line_prefix}{key_html}: <span class="multiline">></span></div>')
                next_indent_class = f"indent-{str(indent + 1)}"  # Convert to string explicitly
                for line in value.split("\n"):
                    html.append(f'<div class="{next_indent_class}">{line_prefix}&nbsp;&nbsp;<span class="value">{line}</span></div>')
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
    x_indent = float(x_pos) + (int(indent) * int(indent_size))
    
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
                    new_x_indent = float(x_indent) + float(indent_size)
                    pdf_renderer.text(new_x_indent, y_pos, "-")
                    y_pos += 5
                    y_pos = format_yaml_for_pdf(item, pdf_renderer, x_pos, y_pos, indent + 2, max_width)
                else:
                    # Simple list item
                    pdf_renderer.set_font("Arial", "", 10)
                    
                    # Handle text wrapping for long items
                    item_text = f"- {item}"
                    if int(len(item_text)) * 2 > int(max_width):  # Approximate character width
                        # TODO: Implement proper text wrapping for PDF
                        chunk_size = max_width // 2
                        lines = [item_text[i:i+chunk_size] for i in range(0, len(item_text), chunk_size)]
                        for i, line in enumerate(lines):
                            new_x_indent = float(x_indent) + float(indent_size)
                            if i > 0:
                                new_x_indent += 2.0  # Extra indent for wrapped lines
                            pdf_renderer.text(new_x_indent, y_pos, line)
                            y_pos += 5
                    else:
                        new_x_indent = float(x_indent) + float(indent_size)
                        pdf_renderer.text(new_x_indent, y_pos, item_text)
                        y_pos += 5
        else:
            # Simple key-value
            pdf_renderer.text(x_indent, y_pos, f"{key}:")
            
            # Set value font (regular)
            pdf_renderer.set_font("Arial", "", 10)
            
            # Handle multiline strings and long values
            if value is None:
                new_x_pos = float(x_indent) + float(len(str(key))) + 3.0
                pdf_renderer.text(new_x_pos, y_pos, "")
                y_pos += 5
            elif isinstance(value, str) and "\n" in value:
                # Multiline string
                new_x_pos = float(x_indent) + float(len(str(key))) + 3.0
                pdf_renderer.text(new_x_pos, y_pos, ">")
                y_pos += 5
                for line in value.split("\n"):
                    new_x_indent = float(x_indent) + float(indent_size)
                    pdf_renderer.text(new_x_indent, y_pos, line)
                    y_pos += 5
            else:
                # Simple value, handle long lines
                value_text = str(value)
                avail_width = int(max_width) - (int(x_indent) + int(len(str(key))) + 5)
                if int(len(value_text)) * 2 > avail_width:
                    new_x_pos = float(x_indent) + float(len(str(key))) + 3.0
                    pdf_renderer.text(new_x_pos, y_pos, value_text[:40] + "...")
                else:
                    new_x_pos = float(x_indent) + float(len(str(key))) + 3.0
                    pdf_renderer.text(new_x_pos, y_pos, str(value_text))
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


if __name__ == "__main__":
    # Example usage
    test_text = """Dataset:
  id: doi:10.18130/V3/B35XWX
  title: "Cell Maps for Artificial Intelligence - March 2025 Data Release (Beta)"
  version: "1.4"
  description: >
    This dataset is the March 2025 Data Release of Cell Maps for AI.
    It contains multiple types of data.
  keywords:
    - label: "AI"
      ontology_label: "artificial intelligence"
    - label: "machine learning"
"""
    
    result = extract_yaml_from_text(test_text)
    print(yaml.dump(result, default_flow_style=False))