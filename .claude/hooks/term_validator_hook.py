#!/usr/bin/env python3
"""
Ontology Term Validation Hook

PostToolUse hook for ontology term validation of the generated D4D schema.
Source edits report pending regeneration and validation. Generated-file edits
run linkml-term-validator and report errors as warnings (does not block).

Only the project's schema directory is eligible; no schemas are regenerated.
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


SCHEMA_DIRECTORY = Path("src/data_sheets_schema/schema")
GENERATED_SCHEMA = "data_sheets_schema_all.yaml"
PENDING_MESSAGE = (
    "Schema source changed: ontology term validation is pending regeneration. "
    "Run `make regen-all`, then `poetry run linkml-term-validator validate-schema "
    "src/data_sheets_schema/schema/data_sheets_schema_all.yaml`. "
    "This hook has not validated the edited source."
)


def schema_file_kind(file_path: str):
    """Classify the actual target within this project's schema directory."""
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    path = Path(file_path)
    path = (path if path.is_absolute() else project_dir / path).resolve()
    if path.parent != project_dir / SCHEMA_DIRECTORY:
        return None
    if path.name == GENERATED_SCHEMA:
        return "generated"
    if path.name.startswith("D4D_") and path.suffix == ".yaml":
        return "source"
    if path.name == "data_sheets_schema.yaml":
        return "source"
    return None


def is_d4d_schema_file(file_path: str) -> bool:
    """Check if the file is a source module in the project's schema directory."""
    return schema_file_kind(file_path) == "source"


def validate_ontology_terms(file_path: str) -> tuple[bool, str]:
    """
    Validate only an explicitly selected generated schema file.

    Returns:
        Tuple of (success, output_message)
    """
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    kind = schema_file_kind(file_path)
    if kind == "source":
        return True, PENDING_MESSAGE
    if kind != "generated":
        return True, "Not the project's generated schema (skipping term validation)"
    schema_path = project_dir / SCHEMA_DIRECTORY / GENERATED_SCHEMA

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
            return True, (f"Ontology term validation passed for generated schema: {schema_path}. "
                          "This validates that file only; source/generated synchronization is not established.")
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

    try:
        selected = [(file_path, schema_file_kind(file_path)) for file_path in file_paths]
        if any(kind == "source" for _path, kind in selected):
            # A batch containing source edits provides no regeneration boundary,
            # even when it also names the generated file. Never attest stale output.
            print(PENDING_MESSAGE)
        else:
            generated = next((path for path, kind in selected if kind == "generated"), None)
            if generated is not None:
                success, message = validate_ontology_terms(generated)
                if success:
                    print(message)
                else:
                    print(f"Warning: {message}", file=sys.stderr)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Term validation error: {error} (skipping)")

    # Always exit 0 (warn only, don't block)
    sys.exit(0)


if __name__ == "__main__":
    main()
