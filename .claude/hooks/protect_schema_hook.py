#!/usr/bin/env python3
"""
Protected Files Hook

PreToolUse hook that warns about editing auto-generated files.
Does not block writes (warn only mode).

Protected paths:
- src/data_sheets_schema/datamodel/ - Auto-generated Python
- src/data_sheets_schema/schema/data_sheets_schema_all.yaml - Merged schema
- project/ - Generated artifacts (JSON Schema, OWL, etc.)
"""

import json
import sys
from pathlib import Path


# Files and directories that should not be manually edited
PROTECTED_PATTERNS = [
    "src/data_sheets_schema/datamodel/",
    "src/data_sheets_schema/schema/data_sheets_schema_all.yaml",
    "project/jsonschema/",
    "project/owl/",
    "project/jsonld/",
    "project/shacl/",
    "project/graphql/",
    "project/excel/",
]

# Warning messages for different protected paths
WARNINGS = {
    "datamodel": (
        "This is an auto-generated Python datamodel. "
        "Edit the schema YAML files instead and run 'make gen-project'."
    ),
    "data_sheets_schema_all.yaml": (
        "This is the auto-generated merged schema. "
        "Edit the source modules in src/data_sheets_schema/schema/ and run 'make full-schema'."
    ),
    "project": (
        "This is an auto-generated artifact. "
        "Edit the schema YAML files and run 'make gen-project' to regenerate."
    ),
}


def get_tool_info():
    """Parse tool use information from stdin."""
    try:
        input_data = sys.stdin.read()
        if not input_data:
            return None
        return json.loads(input_data)
    except json.JSONDecodeError:
        return None


def is_protected_path(file_path: str) -> tuple[bool, str]:
    """
    Check if a file path is protected.

    Returns:
        Tuple of (is_protected, warning_message)
    """
    # Normalize path
    normalized = file_path.replace("\\", "/")

    for pattern in PROTECTED_PATTERNS:
        if pattern in normalized:
            # Determine which warning to use
            if "datamodel" in pattern:
                return True, WARNINGS["datamodel"]
            elif "data_sheets_schema_all.yaml" in pattern:
                return True, WARNINGS["data_sheets_schema_all.yaml"]
            elif "project/" in pattern:
                return True, WARNINGS["project"]

    return False, ""


def main():
    """Main hook entry point."""
    tool_info = get_tool_info()

    if not tool_info:
        sys.exit(0)

    tool_name = tool_info.get("tool_name", "")
    tool_input = tool_info.get("tool_input", {})

    # Get file paths based on tool type
    file_paths = []

    if tool_name in ["Edit", "Write"]:
        file_path = tool_input.get("file_path", "")
        if file_path:
            file_paths.append(file_path)
    elif tool_name == "MultiEdit":
        edits = tool_input.get("edits", [])
        for edit in edits:
            file_path = edit.get("file_path", "")
            if file_path:
                file_paths.append(file_path)

    # Check each file path
    for file_path in file_paths:
        is_protected, warning = is_protected_path(file_path)
        if is_protected:
            print(f"Warning: Editing protected file: {file_path}", file=sys.stderr)
            print(f"         {warning}", file=sys.stderr)

    # Always exit 0 (warn only, don't block)
    sys.exit(0)


if __name__ == "__main__":
    main()
