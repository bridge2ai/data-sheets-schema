#!/usr/bin/env python3
"""
Validator - Wrap linkml-validate for D4D YAML validation.

This module provides a Python wrapper around the linkml-validate command
to validate generated D4D YAML files against the D4D schema.
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


class D4DValidator:
    """Validate D4D YAML files against the D4D schema."""

    def __init__(self, schema_path: str):
        """
        Initialize validator with D4D schema.

        Args:
            schema_path: Path to D4D schema YAML file
        """
        self.schema_path = Path(schema_path)

        if not self.schema_path.exists():
            raise FileNotFoundError(f"D4D schema not found: {schema_path}")

    def validate_d4d_yaml(self, yaml_file: str, target_class: str = "Dataset") -> Tuple[bool, str]:
        """
        Validate D4D YAML file against schema.

        Args:
            yaml_file: Path to D4D YAML file to validate
            target_class: Target class name (default: "Dataset")

        Returns:
            Tuple of (is_valid, error_output)
        """
        yaml_path = Path(yaml_file)
        if not yaml_path.exists():
            return False, f"File not found: {yaml_file}"

        # Try linkml-validate directly first, fall back to poetry run if not found
        commands_to_try = [
            ["linkml-validate", "-s", str(self.schema_path), "-C", target_class, str(yaml_path)],
            ["poetry", "run", "linkml-validate", "-s", str(self.schema_path), "-C", target_class, str(yaml_path)]
        ]

        for cmd in commands_to_try:
            try:
                # Run linkml-validate
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                # Check if validation passed
                is_valid = result.returncode == 0

                # Combine stdout and stderr
                output = result.stdout + result.stderr

                return is_valid, output

            except FileNotFoundError:
                # Command not found, try next approach
                continue
            except subprocess.TimeoutExpired:
                return False, "Validation timeout (30s)"
            except Exception as e:
                # Other error, try next command
                if cmd is commands_to_try[-1]:
                    # Last command failed
                    return False, f"Validation error: {str(e)}"
                continue

        # None of the commands worked
        return False, "linkml-validate not found (install linkml or run from poetry environment)"

    def parse_validation_errors(self, error_output: str) -> List[Dict[str, str]]:
        """
        Parse validation error messages.

        Args:
            error_output: Raw error output from linkml-validate

        Returns:
            List of error dicts with 'field', 'message', 'type' keys
        """
        errors = []

        # Common error patterns
        patterns = [
            # Missing required field: "... is a required field"
            r"'(.+?)' is a required field",
            # Type mismatch: "... Expected type ..."
            r"(.+?): Expected type (.+?), got (.+)",
            # Invalid value: "... is not a valid ..."
            r"'(.+?)' is not a valid (.+)",
            # Enum constraint: "... not in permissible values"
            r"'(.+?)' not in permissible values \[(.+?)\]",
        ]

        lines = error_output.split('\n')
        for line in lines:
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    errors.append({
                        'line': line,
                        'field': match.group(1) if match.groups() else 'unknown',
                        'message': line.strip(),
                        'type': self._classify_error(line)
                    })
                    break

        return errors

    def _classify_error(self, error_line: str) -> str:
        """Classify error type from error message."""
        error_lower = error_line.lower()

        if 'required' in error_lower:
            return 'missing_required'
        elif 'type' in error_lower:
            return 'type_mismatch'
        elif 'not in permissible' in error_lower or 'enum' in error_lower:
            return 'invalid_enum'
        elif 'format' in error_lower or 'pattern' in error_lower:
            return 'format_error'
        else:
            return 'other'

    def suggest_fixes(self, errors: List[Dict[str, str]]) -> List[str]:
        """
        Suggest fixes for common validation errors.

        Args:
            errors: List of parsed errors

        Returns:
            List of fix suggestions
        """
        suggestions = []

        for error in errors:
            error_type = error.get('type')
            field = error.get('field', '')

            if error_type == 'missing_required':
                suggestions.append(
                    f"Add required field '{field}' to your D4D YAML. "
                    f"Check RO-Crate for corresponding value or provide manually."
                )

            elif error_type == 'type_mismatch':
                suggestions.append(
                    f"Fix type for field '{field}'. Check D4D schema for expected type."
                )

            elif error_type == 'invalid_enum':
                suggestions.append(
                    f"Fix enum value for field '{field}'. Use one of the permissible values."
                )

            elif error_type == 'format_error':
                if 'date' in field.lower():
                    suggestions.append(
                        f"Fix date format for '{field}'. Use YYYY-MM-DD format."
                    )
                elif 'url' in field.lower() or 'uri' in field.lower():
                    suggestions.append(
                        f"Fix URI format for '{field}'. Ensure it starts with http://, https://, etc."
                    )

        return suggestions

    def get_validation_summary(self, is_valid: bool, error_output: str) -> str:
        """
        Generate a human-readable validation summary.

        Args:
            is_valid: Whether validation passed
            error_output: Raw error output

        Returns:
            Formatted summary string
        """
        if is_valid:
            return "✓ Validation passed - D4D YAML is valid against schema"

        errors = self.parse_validation_errors(error_output)
        suggestions = self.suggest_fixes(errors)

        summary = "✗ Validation failed\n\n"

        if errors:
            summary += f"Found {len(errors)} error(s):\n\n"
            for i, error in enumerate(errors, 1):
                summary += f"{i}. {error['message']}\n"

            if suggestions:
                summary += "\n\nSuggested fixes:\n\n"
                for i, suggestion in enumerate(suggestions, 1):
                    summary += f"{i}. {suggestion}\n"
        else:
            summary += "Raw error output:\n"
            summary += error_output

        return summary
