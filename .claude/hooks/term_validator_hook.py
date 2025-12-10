#!/usr/bin/env python3
"""
Ontology Term Validation Hook

PostToolUse hook that validates ontology term references in D4D schema files.
Runs linkml-term-validator and reports errors as warnings (does not block).

Triggers on files matching: D4D_*.yaml (schema files)
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def get_tool_info():
    """Parse tool use information from stdin."""
    try:
        input_data = sys.stdin.read()
        if not input_data:
            return None
        return json.loads(input_data)
    except json.JSONDecodeError:
        return None


def is_d4d_schema_file(file_path: str) -> bool:
    """Check if the file is a D4D schema module file."""
    path = Path(file_path)
    # Match D4D_*.yaml files in the schema directory
    if path.name.startswith("D4D_") and path.suffix == ".yaml":
        return True
    # Also match the main schema file
    if path.name == "data_sheets_schema.yaml":
        return True
    return False


def validate_ontology_terms(file_path: str) -> tuple[bool, str]:
    """
    Validate ontology terms in a schema file.

    Returns:
        Tuple of (success, output_message)
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")

    # For schema files, validate the full schema to check all term references
    schema_path = Path(project_dir) / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"

    if not schema_path.exists():
        return True, f"Full schema file not found: {schema_path} (skipping term validation)"

    try:
        result = subprocess.run(
            [
                "poetry", "run", "linkml-term-validator", "validate-schema",
                str(schema_path)
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=project_dir
        )

        output = result.stdout + result.stderr

        # Filter out common noise
        filtered_lines = []
        for line in output.split("\n"):
            if not line.strip():
                continue
            if "INFO" in line:
                continue
            if "DEBUG" in line:
                continue
            filtered_lines.append(line)

        filtered_output = "\n".join(filtered_lines)

        if result.returncode == 0:
            return True, f"Ontology term validation passed for schema"
        else:
            return False, f"Ontology term validation warnings:\n{filtered_output}"

    except subprocess.TimeoutExpired:
        return True, "Term validation timed out (skipping)"
    except FileNotFoundError:
        return True, "linkml-term-validator not found (skipping validation)"
    except Exception as e:
        return True, f"Term validation error: {e} (skipping)"


def main():
    """Main hook entry point."""
    tool_info = get_tool_info()

    if not tool_info:
        # No input, nothing to validate
        sys.exit(0)

    # Get the file path from tool use
    tool_name = tool_info.get("tool_name", "")
    tool_input = tool_info.get("tool_input", {})

    # Handle different tool types
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
    validated = False
    for file_path in file_paths:
        if is_d4d_schema_file(file_path):
            if not validated:
                # Only validate once per batch of edits
                success, message = validate_ontology_terms(file_path)
                validated = True

                if success:
                    print(message)
                else:
                    # Print warning but don't block (exit 0)
                    print(f"Warning: {message}", file=sys.stderr)

    # Always exit 0 (warn only, don't block)
    sys.exit(0)


if __name__ == "__main__":
    main()
