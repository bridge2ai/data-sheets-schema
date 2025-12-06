#!/usr/bin/env python3
"""
D4D YAML Validation Hook

PostToolUse hook that validates D4D YAML files after Edit/Write operations.
Runs linkml-validate and reports errors as warnings (does not block).

Triggers on files matching: *_d4d.yaml
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


def is_d4d_yaml_file(file_path: str) -> bool:
    """Check if the file is a D4D YAML file."""
    return file_path.endswith("_d4d.yaml")


def validate_d4d_yaml(file_path: str) -> tuple[bool, str]:
    """
    Validate a D4D YAML file against the schema.

    Returns:
        Tuple of (success, output_message)
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    schema_path = Path(project_dir) / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"

    if not schema_path.exists():
        return True, f"Schema file not found: {schema_path} (skipping validation)"

    if not Path(file_path).exists():
        return True, f"File not found: {file_path} (skipping validation)"

    try:
        result = subprocess.run(
            [
                "poetry", "run", "linkml-validate",
                "-s", str(schema_path),
                "-C", "Dataset",
                file_path
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_dir
        )

        output = result.stdout + result.stderr

        # Filter out common noise
        filtered_lines = []
        for line in output.split("\n"):
            # Skip empty lines and common warnings
            if not line.strip():
                continue
            if "INFO" in line:
                continue
            filtered_lines.append(line)

        filtered_output = "\n".join(filtered_lines)

        if result.returncode == 0:
            return True, f"D4D validation passed: {file_path}"
        else:
            return False, f"D4D validation warnings for {file_path}:\n{filtered_output}"

    except subprocess.TimeoutExpired:
        return True, f"Validation timed out for {file_path} (skipping)"
    except FileNotFoundError:
        return True, "poetry not found (skipping validation)"
    except Exception as e:
        return True, f"Validation error: {e} (skipping)"


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
    if tool_name in ["Edit", "Write"]:
        file_path = tool_input.get("file_path", "")
    elif tool_name == "MultiEdit":
        # For MultiEdit, check all files
        edits = tool_input.get("edits", [])
        for edit in edits:
            file_path = edit.get("file_path", "")
            if is_d4d_yaml_file(file_path):
                success, message = validate_d4d_yaml(file_path)
                if not success:
                    print(f"Warning: {message}", file=sys.stderr)
        sys.exit(0)
    else:
        sys.exit(0)

    # Check if this is a D4D YAML file
    if not is_d4d_yaml_file(file_path):
        sys.exit(0)

    # Validate the file
    success, message = validate_d4d_yaml(file_path)

    if success:
        print(message)
    else:
        # Print warning but don't block (exit 0)
        print(f"Warning: {message}", file=sys.stderr)

    # Always exit 0 (warn only, don't block)
    sys.exit(0)


if __name__ == "__main__":
    main()
