"""
Unified Transformation API for D4D ↔ RO-Crate semantic exchange.

Provides clean programmatic interface for:
- RO-Crate → D4D transformation
- D4D → RO-Crate transformation
- Multi-file RO-Crate merging
- Round-trip preservation testing
- Provenance tracking

Usage:
    from pathlib import Path
    from src.transformation.transform_api import SemanticTransformer, TransformationConfig

    # Explicit Dataset publication; provenance stays on the result object.
    transformer = SemanticTransformer(TransformationConfig(
        mapping_file=Path("path/to/reviewed-mapping.tsv"), result_contract="dataset_v1"))
    result = transformer.rocrate_to_d4d("input.json", output_path="output.yaml")
    dataset = result.data
    metadata = result.transformation_metadata

    # With custom config
    config = TransformationConfig(
        mapping_file=Path("path/to/reviewed-mapping.tsv"),
        profile_level="complete",
        preserve_provenance=True,
        merge_strategy="merge",
        result_contract="dataset_v1"
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
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime
from hashlib import sha256
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

from data_sheets_schema.legacy_publication import PublicationError, prepare_dataset, publish
from data_sheets_schema.legacy_root_identity import scoring_fields
from data_sheets_schema.legacy_creators import (
    creator_route, author_source_presence, construction_basis, source_presence_lines,
    VALUE_BASIS_LABEL, MEASUREMENT_LIMIT,
)

from data_sheets_schema.legacy_creator_references import reference_evidence, reference_lines

RESULT_CONTRACTS = frozenset({"legacy", "dataset_v1"})
RESULT_FORMAT = "d4d_transformation_result_v1"


def _result_contract(value):
    if type(value) is not str or value not in RESULT_CONTRACTS:
        raise ValueError("result_contract must be 'legacy' or 'dataset_v1'")
    return value


def _publication_binding(path, raw, encoding):
    """Name the exact accepted serialization after the publisher has written it."""
    path = Path(path)
    if path.read_bytes() != raw:
        raise PublicationError(f"Published Dataset bytes changed before provenance binding: {path}")
    return {"format": "d4d_dataset_publication_v1", "path": str(path.resolve()),
            "sha256": sha256(raw).hexdigest(), "bytes": len(raw),
            "encoding": encoding, "root_class": "Dataset"}

# Import validation framework
# Only add to sys.path if not already present to avoid pollution
validation_dir = Path(__file__).parent.parent
if validation_dir.exists() and str(validation_dir) not in sys.path:
    sys.path.insert(0, str(validation_dir))
try:
    from validation.unified_validator import UnifiedValidator, ValidationLevel
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False


def _parse_rocrate(rocrate_path: Union[Path, str]):
    """`ROCrateParser` on the crate at `rocrate_path`, read first as
    `fairscape-cli parse` reads one (#4186).

    The parser imported above is the copy under .claude/agents/scripts,
    which opens the crate as UTF-8 itself, so a crate that is not UTF-8
    ended `rocrate_to_d4d` and `merge_rocrates` with a bare
    UnicodeDecodeError. Read through `rocrate_map.read_crate_json`, such
    a crate is refused with a CrateEncodingError that names the first byte
    that does not decode and says to transcode it. With `validate_input`,
    the default, `rocrate_to_d4d` still refuses it earlier, when the input
    validation fails, as before. A path that is not a file is left to the
    parser, which reports it as before.
    """
    from data_sheets_schema.rocrate_map import TRANSCODE_HINT, read_crate_json

    if Path(rocrate_path).is_file():
        read_crate_json(Path(rocrate_path), hint=TRANSCODE_HINT)
    return ROCrateParser(str(rocrate_path))


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

    # Explicit compatibility choice for Dataset/metadata placement. Outer
    # diagnostics qualify compatible construction counts in both contracts.
    result_contract: str = "legacy"


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

    # Legacy-named construction statistics; see coverage_basis, not source coverage.
    coverage_percentage: Optional[float] = None
    unmapped_fields: Optional[List[str]] = None

    # Validation results
    validation_passed: Optional[bool] = None
    validation_errors: Optional[List[str]] = None

    # Provenance
    transformation_metadata: Optional[Dict[str, Any]] = None

    # Additive diagnostics: construction counts and original route evidence.
    # These remain available when optional provenance is disabled.
    coverage_basis: Optional[Dict[str, Any]] = None
    source_presence: Optional[Dict[str, Any]] = None


@dataclass
class CreatorReferenceTransformationResult(TransformationResult):
    """Only the explicit reference policy adds source-member evidence."""

    creator_reference_construction: Optional[Dict[str, Any]] = None


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
        _result_contract(self.config.result_contract)
        self._mapping_capture = None

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
                path = self.config.mapping_file.resolve()
                # Capture alongside the existing loader. A capture failure must
                # not change legacy draft admission; dataset_v1 requires it.
                try:
                    before = path.read_bytes()
                except OSError:
                    before = None
                loader = MappingLoader(str(self.config.mapping_file))
                try:
                    if before is not None and path.read_bytes() == before:
                        self._mapping_capture = (path, before)
                except OSError:
                    pass
                return loader
            else:
                print(f"Warning: Mapping file not found: {self.config.mapping_file}")
                return None
        except Exception as e:
            print(f"Warning: Could not initialize mapping loader: {e}")
            return None

    def _mapping_identity(self):
        """Bind the loaded TSV bytes; this does not authenticate an algorithm version."""
        if self._mapping_capture is None:
            raise PublicationError("dataset_v1 requires a captured mapping file")
        path, raw = self._mapping_capture
        try:
            unchanged = self.config.mapping_file.resolve() == path and path.read_bytes() == raw
        except OSError:
            unchanged = False
        if not unchanged:
            raise PublicationError("Mapping bytes changed after loader initialization; create a new transformer")
        return {"path": str(path), "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}

    def _contract(self, override):
        return _result_contract(self.config.result_contract if override is None else override)

    # =========================================================================
    # RO-Crate → D4D Transformation
    # =========================================================================

    def rocrate_to_d4d(
        self,
        rocrate_input: Union[Path, str, Dict],
        output_path: Optional[Path] = None,
        validate: Optional[bool] = None,
        *,
        result_contract: Optional[str] = None
    ) -> TransformationResult:
        """
        Transform RO-Crate JSON-LD to D4D YAML.

        Args:
            rocrate_input: Path to RO-Crate file or dict (URLs not supported)
            output_path: Optional path to save D4D YAML
            validate: Override config.validate_output (default: use config)
            result_contract: Explicit dataset_v1 keeps provenance outside data;
                legacy (the default) preserves the existing draft shape.

        Returns:
            TransformationResult with D4D data and metadata
        """
        contract = self._contract(result_contract)
        mapping = self._mapping_identity() if contract == "dataset_v1" else None
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
            parser = _parse_rocrate(rocrate_path)

            # Check mapping loader is available
            if self.mapping_loader is None:
                raise RuntimeError("Mapping loader not initialized. Check mapping file path.")

            # Build D4D structure
            builder = D4DBuilder(self.mapping_loader)
            d4d_dict = builder.build_dataset(parser)

            # Track coverage statistics
            # Required root identity is construction, not additional source
            # coverage. Unmarked custom ID mappings keep their prior meaning.
            covered_fields = scoring_fields(self.mapping_loader)
            mapped_count = len([f for f in covered_fields if d4d_dict.get(f) is not None])
            coverage_percentage = (mapped_count / len(covered_fields) * 100) if covered_fields else 0.0
            unmapped_fields = [f for f in covered_fields if d4d_dict.get(f) is None]
            basis = construction_basis(mapped_count, len(covered_fields))
            source_presence = author_source_presence(
                self.mapping_loader, [parser], [source_path])
            marked_creators = creator_route(self.mapping_loader)
            references = reference_evidence(
                source_presence, [builder.get_creator_reference_construction()])

        finally:
            # Clean up temp file if created
            if cleanup_temp and rocrate_path.exists():
                rocrate_path.unlink()

        # Legacy drafts retain embedded metadata. The opt-in contract never
        # adds it to, or strips any mapped field from, the Dataset candidate.
        timestamp = datetime.now().isoformat()
        mapping_version = 'v2_semantic' if mapping is None else 'sha256:' + mapping['sha256']
        metadata = None
        if self.config.preserve_provenance:
            metadata = {
                'source': source_path,
                'source_type': 'rocrate',
                'transformation_date': timestamp,
                'mapping_version': mapping_version,
                'profile_level': self.config.profile_level,
                'coverage_percentage': coverage_percentage,
                'unmapped_fields': deepcopy(unmapped_fields) if mapping is not None else unmapped_fields,
                'transformer_version': 'semantic_transformer_1.0'
            }
            if marked_creators:
                metadata['coverage_basis'] = deepcopy(basis)
            if mapping is None:
                d4d_dict['transformation_metadata'] = metadata
            else:
                metadata.update(result_contract=contract, mapping=mapping, publication=None)

        # Validate output if requested
        validation_passed = None
        validation_errors = None

        if validate and self.validator:
            # Save to temp file for validation
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as tmp:
                yaml.safe_dump(d4d_dict, tmp, indent=self.config.output_indent, sort_keys=False)
                tmp_path = Path(tmp.name)

            try:
                validation_reports = self.validator.validate_all(
                    tmp_path,
                    format="yaml",
                    schema="d4d",
                    target_class="Dataset",
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
            if validation_passed is False:
                raise PublicationError(
                    f"Input {source_path}; output {output_path}: requested Dataset "
                    f"validation failed: {validation_errors}")
            raw = prepare_dataset(d4d_dict, context=f"Input {source_path}; output {output_path}",
                                  encoding=self.config.output_encoding,
                                  indent=self.config.output_indent, sort_keys=False)
            if mapping is not None:
                self._mapping_identity()
            publish([(Path(output_path), raw)],
                    protected=[self.config.mapping_file, rocrate_path])
            if mapping is not None and metadata is not None:
                metadata['publication'] = _publication_binding(output_path, raw, self.config.output_encoding)

        if mapping is not None:
            self._mapping_identity()

        # Return result
        result_type = (CreatorReferenceTransformationResult if references is not None
                       else TransformationResult)
        reference_fields = ({'creator_reference_construction': references}
                            if references is not None else {})
        return result_type(
            data=d4d_dict,
            source=source_path,
            target="d4d",
            timestamp=datetime.now().isoformat() if mapping is None else timestamp,
            mapping_version=mapping_version,
            coverage_percentage=coverage_percentage,
            unmapped_fields=unmapped_fields,
            validation_passed=validation_passed,
            validation_errors=validation_errors,
            transformation_metadata=d4d_dict.get('transformation_metadata') if mapping is None else metadata,
            coverage_basis=basis, source_presence=source_presence, **reference_fields
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
        validate: Optional[bool] = None,
        *,
        result_contract: Optional[str] = None
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
            result_contract: dataset_v1 returns a versioned data/metadata envelope;
                legacy preserves Dataset/metadata placement. Both envelopes expose
                a separate source_presence diagnostic.

        Returns:
            Legacy: 'd4d', 'merge_report', 'source_presence'. dataset_v1:
            'format', 'data', 'transformation_metadata', 'merge_report',
            'source_presence'. No merged coverage percentage is measured.
        """
        contract = self._contract(result_contract)
        mapping = self._mapping_identity() if contract == "dataset_v1" else None
        if not SCRIPTS_AVAILABLE:
            raise RuntimeError("Transformation scripts not available. Check imports.")

        if self.mapping_loader is None:
            raise RuntimeError("Mapping loader not initialized. Check mapping file path.")

        validate = validate if validate is not None else self.config.validate_output

        # Parse all RO-Crates
        parsers = []
        source_names = []
        for rocrate_path in rocrate_inputs:
            parser = _parse_rocrate(rocrate_path)
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
        source_presence = merger.get_source_presence()
        references = merger.get_creator_reference_construction()
        reference_fields = ({'creator_reference_construction': references}
                            if references is not None else {})

        # Metadata is separate only in the explicitly selected contract.
        metadata = None
        if self.config.preserve_provenance:
            metadata = {
                'sources': [str(p) for p in rocrate_inputs],
                'source_type': 'rocrate_merge',
                'merge_strategy': self.config.merge_strategy,
                'transformation_date': datetime.now().isoformat(),
                'mapping_version': 'v2_semantic',
                'profile_level': self.config.profile_level,
                'transformer_version': 'semantic_transformer_1.0'
            }
            if mapping is None:
                merged_d4d['transformation_metadata'] = metadata
            else:
                # merge_strategy is a legacy configuration declaration, not
                # a switch passed to the per-field merger.
                metadata['configured_merge_strategy'] = metadata.pop('merge_strategy')
                metadata.update(result_contract=contract, mapping=mapping,
                                mapping_version='sha256:' + mapping['sha256'],
                                source_order=[str(parser.rocrate_path) for parser in parsers],
                                publication=None)

        # Validate merged result if requested
        validation_passed = None
        validation_errors = []
        if validate and self.validator:
            # Save to temp file for validation
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as tmp:
                yaml.safe_dump(merged_d4d, tmp, indent=self.config.output_indent, sort_keys=False)
                tmp_path = Path(tmp.name)

            try:
                validation_reports = self.validator.validate_all(
                    tmp_path,
                    format="yaml",
                    schema="d4d",
                    target_class="Dataset",
                    skip_levels=[ValidationLevel.PROFILE, ValidationLevel.ROUNDTRIP]
                )

                validation_passed = all(r.passed for r in validation_reports.values())
                if not validation_passed:
                    print("Warning: Merged D4D validation failed")
                    for report in validation_reports.values():
                        if not report.passed:
                            validation_errors.extend(report.errors)
                            print(f"  {report.level.value}: {', '.join(report.errors)}")
            finally:
                tmp_path.unlink()

        # Save to output file if requested
        if output_path:
            if validation_passed is False:
                raise PublicationError(
                    f"Inputs {rocrate_inputs}; output {output_path}: requested Dataset "
                    f"validation failed: {validation_errors}")
            raw = prepare_dataset(merged_d4d, context=f"Inputs {rocrate_inputs}; output {output_path}",
                                  encoding=self.config.output_encoding,
                                  indent=self.config.output_indent, sort_keys=False)
            if mapping is not None:
                self._mapping_identity()
            publish([(Path(output_path), raw)],
                    protected=[self.config.mapping_file, *rocrate_inputs])
            if mapping is not None and metadata is not None:
                metadata['publication'] = _publication_binding(output_path, raw, self.config.output_encoding)

        if mapping is not None:
            self._mapping_identity()
            return {'format': RESULT_FORMAT, 'data': merged_d4d,
                    'transformation_metadata': metadata, 'merge_report': merge_report,
                    'source_presence': source_presence, **reference_fields}

        return {
            'd4d': merged_d4d,
            'merge_report': merge_report,
            'source_presence': source_presence, **reference_fields
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
    profile_level: str = "basic",
    *,
    result_contract: str = "legacy",
    mapping_file: Optional[Union[Path, str]] = None
) -> TransformationResult:
    """
    Convenience function to transform a single RO-Crate file to D4D YAML.

    Args:
        input_path: Path to RO-Crate JSON-LD file
        output_path: Path to save D4D YAML
        validate: Run validation on output
        profile_level: RO-Crate profile level
        result_contract: legacy or the explicit dataset_v1 metadata separation
        mapping_file: Explicit TSV path; None retains the existing default table

    Returns:
        TransformationResult
    """
    _result_contract(result_contract)
    mapping_options = {} if mapping_file is None else {'mapping_file': Path(mapping_file)}
    config = TransformationConfig(
        validate_output=validate,
        profile_level=profile_level,
        result_contract=result_contract,
        **mapping_options
    )
    transformer = SemanticTransformer(config)
    return transformer.rocrate_to_d4d(
        Path(input_path),
        output_path=Path(output_path),
        result_contract=result_contract
    )


def batch_transform_rocrates(
    input_dir: Union[Path, str],
    output_dir: Union[Path, str],
    pattern: str = "*.json",
    validate: bool = True,
    *,
    result_contract: str = "legacy",
    mapping_file: Optional[Union[Path, str]] = None
) -> List[TransformationResult]:
    """
    Batch transform all RO-Crate files in a directory.

    Args:
        input_dir: Directory containing RO-Crate JSON-LD files
        output_dir: Directory to save D4D YAML files
        pattern: File pattern to match (default: "*.json")
        validate: Run validation on outputs
        result_contract: legacy or the explicit dataset_v1 metadata separation
        mapping_file: Explicit TSV path; None retains the existing default table

    Returns:
        List of TransformationResults
    """
    contract = _result_contract(result_contract)
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Refuse an invalid later source before an earlier source can overwrite
    # its destination. Keep inspect-only parsers permissive; this is a
    # Dataset-producing batch (#4588, #4591).
    rocrate_files = sorted(input_path.glob(pattern))
    for rocrate_file in rocrate_files:
        _parse_rocrate(rocrate_file).require_root_dataset()

    mapping_options = {} if mapping_file is None else {'mapping_file': Path(mapping_file)}
    config = TransformationConfig(validate_output=validate, result_contract=contract, **mapping_options)
    transformer = SemanticTransformer(config)
    prepared = []
    results = []
    for rocrate_file in rocrate_files:
        out_file = output_path / f"{rocrate_file.stem}_d4d.yaml"
        result = transformer.rocrate_to_d4d(rocrate_file, result_contract=contract)
        if result.validation_passed is False:
            raise PublicationError(
                f"Input {rocrate_file}; output {out_file}: requested Dataset "
                f"validation failed: {result.validation_errors}")
        prepared.append((out_file, prepare_dataset(
            result.data, context=f"Input {rocrate_file}; output {out_file}",
            encoding=config.output_encoding,
            indent=config.output_indent, sort_keys=False)))
        results.append(result)
    if contract == "dataset_v1":
        transformer._mapping_identity()
    publish(prepared, protected=[config.mapping_file, *rocrate_files])
    if contract == "dataset_v1":
        transformer._mapping_identity()
        for result, (out_file, raw) in zip(results, prepared):
            if result.transformation_metadata is not None:
                result.transformation_metadata['publication'] = _publication_binding(
                    out_file, raw, config.output_encoding)
    for rocrate_file, (out_file, _) in zip(rocrate_files, prepared):
        print(f"✓ Transformed: {rocrate_file.name} → {out_file.name}")

    return results


# ==============================================================================
# CLI Interface
# ==============================================================================

def main(argv=None):
    """Keep Dataset YAML on disk; emit a JSON result only on explicit opt-in."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('transform', 'batch', 'merge'):
        command = commands.add_parser(name)
        command.add_argument('--result-contract', choices=sorted(RESULT_CONTRACTS), default='legacy')
        command.add_argument('--mapping', type=Path,
                             help='Explicit mapping TSV (default table remains unchanged)')
        if name == 'merge':
            command.add_argument('output')
            command.add_argument('inputs', nargs='+')
        else:
            command.add_argument('input')
            command.add_argument('output')
    commands.add_parser('stats')
    args = parser.parse_args(argv)
    if args.command == 'merge' and len(args.inputs) < 2:
        parser.error('merge requires at least two input paths')
    contract = getattr(args, 'result_contract', 'legacy')

    def perform():
        if args.command == 'transform':
            return transform_rocrate_file(args.input, args.output, result_contract=contract,
                                          mapping_file=args.mapping)
        if args.command == 'batch':
            return batch_transform_rocrates(args.input, args.output, result_contract=contract,
                                           mapping_file=args.mapping)
        mapping = getattr(args, 'mapping', None)
        mapping_options = {} if mapping is None else {'mapping_file': mapping}
        transformer = SemanticTransformer(TransformationConfig(result_contract=contract, **mapping_options))
        if args.command == 'merge':
            return transformer.merge_rocrates(
                [Path(item) for item in args.inputs], output_path=Path(args.output),
                result_contract=contract)
        return transformer.get_mapping_stats()

    if contract == 'dataset_v1':
        # Imported legacy components print progress. Keep the opted-in stdout
        # parseable, including construction, validation and batch publication.
        with redirect_stdout(sys.stderr):
            result = perform()
        if args.command == 'transform':
            document = {'format': RESULT_FORMAT, **asdict(result)}
            reference_output = isinstance(result, CreatorReferenceTransformationResult)
        elif args.command == 'batch':
            document = {'format': RESULT_FORMAT, 'results': [asdict(item) for item in result]}
            reference_output = any(isinstance(item, CreatorReferenceTransformationResult)
                                   for item in result)
        else:
            document = result
            reference_output = 'creator_reference_construction' in result
        # Only the new reference policy carries arbitrary matched-member JSON.
        # ASCII escaping preserves those parsed values, including lone surrogate
        # escapes, without changing the older result policies' wire spelling.
        print(json.dumps(document, ensure_ascii=reference_output, indent=2))
        return

    result = perform()
    if args.command == "transform":
        print(f"✓ Transformation complete")
        print(f"  {VALUE_BASIS_LABEL}: {result.coverage_percentage:.1f}%")
        print(f"  {MEASUREMENT_LIMIT}")
        print('\n'.join(source_presence_lines(result.source_presence, raw=False)))
        if getattr(result, 'creator_reference_construction', None) is not None:
            print('\n'.join(reference_lines(getattr(result, 'creator_reference_construction', None))))
        if result.validation_passed is not None:
            print(f"  Validation: {'PASS' if result.validation_passed else 'FAIL'}")

    elif args.command == "batch":
        print(f"\n✓ Batch transformation complete: {len(result)} files")
        for item in result:
            print(f"  {item.source}: {VALUE_BASIS_LABEL}: {item.coverage_percentage:.1f}%")
            print('\n'.join(source_presence_lines(item.source_presence, raw=False)))
            if getattr(item, 'creator_reference_construction', None) is not None:
                print('\n'.join(reference_lines(getattr(item, 'creator_reference_construction', None))))
        print(MEASUREMENT_LIMIT)
    elif args.command == "merge":
        print(f"✓ Merged {len(args.inputs)} RO-Crates → {args.output}")
        print('\n'.join(source_presence_lines(result['source_presence'], raw=False)))
        if 'creator_reference_construction' in result:
            print('\n'.join(reference_lines(result.get('creator_reference_construction'))))
    elif args.command == "stats":
        print("\nMapping Statistics:")
        print("=" * 50)
        for key, value in result.items():
            print(f"  {key}: {value}")


if __name__ == '__main__':
    main()
