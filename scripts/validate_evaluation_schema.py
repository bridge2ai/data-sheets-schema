#!/usr/bin/env python3
"""
Validate D4D evaluation JSON files against their schemas.

This ensures evaluations conform to the standardized schema, which in turn
ensures HTML renderers can reliably parse the output.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import jsonschema
    from jsonschema import validate, ValidationError
except ImportError:
    print("ERROR: jsonschema package not installed")
    print("Install with: pip install jsonschema")
    sys.exit(1)


def load_schema(schema_path: Path) -> Dict:
    """Load JSON Schema file."""
    with open(schema_path, 'r') as f:
        return json.load(f)


def load_evaluation(eval_path: Path) -> Dict:
    """Load evaluation JSON file."""
    with open(eval_path, 'r') as f:
        return json.load(f)


def validate_evaluation(eval_data: Dict, schema: Dict) -> Tuple[bool, List[str]]:
    """
    Validate evaluation data against schema.

    Returns:
        (is_valid, errors): Tuple of validation status and error messages
    """
    errors = []
    try:
        validate(instance=eval_data, schema=schema)
        return True, []
    except ValidationError as e:
        errors.append(f"Validation error: {e.message}")
        errors.append(f"  Path: {' -> '.join(str(p) for p in e.path)}")
        if e.schema_path:
            errors.append(f"  Schema path: {' -> '.join(str(p) for p in e.schema_path)}")
        return False, errors


def main():
    """Validate all evaluation JSON files in specified directories."""

    # Paths
    base_dir = Path(__file__).parent.parent
    schema_dir = base_dir / "src" / "download" / "prompts"
    eval_base = base_dir / "data" / "evaluation_llm"

    # Load schemas
    schemas = {
        "rubric10-semantic": load_schema(schema_dir / "rubric10_semantic_schema.json"),
        "rubric20-semantic": load_schema(schema_dir / "rubric20_semantic_schema.json"),
    }

    # Find all evaluation JSON files
    eval_files = []
    for rubric_type in ["rubric10_semantic", "rubric20_semantic"]:
        rubric_dir = eval_base / rubric_type / "concatenated"
        if rubric_dir.exists():
            eval_files.extend(rubric_dir.glob("*_evaluation.json"))

    if not eval_files:
        print(f"No evaluation files found in {eval_base}")
        return 1

    print(f"Found {len(eval_files)} evaluation files to validate\n")

    # Validate each file
    valid_count = 0
    invalid_count = 0

    for eval_file in sorted(eval_files):
        print(f"Validating: {eval_file.name}")

        # Load evaluation
        try:
            eval_data = load_evaluation(eval_file)
        except Exception as e:
            print(f"  ❌ Failed to load: {e}")
            invalid_count += 1
            continue

        # Determine rubric type
        rubric = eval_data.get("rubric", "unknown")
        if rubric not in schemas:
            print(f"  ⚠️  No schema available for rubric type: {rubric}")
            continue

        # Validate
        is_valid, errors = validate_evaluation(eval_data, schemas[rubric])

        if is_valid:
            print(f"  ✅ Valid")
            valid_count += 1
        else:
            print(f"  ❌ Invalid:")
            for error in errors:
                print(f"     {error}")
            invalid_count += 1

        print()

    # Summary
    print("=" * 60)
    print(f"SUMMARY:")
    print(f"  ✅ Valid:   {valid_count}")
    print(f"  ❌ Invalid: {invalid_count}")
    print(f"  📊 Total:   {valid_count + invalid_count}")
    print("=" * 60)

    return 0 if invalid_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
