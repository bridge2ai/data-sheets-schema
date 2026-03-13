"""
Unified Transformation API for D4D ↔ RO-Crate semantic exchange.

Provides clean programmatic interface for:
- RO-Crate → D4D transformation
- D4D → RO-Crate transformation
- Multi-file RO-Crate merging
- Round-trip preservation testing
- Provenance tracking

Usage:
    from src.transformation.transform_api import SemanticTransformer, TransformationConfig

    # Basic transformation
    transformer = SemanticTransformer()
    d4d_dict = transformer.rocrate_to_d4d("input.json", validate=True)

    # With custom config
    config = TransformationConfig(
        profile_level="complete",
        preserve_provenance=True,
        merge_strategy="merge"
    )
    transformer = SemanticTransformer(config)
    d4d_dict = transformer.rocrate_to_d4d("input.json")

    # Merge multiple RO-Crates
    merged = transformer.merge_rocrates(
        ["ro-crate1.json", "ro-crate2.json"],
        output_path="merged_d4d.yaml"
    )

    # Round-trip test
    preservation = transformer.roundtrip_test("input.yaml", format="d4d")
"""

import json
import yaml
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

# Import transformation scripts from .claude/agents/scripts/
# Note: These are legacy recovered scripts not installed as a package
scripts_dir = Path(__file__).resolve().parent.parent.parent / '.claude' / 'agents' / 'scripts'
if scripts_dir.exists() and str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

try:
    from mapping_loader import MappingLoader
    from rocrate_parser import ROCrateParser
    from d4d_builder import D4DBuilder
    from validator import D4DValidator
    from rocrate_merger import ROCrateMerger
    from informativeness_scorer import InformativenessScorer
    from field_prioritizer import FieldPrioritizer
    SCRIPTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import transformation scripts from {scripts_dir}: {e}")
    print("Ensure transformation scripts exist in .claude/agents/scripts/")
    SCRIPTS_AVAILABLE = False

# Import validation framework
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from validation.unified_validator import UnifiedValidator, ValidationLevel
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False


@dataclass
class TransformationConfig:
    """Configuration for semantic transformations."""

    # Mapping configuration
    mapping_file: Path = field(default_factory=lambda: Path("data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv"))

    # Validation settings
    validate_input: bool = True
    validate_output: bool = True

    # Profile settings
    profile_level: str = "basic"  # "minimal", "basic", "complete"

    # Merge strategy for multi-source RO-Crates
    merge_strategy: str = "merge"  # "merge", "concatenate", "hybrid"

    # Provenance tracking
    preserve_provenance: bool = True

    # Output format
    output_indent: int = 2
    output_encoding: str = "utf-8"


@dataclass
class TransformationResult:
    """Results from a transformation operation."""

    # Transformed data
    data: Dict[str, Any]

    # Transformation metadata
    source: str
    target: str
    timestamp: str
    mapping_version: str

    # Coverage statistics
    coverage_percentage: Optional[float] = None
    unmapped_fields: Optional[List[str]] = None

    # Validation results
    validation_passed: Optional[bool] = None
    validation_errors: Optional[List[str]] = None

    # Provenance
    transformation_metadata: Optional[Dict[str, Any]] = None


class SemanticTransformer:
    """
    Unified API for D4D ↔ RO-Crate semantic transformation.

    Wraps transformation scripts with clean interface, validation,
    and provenance tracking.
    """

    def __init__(self, config: Optional[TransformationConfig] = None):
        """
        Initialize transformer with configuration.

        Args:
            config: Transformation configuration (uses defaults if None)
        """
        self.config = config or TransformationConfig()

        # Initialize components
        if SCRIPTS_AVAILABLE:
            self.mapping_loader = self._init_mapping_loader()
        else:
            self.mapping_loader = None

        if VALIDATION_AVAILABLE:
            self.validator = UnifiedValidator()
        else:
            self.validator = None

    def _init_mapping_loader(self) -> Optional[Any]:
        """Initialize mapping loader with configuration."""
        try:
            if self.config.mapping_file.exists():
                return MappingLoader(str(self.config.mapping_file))
            else:
                print(f"Warning: Mapping file not found: {self.config.mapping_file}")
                return None
        except Exception as e:
            print(f"Warning: Could not initialize mapping loader: {e}")
            return None

    # =========================================================================
    # RO-Crate → D4D Transformation
    # =========================================================================

    def rocrate_to_d4d(
        self,
        rocrate_input: Union[Path, str, Dict],
        output_path: Optional[Path] = None,
        validate: Optional[bool] = None
    ) -> TransformationResult:
        """
        Transform RO-Crate JSON-LD to D4D YAML.

        Args:
            rocrate_input: Path to RO-Crate file, URL string, or dict
            output_path: Optional path to save D4D YAML
            validate: Override config.validate_output (default: use config)

        Returns:
            TransformationResult with D4D data and metadata
        """
        if not SCRIPTS_AVAILABLE:
            raise RuntimeError("Transformation scripts not available. Check imports.")

        validate = validate if validate is not None else self.config.validate_output

        # Load RO-Crate data
        cleanup_temp = False
        if isinstance(rocrate_input, dict):
            # Save dict to temp file for ROCrateParser (expects file path)
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
                json.dump(rocrate_input, tmp, indent=2)
                rocrate_path = Path(tmp.name)
            source_path = "dict"
            cleanup_temp = True
        elif isinstance(rocrate_input, (Path, str)):
            rocrate_path = Path(rocrate_input) if isinstance(rocrate_input, str) else rocrate_input

            # Validate input if requested
            if self.config.validate_input and self.validator and rocrate_path.exists():
                validation_reports = self.validator.validate_all(
                    rocrate_path,
                    format="json",
                    schema="rocrate",
                    profile_level=self.config.profile_level,
                    skip_levels=[ValidationLevel.ROUNDTRIP]
                )

                syntax_ok = validation_reports[ValidationLevel.SYNTAX].passed
                if not syntax_ok:
                    raise ValueError(f"RO-Crate input validation failed: {rocrate_path}")

            source_path = str(rocrate_path)
        else:
            raise TypeError(f"Unsupported input type: {type(rocrate_input)}")

        try:
            # Parse RO-Crate (expects file path string)
            parser = ROCrateParser(str(rocrate_path))

            # Build D4D structure
            builder = D4DBuilder(self.mapping_loader)
            d4d_dict = builder.build_dataset(parser)

            # Track coverage statistics
            covered_fields = self.mapping_loader.get_covered_fields()
            mapped_count = len([f for f in covered_fields if d4d_dict.get(f) is not None])
            coverage_percentage = (mapped_count / len(covered_fields) * 100) if covered_fields else 0.0
            unmapped_fields = [f for f in covered_fields if d4d_dict.get(f) is None]

        finally:
            # Clean up temp file if created
            if cleanup_temp and rocrate_path.exists():
                rocrate_path.unlink()

        # Add transformation metadata
        if self.config.preserve_provenance:
            d4d_dict['transformation_metadata'] = {
                'source': source_path,
                'source_type': 'rocrate',
                'transformation_date': datetime.now().isoformat(),
                'mapping_version': 'v2_semantic',
                'profile_level': self.config.profile_level,
                'coverage_percentage': coverage_percentage,
                'unmapped_fields': unmapped_fields,
                'transformer_version': 'semantic_transformer_1.0'
            }

        # Validate output if requested
        validation_passed = None
        validation_errors = None

        if validate and self.validator:
            # Save to temp file for validation
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as tmp:
                yaml.dump(d4d_dict, tmp, indent=self.config.output_indent, sort_keys=False)
                tmp_path = Path(tmp.name)

            try:
                validation_reports = self.validator.validate_all(
                    tmp_path,
                    format="yaml",
                    schema="d4d",
                    skip_levels=[ValidationLevel.PROFILE, ValidationLevel.ROUNDTRIP]
                )

                validation_passed = all(r.passed for r in validation_reports.values())
                validation_errors = []
                for report in validation_reports.values():
                    validation_errors.extend(report.errors)
            finally:
                tmp_path.unlink()  # Clean up temp file

        # Save to output file if requested
        if output_path:
            with open(output_path, 'w', encoding=self.config.output_encoding) as f:
                yaml.dump(d4d_dict, f, indent=self.config.output_indent, sort_keys=False)

        # Return result
        return TransformationResult(
            data=d4d_dict,
            source=source_path,
            target="d4d",
            timestamp=datetime.now().isoformat(),
            mapping_version='v2_semantic',
            coverage_percentage=coverage_percentage,
            unmapped_fields=unmapped_fields,
            validation_passed=validation_passed,
            validation_errors=validation_errors,
            transformation_metadata=d4d_dict.get('transformation_metadata')
        )

    # =========================================================================
    # D4D → RO-Crate Transformation (Stub for Phase 3+)
    # =========================================================================

    def d4d_to_rocrate(
        self,
        d4d_input: Union[Path, Dict],
        output_path: Optional[Path] = None,
        profile_level: Optional[str] = None,
        validate: Optional[bool] = None
    ) -> TransformationResult:
        """
        Transform D4D YAML to RO-Crate JSON-LD.

        Uses inverse mappings from d4d_to_rocrate.yaml
        Adds profile conformance and SHACL validation

        Args:
            d4d_input: Path to D4D YAML file or dict
            output_path: Optional path to save RO-Crate JSON-LD
            profile_level: Profile level ("minimal", "basic", "complete")
            validate: Override config.validate_output

        Returns:
            TransformationResult with RO-Crate data and metadata
        """
        # Stub for now - full implementation in Phase 3+
        raise NotImplementedError("D4D → RO-Crate transformation not yet implemented")

    # =========================================================================
    # Multi-file RO-Crate Merging
    # =========================================================================

    def merge_rocrates(
        self,
        rocrate_inputs: List[Union[Path, str]],
        output_path: Optional[Path] = None,
        auto_prioritize: bool = True,
        validate: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Merge multiple RO-Crates into comprehensive D4D.

        Wraps rocrate_merger.py + informativeness_scorer.py
        Returns merged D4D + merge report

        Args:
            rocrate_inputs: List of paths to RO-Crate JSON-LD files
            output_path: Optional path to save merged D4D YAML
            auto_prioritize: Use informativeness scoring to rank sources
            validate: Override config.validate_output

        Returns:
            Dict with 'd4d' and 'merge_report' keys
        """
        if not SCRIPTS_AVAILABLE:
            raise RuntimeError("Transformation scripts not available. Check imports.")

        validate = validate if validate is not None else self.config.validate_output

        # Parse all RO-Crates
        parsers = []
        source_names = []
        for rocrate_path in rocrate_inputs:
            parser = ROCrateParser(str(rocrate_path))
            parsers.append(parser)
            source_names.append(Path(rocrate_path).stem)

        # Rank by informativeness if requested
        primary_index = 0
        if auto_prioritize:
            scorer = InformativenessScorer()
            ranked = scorer.rank_rocrates(parsers, self.mapping_loader)
            # ranked is List[(parser, scores, rank)] sorted by score
            parsers = [parser for parser, scores, rank in ranked]
            source_names = [Path(parser.rocrate_path).stem for parser in parsers]
            primary_index = 0  # Highest ranked becomes primary

        # Merge using field prioritization
        merger = ROCrateMerger(self.mapping_loader)
        merged_d4d = merger.merge_rocrates(parsers, primary_index=primary_index, source_names=source_names)

        # Get merge report
        merge_report = merger.generate_merge_report(parsers, source_names=source_names)

        # Add transformation metadata
        if self.config.preserve_provenance:
            merged_d4d['transformation_metadata'] = {
                'sources': [str(p) for p in rocrate_inputs],
                'source_type': 'rocrate_merge',
                'merge_strategy': self.config.merge_strategy,
                'transformation_date': datetime.now().isoformat(),
                'mapping_version': 'v2_semantic',
                'profile_level': self.config.profile_level,
                'transformer_version': 'semantic_transformer_1.0'
            }

        # Validate merged result if requested
        if validate and self.validator:
            # Save to temp file for validation
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as tmp:
                yaml.dump(merged_d4d, tmp, indent=self.config.output_indent, sort_keys=False)
                tmp_path = Path(tmp.name)

            try:
                validation_reports = self.validator.validate_all(
                    tmp_path,
                    format="yaml",
                    schema="d4d",
                    skip_levels=[ValidationLevel.PROFILE, ValidationLevel.ROUNDTRIP]
                )

                if not all(r.passed for r in validation_reports.values()):
                    print("Warning: Merged D4D validation failed")
                    for report in validation_reports.values():
                        if not report.passed:
                            print(f"  {report.level.value}: {', '.join(report.errors)}")
            finally:
                tmp_path.unlink()

        # Save to output file if requested
        if output_path:
            with open(output_path, 'w', encoding=self.config.output_encoding) as f:
                yaml.dump(merged_d4d, f, indent=self.config.output_indent, sort_keys=False)

        return {
            'd4d': merged_d4d,
            'merge_report': merge_report
        }

    # =========================================================================
    # Round-trip Testing
    # =========================================================================

    def roundtrip_test(
        self,
        input_path: Path,
        format: str = "d4d"  # "d4d" or "rocrate"
    ) -> Dict[str, Any]:
        """
        Test round-trip preservation.

        Transform A → B → A, compare and report

        Args:
            input_path: Path to input file
            format: Input format ("d4d" or "rocrate")

        Returns:
            Dict with preservation metrics and comparison details
        """
        # Stub for now - full implementation requires both directions
        raise NotImplementedError("Round-trip testing requires D4D → RO-Crate transformation (Phase 3+)")

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_mapping_stats(self) -> Dict[str, Any]:
        """Get statistics about the current mapping."""
        if not self.mapping_loader:
            return {"error": "Mapping loader not initialized"}

        covered_fields = self.mapping_loader.get_covered_fields()
        all_rocrate_props = self.mapping_loader.get_all_mapped_rocrate_properties()
        direct_mappings = [f for f in covered_fields if self.mapping_loader.is_direct_mapping(f)]

        return {
            "mapping_file": str(self.config.mapping_file),
            "total_mappings": len(self.mapping_loader.mappings),
            "covered_d4d_fields": len(covered_fields),
            "rocrate_properties": len(all_rocrate_props),
            "direct_mappings": len(direct_mappings),
            "transformation_required": len(covered_fields) - len(direct_mappings)
        }


# ==============================================================================
# Helper functions for common workflows
# ==============================================================================

def transform_rocrate_file(
    input_path: Union[Path, str],
    output_path: Union[Path, str],
    validate: bool = True,
    profile_level: str = "basic"
) -> TransformationResult:
    """
    Convenience function to transform a single RO-Crate file to D4D YAML.

    Args:
        input_path: Path to RO-Crate JSON-LD file
        output_path: Path to save D4D YAML
        validate: Run validation on output
        profile_level: RO-Crate profile level

    Returns:
        TransformationResult
    """
    config = TransformationConfig(
        validate_output=validate,
        profile_level=profile_level
    )
    transformer = SemanticTransformer(config)
    return transformer.rocrate_to_d4d(
        Path(input_path),
        output_path=Path(output_path)
    )


def batch_transform_rocrates(
    input_dir: Union[Path, str],
    output_dir: Union[Path, str],
    pattern: str = "*.json",
    validate: bool = True
) -> List[TransformationResult]:
    """
    Batch transform all RO-Crate files in a directory.

    Args:
        input_dir: Directory containing RO-Crate JSON-LD files
        output_dir: Directory to save D4D YAML files
        pattern: File pattern to match (default: "*.json")
        validate: Run validation on outputs

    Returns:
        List of TransformationResults
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    config = TransformationConfig(validate_output=validate)
    transformer = SemanticTransformer(config)

    results = []
    for rocrate_file in input_path.glob(pattern):
        out_file = output_path / f"{rocrate_file.stem}_d4d.yaml"
        result = transformer.rocrate_to_d4d(rocrate_file, output_path=out_file)
        results.append(result)
        print(f"✓ Transformed: {rocrate_file.name} → {out_file.name}")

    return results


# ==============================================================================
# CLI Interface
# ==============================================================================

def main():
    """CLI entry point for transformation API."""
    if len(sys.argv) < 3:
        print("Usage: python transform_api.py <command> <args...>")
        print("\nCommands:")
        print("  transform <rocrate.json> <output.yaml>  - Transform single RO-Crate to D4D")
        print("  batch <input_dir> <output_dir>          - Batch transform directory")
        print("  merge <out.yaml> <in1.json> <in2.json>  - Merge multiple RO-Crates")
        print("  stats                                    - Show mapping statistics")
        sys.exit(1)

    command = sys.argv[1]

    if command == "transform":
        if len(sys.argv) < 4:
            print("Usage: transform <rocrate.json> <output.yaml>")
            sys.exit(1)

        result = transform_rocrate_file(sys.argv[2], sys.argv[3])
        print(f"✓ Transformation complete")
        print(f"  Coverage: {result.coverage_percentage:.1f}%")
        if result.validation_passed is not None:
            print(f"  Validation: {'PASS' if result.validation_passed else 'FAIL'}")

    elif command == "batch":
        if len(sys.argv) < 4:
            print("Usage: batch <input_dir> <output_dir>")
            sys.exit(1)

        results = batch_transform_rocrates(sys.argv[2], sys.argv[3])
        print(f"\n✓ Batch transformation complete: {len(results)} files")

    elif command == "merge":
        if len(sys.argv) < 5:
            print("Usage: merge <output.yaml> <input1.json> <input2.json> [input3.json...]")
            sys.exit(1)

        output = Path(sys.argv[2])
        inputs = [Path(f) for f in sys.argv[3:]]

        transformer = SemanticTransformer()
        result = transformer.merge_rocrates(inputs, output_path=output)
        print(f"✓ Merged {len(inputs)} RO-Crates → {output}")

    elif command == "stats":
        transformer = SemanticTransformer()
        stats = transformer.get_mapping_stats()

        print("\nMapping Statistics:")
        print("=" * 50)
        for key, value in stats.items():
            print(f"  {key}: {value}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
