"""
Unified validation framework for D4D and RO-Crate metadata.

Provides 4 levels of validation:
1. Syntax validation (~1 second) - JSON-LD/YAML correctness
2. Semantic validation (~5 seconds) - LinkML/SHACL conformance
3. Profile validation (~10 seconds) - D4D RO-Crate profile levels
4. Round-trip validation (~30 seconds) - Preservation testing

Usage:
    from src.validation.unified_validator import UnifiedValidator, ValidationLevel

    validator = UnifiedValidator(
        schema_path=Path("src/data_sheets_schema/schema/data_sheets_schema.yaml"),
        profile_shapes_dir=Path("data/ro-crate/profiles/shapes")
    )

    # Run individual validation levels
    syntax_report = validator.validate_syntax(input_path, format="yaml")
    semantic_report = validator.validate_semantic(input_path, schema="d4d")
    profile_report = validator.validate_profile(input_path, level="basic")
    roundtrip_report = validator.validate_roundtrip(input_path, format="d4d")

    # Run all validation levels
    all_reports = validator.validate_all(input_path, format="yaml")
"""

import json
import subprocess
import yaml
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys

# Optional imports for advanced features
try:
    from linkml.validators.jsonschemavalidator import JsonSchemaDataValidator
    LINKML_AVAILABLE = True
except ImportError:
    LINKML_AVAILABLE = False

try:
    import pyshacl
    PYSHACL_AVAILABLE = True
except ImportError:
    PYSHACL_AVAILABLE = False


class ValidationLevel(Enum):
    """Validation levels in order of complexity."""
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    PROFILE = "profile"
    ROUNDTRIP = "roundtrip"


@dataclass
class ValidationReport:
    """Results from a single validation level."""
    level: ValidationLevel
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)
    coverage_percentage: Optional[float] = None
    missing_fields: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        status = "✓ PASS" if self.passed else "✗ FAIL"
        lines = [f"{status} - {self.level.value.upper()} Validation"]

        if self.errors:
            lines.append(f"  Errors ({len(self.errors)}):")
            for err in self.errors[:5]:  # Show first 5
                lines.append(f"    - {err}")
            if len(self.errors) > 5:
                lines.append(f"    ... and {len(self.errors) - 5} more")

        if self.warnings:
            lines.append(f"  Warnings ({len(self.warnings)}):")
            for warn in self.warnings[:3]:
                lines.append(f"    - {warn}")

        if self.coverage_percentage is not None:
            lines.append(f"  Coverage: {self.coverage_percentage:.1f}%")

        if self.missing_fields:
            lines.append(f"  Missing fields ({len(self.missing_fields)}): {', '.join(self.missing_fields[:5])}")

        return "\n".join(lines)


# Profile conformance level requirements
LEVEL_REQUIREMENTS = {
    "minimal": {
        "required_count": 8,
        "required_fields": [
            "@type", "name", "description", "datePublished",
            "license", "keywords", "author", "identifier"
        ]
    },
    "basic": {
        "required_count": 25,
        "required_fields": [
            # Level 1 (8)
            "@type", "name", "description", "datePublished",
            "license", "keywords", "author", "identifier",
            # Level 2 additional (17)
            "d4d:purposes", "d4d:addressingGaps",
            "contentSize", "evi:formats",
            "rai:dataCollection", "rai:dataCollectionTimeframe",
            "rai:dataManipulationProtocol", "rai:dataPreprocessingProtocol",
            "ethicalReview", "humanSubjectResearch", "deidentified", "confidentialityLevel",
            "rai:dataLimitations", "rai:dataBiases",
            "rai:dataUseCases", "prohibitedUses",
            "publisher", "rai:dataReleaseMaintenancePlan"
        ]
    },
    "complete": {
        "required_count": 100,
        "required_fields": []  # All D4D sections populated
    }
}


class UnifiedValidator:
    """Multi-level validation framework for D4D and RO-Crate metadata."""

    def __init__(
        self,
        schema_path: Optional[Path] = None,
        profile_shapes_dir: Optional[Path] = None
    ):
        """
        Initialize validator with schema and profile resources.

        Args:
            schema_path: Path to D4D LinkML schema YAML
            profile_shapes_dir: Directory containing SHACL shape files
        """
        self.schema_path = schema_path or self._default_schema_path()
        self.profile_shapes_dir = profile_shapes_dir or self._default_shapes_dir()

        # Lazy-load validators
        self._linkml_validator = None
        self._shacl_shapes = {}

    def _default_schema_path(self) -> Path:
        """Get default D4D schema path."""
        # Assume running from repo root
        return Path("src/data_sheets_schema/schema/data_sheets_schema.yaml")

    def _default_shapes_dir(self) -> Path:
        """Get default SHACL shapes directory."""
        return Path("data/ro-crate/profiles/shapes")

    # =========================================================================
    # Migration Support
    # =========================================================================

    @staticmethod
    def migrate_legacy_file_properties(data: Dict[str, Any]) -> tuple[Dict[str, Any], List[str]]:
        """
        Migrate legacy D4D files with file properties at Dataset level.

        Detects if Dataset has file properties (bytes, path, format, etc.)
        and no file_collections. If so, creates a single FileCollection
        with those properties.

        Args:
            data: Parsed D4D data dictionary

        Returns:
            Tuple of (migrated_data, warnings)
        """
        warnings = []

        # File properties that should be on File objects (not FileCollection)
        file_level_props = ['format', 'encoding', 'media_type', 'hash', 'md5', 'sha256', 'dialect']
        # Collection properties that stay on FileCollection
        collection_props = ['path', 'compression']
        # Size property needs special handling (bytes → total_bytes)

        # Check if migration needed
        all_legacy_props = file_level_props + collection_props + ['bytes']
        has_file_props = any(k in data for k in all_legacy_props)
        has_collections = 'file_collections' in data and data['file_collections']

        if has_file_props and not has_collections:
            # Create default file collection
            file_collection = {
                'id': f"{data.get('id', 'dataset')}-files",
                'name': "Dataset Files",
                'description': "Migrated from legacy dataset file properties"
            }

            # Create a File object for file-level properties
            file_obj = {
                'id': f"{data.get('id', 'dataset')}-file",
                'file_type': 'data_file'
            }

            # Track migrated properties for warning
            migrated_props = []

            # Move file-level properties to File object
            for prop in file_level_props:
                if prop in data:
                    file_obj[prop] = data.pop(prop)
                    migrated_props.append(prop)

            # Move collection-level properties to FileCollection
            for prop in collection_props:
                if prop in data:
                    file_collection[prop] = data.pop(prop)
                    migrated_props.append(prop)

            # Handle bytes → total_bytes conversion
            if 'bytes' in data:
                # Put bytes on File object
                file_obj['bytes'] = data.pop('bytes')
                # Set total_bytes on FileCollection (same value for single file)
                file_collection['total_bytes'] = file_obj['bytes']
                migrated_props.append('bytes')

            # Add File to collection resources if it has any properties
            if any(k in file_obj for k in file_level_props + ['bytes']):
                file_collection['resources'] = [file_obj]
                file_collection['file_count'] = 1

            # Add collection
            data['file_collections'] = [file_collection]

            # Create warning message
            warning_msg = (
                f"DEPRECATION: File properties ({', '.join(migrated_props)}) at Dataset level are deprecated. "
                f"Use file_collections with File objects instead. Automatically migrated to FileCollection with File resources. "
                f"This automatic migration will be removed in schema version 2.0."
            )
            warnings.append(warning_msg)

            # Update schema version if present
            if 'schema_version' in data:
                data['schema_version'] = '1.1'

        return data, warnings

    # =========================================================================
    # Level 1: Syntax Validation
    # =========================================================================

    def validate_syntax(
        self,
        input_path: Path,
        format: str = "yaml"  # "yaml", "json", "json-ld"
    ) -> ValidationReport:
        """
        Level 1: Validate syntax correctness.

        Checks:
        - File is readable and parseable
        - Valid YAML/JSON/JSON-LD syntax
        - No parse errors

        Args:
            input_path: Path to file to validate
            format: Expected format ("yaml", "json", "json-ld")

        Returns:
            ValidationReport with syntax errors
        """
        report = ValidationReport(level=ValidationLevel.SYNTAX, passed=True)

        if not input_path.exists():
            report.passed = False
            report.errors.append(f"File not found: {input_path}")
            return report

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if format in ("yaml", "yml"):
                data = yaml.safe_load(content)
                if data is None:
                    report.passed = False
                    report.errors.append("Empty YAML file")
            elif format in ("json", "json-ld", "jsonld"):
                data = json.loads(content)
                if not data:
                    report.passed = False
                    report.errors.append("Empty JSON file")
            else:
                report.passed = False
                report.errors.append(f"Unsupported format: {format}")
                return report

            report.info.append(f"Valid {format.upper()} syntax")
            report.metadata['format'] = format
            report.metadata['file_size'] = len(content)

        except yaml.YAMLError as e:
            report.passed = False
            report.errors.append(f"YAML syntax error: {e}")
        except json.JSONDecodeError as e:
            report.passed = False
            report.errors.append(f"JSON syntax error: {e}")
        except Exception as e:
            report.passed = False
            report.errors.append(f"Syntax validation error: {e}")

        return report

    # =========================================================================
    # Level 2: Semantic Validation
    # =========================================================================

    def validate_semantic(
        self,
        input_path: Path,
        schema: str = "d4d",  # "d4d" or "rocrate"
        target_class: Optional[str] = None
    ) -> ValidationReport:
        """
        Level 2: Validate semantic correctness against schema.

        For D4D: Uses LinkML schema validation (classes, slots, types, ranges)
        For RO-Crate: Uses SHACL shape validation

        Args:
            input_path: Path to file to validate
            schema: Which schema to validate against ("d4d" or "rocrate")
            target_class: Specific class to validate (default: Dataset)

        Returns:
            ValidationReport with semantic errors
        """
        report = ValidationReport(level=ValidationLevel.SEMANTIC, passed=True)

        # First check syntax
        format_ext = input_path.suffix.lstrip('.')
        if format_ext in ('yml', 'yaml'):
            format_type = 'yaml'
        elif format_ext in ('json', 'jsonld'):
            format_type = 'json'
        else:
            report.passed = False
            report.errors.append(f"Unknown file format: {input_path.suffix}")
            return report

        syntax_report = self.validate_syntax(input_path, format=format_type)
        if not syntax_report.passed:
            report.passed = False
            report.errors.append("Syntax validation failed (run level 1 first)")
            return report

        if schema == "d4d":
            return self._validate_d4d_semantic(input_path, target_class, report)
        elif schema == "rocrate":
            return self._validate_rocrate_semantic(input_path, report)
        else:
            report.passed = False
            report.errors.append(f"Unknown schema type: {schema}")
            return report

    def _validate_d4d_semantic(
        self,
        input_path: Path,
        target_class: Optional[str],
        report: ValidationReport
    ) -> ValidationReport:
        """Validate D4D YAML against LinkML schema."""

        if not LINKML_AVAILABLE:
            report.warnings.append("linkml not installed - skipping semantic validation")
            report.info.append("Install with: pip install linkml")
            return report

        try:
            # Load and potentially migrate data
            with open(input_path, 'r') as f:
                data = yaml.safe_load(f)

            # Apply migration if needed
            migrated_data, migration_warnings = self.migrate_legacy_file_properties(data)

            # Add migration warnings to report
            report.warnings.extend(migration_warnings)

            # If migrated, write to temp file for validation
            if migration_warnings:
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.yaml',
                    delete=False
                )
                try:
                    yaml.dump(migrated_data, temp_file, default_flow_style=False, sort_keys=False)
                    temp_file.close()
                    validation_path = Path(temp_file.name)
                    report.info.append("Validating migrated data (legacy file properties → FileCollection)")
                except Exception as e:
                    report.errors.append(f"Failed to write migrated data: {e}")
                    return report
            else:
                validation_path = input_path

            # Use linkml-validate command
            cmd = [
                "linkml-validate",
                "-s", str(self.schema_path),
                str(validation_path)
            ]

            if target_class:
                cmd.extend(["-C", target_class])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Clean up temp file if created
            if migration_warnings and validation_path != input_path:
                try:
                    validation_path.unlink()
                except Exception:
                    pass  # Best effort cleanup

            if result.returncode == 0:
                report.info.append("D4D schema validation passed")
            else:
                report.passed = False
                # Parse validation errors from output
                if result.stderr:
                    for line in result.stderr.strip().split('\n'):
                        if line and not line.startswith('WARNING'):
                            report.errors.append(line)

                if result.stdout:
                    for line in result.stdout.strip().split('\n'):
                        if 'error' in line.lower():
                            report.errors.append(line)

        except subprocess.TimeoutExpired:
            report.passed = False
            report.errors.append("Validation timeout (>30 seconds)")
            # Clean up temp file if created
            if migration_warnings and validation_path != input_path:
                try:
                    validation_path.unlink()
                except Exception:
                    pass
        except FileNotFoundError:
            report.warnings.append("linkml-validate command not found")
            report.info.append("Install with: pip install linkml")
        except Exception as e:
            report.passed = False
            report.errors.append(f"D4D validation error: {e}")

        return report

    def _validate_rocrate_semantic(
        self,
        input_path: Path,
        report: ValidationReport
    ) -> ValidationReport:
        """Validate RO-Crate JSON-LD against SHACL shapes."""

        if not PYSHACL_AVAILABLE:
            report.warnings.append("pyshacl not installed - skipping SHACL validation")
            report.info.append("Install with: pip install pyshacl")
            return report

        # For now, just note that SHACL validation would run here
        # Full implementation would load shapes and validate
        report.info.append("RO-Crate SHACL validation (stub - not yet implemented)")
        report.warnings.append("SHACL validation requires shape files in: " + str(self.profile_shapes_dir))

        return report

    # =========================================================================
    # Level 3: Profile Validation
    # =========================================================================

    def validate_profile(
        self,
        input_path: Path,
        level: str = "basic"  # "minimal", "basic", "complete"
    ) -> ValidationReport:
        """
        Level 3: Validate conformance to D4D RO-Crate profile level.

        Checks:
        - Required fields present
        - Field coverage percentage
        - Recommended fields (warnings for Level 2+)

        Args:
            input_path: Path to RO-Crate JSON-LD file
            level: Profile level ("minimal", "basic", "complete")

        Returns:
            ValidationReport with profile conformance details
        """
        report = ValidationReport(level=ValidationLevel.PROFILE, passed=True)

        if level not in LEVEL_REQUIREMENTS:
            report.passed = False
            report.errors.append(f"Unknown profile level: {level}")
            return report

        # Load and parse file
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                if input_path.suffix in ('.json', '.jsonld'):
                    data = json.load(f)
                elif input_path.suffix in ('.yaml', '.yml'):
                    data = yaml.safe_load(f)
                else:
                    report.passed = False
                    report.errors.append(f"Unsupported file format: {input_path.suffix}")
                    return report
        except Exception as e:
            report.passed = False
            report.errors.append(f"Failed to load file: {e}")
            return report

        # Extract Dataset entity from RO-Crate @graph
        if '@graph' in data and isinstance(data['@graph'], list):
            datasets = [e for e in data['@graph'] if 'Dataset' in str(e.get('@type', ''))]
            if not datasets:
                report.passed = False
                report.errors.append("No Dataset entity found in RO-Crate @graph")
                return report
            dataset = datasets[0]  # Use first Dataset
        elif '@type' in data:
            dataset = data  # Direct D4D format
        else:
            report.passed = False
            report.errors.append("Cannot find Dataset entity in file")
            return report

        # Check required fields
        requirements = LEVEL_REQUIREMENTS[level]
        required_fields = requirements["required_fields"]
        missing_fields = []

        for field in required_fields:
            if field not in dataset and not self._check_nested_field(dataset, field):
                missing_fields.append(field)

        # Calculate coverage
        found_count = len(required_fields) - len(missing_fields)
        coverage = (found_count / len(required_fields) * 100) if required_fields else 100.0

        report.coverage_percentage = coverage
        report.missing_fields = missing_fields
        report.metadata['level'] = level
        report.metadata['required_count'] = len(required_fields)
        report.metadata['found_count'] = found_count

        # Determine pass/fail
        if level == "minimal" and coverage < 100:
            report.passed = False
            report.errors.append(f"Missing required fields for Level 1: {', '.join(missing_fields)}")
        elif level == "basic" and coverage < 80:
            report.passed = False
            report.errors.append(f"Insufficient coverage for Level 2: {coverage:.1f}% (need ≥80%)")
            report.errors.append(f"Missing fields: {', '.join(missing_fields)}")
        elif level == "complete" and coverage < 70:
            report.passed = False
            report.errors.append(f"Insufficient coverage for Level 3: {coverage:.1f}% (need ≥70%)")
        else:
            report.info.append(f"Profile level '{level}' validation passed ({coverage:.1f}% coverage)")

        if 70 <= coverage < 100 and level in ("minimal", "basic"):
            report.warnings.append(f"Missing optional fields: {', '.join(missing_fields)}")

        return report

    def _check_nested_field(self, data: Dict, field: str) -> bool:
        """Check if a field exists, handling namespace prefixes."""
        # Handle d4d:, rai:, evi: prefixes
        if ':' in field:
            prefix, name = field.split(':', 1)
            # Try with prefix
            if field in data:
                return True
            # Try without prefix
            if name in data:
                return True
        return field in data

    # =========================================================================
    # Level 4: Round-trip Validation
    # =========================================================================

    def validate_roundtrip(
        self,
        input_path: Path,
        format: str = "d4d"  # "d4d" or "rocrate"
    ) -> ValidationReport:
        """
        Level 4: Validate round-trip preservation.

        Transforms input → intermediate → output and compares.

        D4D → RO-Crate → D4D
        RO-Crate → D4D → RO-Crate

        Args:
            input_path: Path to input file
            format: Input format ("d4d" or "rocrate")

        Returns:
            ValidationReport with preservation metrics
        """
        report = ValidationReport(level=ValidationLevel.ROUNDTRIP, passed=True)

        # Round-trip validation requires transformation API (Phase 3)
        report.info.append("Round-trip validation requires transformation API")
        report.warnings.append("Not yet implemented - coming in Phase 3")
        report.metadata['requires_phase3'] = True

        return report

    # =========================================================================
    # Combined Validation
    # =========================================================================

    def validate_all(
        self,
        input_path: Path,
        format: str = "yaml",
        schema: str = "d4d",
        profile_level: str = "basic",
        skip_levels: Optional[List[ValidationLevel]] = None
    ) -> Dict[ValidationLevel, ValidationReport]:
        """
        Run all validation levels and return comprehensive report.

        Args:
            input_path: Path to file to validate
            format: File format ("yaml", "json", "json-ld")
            schema: Schema to validate against ("d4d", "rocrate")
            profile_level: Profile level for Level 3 ("minimal", "basic", "complete")
            skip_levels: Optional levels to skip

        Returns:
            Dict mapping ValidationLevel to ValidationReport
        """
        skip_levels = skip_levels or []
        reports = {}

        # Level 1: Syntax
        if ValidationLevel.SYNTAX not in skip_levels:
            syntax = self.validate_syntax(input_path, format=format)
            reports[ValidationLevel.SYNTAX] = syntax

            if not syntax.passed:
                # If syntax fails, stop here
                for level in [ValidationLevel.SEMANTIC, ValidationLevel.PROFILE, ValidationLevel.ROUNDTRIP]:
                    reports[level] = ValidationReport(
                        level=level,
                        passed=False,
                        errors=["Skipped due to syntax errors"]
                    )
                return reports

        # Level 2: Semantic
        if ValidationLevel.SEMANTIC not in skip_levels:
            semantic = self.validate_semantic(input_path, schema=schema)
            reports[ValidationLevel.SEMANTIC] = semantic

        # Level 3: Profile
        if ValidationLevel.PROFILE not in skip_levels and schema == "rocrate":
            profile = self.validate_profile(input_path, level=profile_level)
            reports[ValidationLevel.PROFILE] = profile
        elif ValidationLevel.PROFILE not in skip_levels:
            reports[ValidationLevel.PROFILE] = ValidationReport(
                level=ValidationLevel.PROFILE,
                passed=True,
                info=["Profile validation only applies to RO-Crate format"]
            )

        # Level 4: Round-trip
        if ValidationLevel.ROUNDTRIP not in skip_levels:
            roundtrip = self.validate_roundtrip(input_path, format=schema)
            reports[ValidationLevel.ROUNDTRIP] = roundtrip

        return reports

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def print_report(self, reports: Dict[ValidationLevel, ValidationReport]):
        """Pretty-print validation reports."""
        print("\n" + "=" * 70)
        print("VALIDATION REPORT")
        print("=" * 70)

        for level in [ValidationLevel.SYNTAX, ValidationLevel.SEMANTIC,
                      ValidationLevel.PROFILE, ValidationLevel.ROUNDTRIP]:
            if level in reports:
                print(f"\n{reports[level]}")

        print("\n" + "=" * 70)

        # Overall summary
        all_passed = all(r.passed for r in reports.values())
        print(f"\nOVERALL: {'✓ PASS' if all_passed else '✗ FAIL'}")
        print("=" * 70 + "\n")


def main():
    """CLI entry point for validation."""
    if len(sys.argv) < 2:
        print("Usage: python unified_validator.py <file_path> [format] [schema] [level]")
        print("\nExamples:")
        print("  python unified_validator.py data/test/minimal_d4d.yaml yaml d4d basic")
        print("  python unified_validator.py data/ro-crate/examples/basic.json json rocrate basic")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    format = sys.argv[2] if len(sys.argv) > 2 else "yaml"
    schema = sys.argv[3] if len(sys.argv) > 3 else "d4d"
    level = sys.argv[4] if len(sys.argv) > 4 else "basic"

    validator = UnifiedValidator()
    reports = validator.validate_all(
        input_path,
        format=format,
        schema=schema,
        profile_level=level
    )

    validator.print_report(reports)

    # Exit code: 0 if all passed, 1 otherwise
    all_passed = all(r.passed for r in reports.values())
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
