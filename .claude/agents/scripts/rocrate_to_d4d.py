#!/usr/bin/env python3
"""
RO-Crate to D4D Transformation Script

Transform RO-Crate JSON-LD metadata files into D4D YAML datasheets using
the authoritative TSV mapping file.

Supports both single-file and multi-file (merge) modes:
- Single mode: Transform one RO-Crate to D4D
- Merge mode: Intelligently merge multiple RO-Crates into comprehensive D4D

Usage:
    # Single file
    python rocrate_to_d4d.py \\
        --input <rocrate.json> \\
        --output <output.yaml> \\
        --mapping <mapping.tsv> \\
        --validate

    # Multi-file merge
    python rocrate_to_d4d.py \\
        --merge \\
        --inputs <rocrate1.json> <rocrate2.json> <rocrate3.json> \\
        --output <output.yaml> \\
        --mapping <mapping.tsv> \\
        --auto-prioritize \\
        --validate
"""

import argparse
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from io import StringIO

# Import our modules
from mapping_loader import MappingLoader
from rocrate_parser import ROCrateParser
from d4d_builder import D4DBuilder
from validator import D4DValidator
from rocrate_merger import ROCrateMerger
from informativeness_scorer import InformativenessScorer
from data_sheets_schema.legacy_publication import prepare_dataset, publish, diagnostic
from data_sheets_schema.legacy_root_identity import root_identity_route, scoring_fields
from data_sheets_schema.legacy_creator_references import reference_evidence, reference_lines
from data_sheets_schema.legacy_creators import (
    author_source_presence, source_presence_lines, KEY_BASIS_LABEL, MEASUREMENT_LIMIT,
)


def render_transformation_report(
    rocrate_parser: ROCrateParser,
    d4d_builder: D4DBuilder,
    mapping_loader: MappingLoader,
) -> str:
    """Generate report of unmapped fields and transformation summary."""
    f = StringIO()
    f.write("="*80 + "\n")
    f.write("RO-Crate to D4D Transformation Report\n")
    f.write(f"Generated: {datetime.now().isoformat()}\n")
    f.write("="*80 + "\n\n")

    # Transformation summary
    covered_fields = scoring_fields(mapping_loader)
    dataset = d4d_builder.get_dataset()
    identity_construction = root_identity_route(mapping_loader)
    populated_count = len(dataset) - int(identity_construction and 'id' in dataset)
    percentage = populated_count / len(covered_fields) * 100 if covered_fields else 0

    f.write("TRANSFORMATION SUMMARY\n")
    f.write("-"*80 + "\n")
    f.write(f"Eligible mapped fields: {len(covered_fields)}\n")
    f.write(f"Constructed output keys: {populated_count}\n")
    f.write(f"{KEY_BASIS_LABEL}: {populated_count}/{len(covered_fields)} ")
    f.write(f"({percentage:.1f}%)\n\n")
    f.write(MEASUREMENT_LIMIT + "\n")
    presence = author_source_presence(
        mapping_loader, [rocrate_parser], [str(rocrate_parser.rocrate_path)])
    f.write("\n".join(source_presence_lines(presence)) + "\n")
    references = reference_evidence(
        presence, [d4d_builder.get_creator_reference_construction()])
    if references is not None:
        f.write("\n".join(reference_lines(references)) + "\n")
    if identity_construction:
        f.write("Required Dataset.id construction is excluded from this count.\n\n")

    # Unmapped RO-Crate properties
    mapped_props = mapping_loader.get_all_mapped_rocrate_properties()
    unmapped = rocrate_parser.get_unmapped_properties(mapped_props)

    f.write("UNMAPPED RO-CRATE PROPERTIES\n")
    f.write("-"*80 + "\n")
    f.write(f"Found {len(unmapped)} properties in RO-Crate with no D4D mapping:\n\n")

    for prop_path, sample_value in sorted(unmapped.items()):
        f.write(f"  • {prop_path}\n")
        f.write(f"    Sample value: {sample_value}\n\n")

    if unmapped:
        f.write("\nThese properties could be added to the mapping TSV for future ")
        f.write("iterations to add mapping routes; this alone adds no source evidence.\n")

    return f.getvalue()

def prepare_d4d_yaml(
    dataset: Dict[str, Any],
    output_path: Path,
    mapping_path: Path,
    rocrate_path: Path = None,
    rocrate_paths: List[Path] = None,
    provenance: Dict[str, List[str]] = None
):
    """Render and validate bytes, including the existing provenance header."""
    f = StringIO()
    # Write metadata header
    f.write("# D4D Datasheet Generated from RO-Crate\n")

    if rocrate_paths:
        # Multi-file merge mode
        f.write(f"# Primary source: {rocrate_paths[0].name}\n")
        if len(rocrate_paths) > 1:
            f.write("# Additional sources:\n")
            for path in rocrate_paths[1:]:
                f.write(f"#   - {path.name}\n")
        f.write(f"# Merged: {datetime.now().isoformat()}\n")
    elif rocrate_path:
        # Single file mode
        f.write(f"# Source: {rocrate_path.name}\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")

    f.write(f"# Mapping: {mapping_path.name}\n")
    f.write(f"# Generator: d4d-rocrate skill\n")

    # Add provenance if available
    if provenance:
        f.write("\n# Field provenance (which sources contributed):\n")
        for field, sources in sorted(provenance.items()):
            sources_str = ", ".join(sources)
            f.write(f"#   {field}: {sources_str}\n")

    f.write("\n")

    # Write YAML data (use safe_dump to handle special characters)
    yaml.safe_dump(
        dataset,
        f,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False
    )

    return prepare_dataset(dataset, text=f.getvalue(),
                           context=f"Inputs {rocrate_paths or rocrate_path}; output {output_path}")



def generate_transformation_report(rocrate_parser, d4d_builder, mapping_loader, output_dir):
    """Publish a report only after its final Dataset passes the required gate."""
    prepare_dataset(d4d_builder.get_dataset())
    path = Path(output_dir) / "transformation_report.txt"
    raw = render_transformation_report(rocrate_parser, d4d_builder, mapping_loader).encode("utf-8")
    publish([(path, raw)], protected=[rocrate_parser.rocrate_path, mapping_loader.tsv_path])
    print(f"\n✓ Transformation report saved: {path}")
    return path


def save_d4d_yaml(dataset, output_path, mapping_path, rocrate_path=None,
                  rocrate_paths=None, provenance=None):
    raw = prepare_d4d_yaml(dataset, output_path, mapping_path, rocrate_path,
                           rocrate_paths, provenance)
    publish([(Path(output_path), raw)],
            protected=[mapping_path, *(rocrate_paths or ([rocrate_path] if rocrate_path else []))])
    print(f"\n✓ D4D YAML saved: {output_path}")

def main():
    """Main transformation orchestrator."""
    parser = argparse.ArgumentParser(
        description="Transform RO-Crate JSON-LD to D4D YAML datasheet (single or multi-file merge)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single file transformation
  python rocrate_to_d4d.py \\
      --input data/raw/CM4AI/ro-crate-metadata.json \\
      --output output/CM4AI_d4d.yaml \\
      --mapping data/ro-crate_mapping/mapping.tsv

  # Multi-file merge with auto-prioritization
  python rocrate_to_d4d.py \\
      --merge \\
      --inputs \\
        data/ro-crate/CM4AI/release-ro-crate-metadata.json \\
        data/ro-crate/CM4AI/mass-spec-iPSCs-ro-crate-metadata.json \\
        data/ro-crate/CM4AI/mass-spec-cancer-cells-ro-crate-metadata.json \\
      --output data/d4d_concatenated/rocrate/CM4AI_comprehensive_d4d.yaml \\
      --mapping data/ro-crate_mapping/mapping.tsv \\
      --auto-prioritize \\
      --validate

  # Multi-file merge with specific primary source
  python rocrate_to_d4d.py \\
      --merge \\
      --inputs file1.json file2.json file3.json \\
      --primary 0 \\
      --output merged.yaml \\
      --mapping mapping.tsv
        """
    )

    # Single vs multi-file mode selection
    parser.add_argument(
        '--merge',
        action='store_true',
        help='Enable multi-file merge mode (requires --inputs)'
    )

    parser.add_argument(
        '-i', '--input',
        help='Path to RO-Crate JSON-LD file (single-file mode)'
    )

    parser.add_argument(
        '--inputs',
        nargs='+',
        help='Multiple RO-Crate input files (multi-file merge mode)'
    )

    parser.add_argument(
        '--primary',
        type=int,
        default=0,
        help='Index of primary source for merge (default: 0 = first file)'
    )

    parser.add_argument(
        '--auto-prioritize',
        action='store_true',
        help='Automatically rank sources by informativeness (merge mode only)'
    )

    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Path for output D4D YAML file'
    )

    parser.add_argument(
        '-m', '--mapping',
        required=True,
        help='Path to mapping TSV file'
    )

    parser.add_argument(
        '-s', '--schema',
        default='src/data_sheets_schema/schema/data_sheets_schema_all.yaml',
        help='Path to D4D schema YAML (default: %(default)s)'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate output against D4D schema'
    )

    parser.add_argument(
        '--strict',
        action='store_true',
        help='Fail on missing required D4D fields'
    )

    parser.add_argument(
        '--no-report',
        action='store_true',
        help='Skip generation of transformation report'
    )

    args = parser.parse_args()

    # Validate mode and inputs
    if args.merge:
        if not args.inputs:
            print("✗ Error: --merge requires --inputs with multiple files", file=sys.stderr)
            return 1
        if len(args.inputs) < 2:
            print("✗ Warning: Merge mode with single file, using single-file mode instead")
            args.merge = False
            args.input = args.inputs[0]
    else:
        if not args.input:
            print("✗ Error: Single-file mode requires --input", file=sys.stderr)
            return 1

    # Validate paths
    mapping_path = Path(args.mapping)
    schema_path = Path(args.schema)
    output_path = Path(args.output)

    if not mapping_path.exists():
        print(f"✗ Error: Mapping TSV not found: {mapping_path}", file=sys.stderr)
        return 1

    print("="*80)
    if args.merge:
        print("Multi-RO-Crate Merge to D4D")
    else:
        print("RO-Crate to D4D Transformation")
    print("="*80)

    # Step 1: Load mapping
    print("\n[1/5] Loading mapping...")
    try:
        mapping = MappingLoader(str(mapping_path))
    except Exception as e:
        print(f"✗ Error loading mapping: {e}", file=sys.stderr)
        return 1

    # Branch based on mode
    if args.merge:
        # ========== MULTI-FILE MERGE MODE ==========
        # Validate all input files
        input_paths = [Path(p) for p in args.inputs]
        for input_path in input_paths:
            if not input_path.exists():
                print(f"✗ Error: RO-Crate file not found: {input_path}", file=sys.stderr)
                return 1

        # Step 2: Parse all RO-Crates
        print(f"\n[2/5] Parsing {len(input_paths)} RO-Crate files...")
        try:
            parsers = []
            for input_path in input_paths:
                print(f"  - {input_path.name}")
                parser = ROCrateParser(str(input_path))
                # Every requested source participates or the whole operation
                # fails. Skipping one silently changes the published merge.
                parser.require_root_dataset()
                parsers.append(parser)

            if not parsers:
                print("✗ Error: No valid RO-Crate files with root Dataset", file=sys.stderr)
                return 1

        except Exception as e:
            print(f"✗ Error parsing RO-Crates: {e}", file=sys.stderr)
            return 1

        # Step 3: Optionally rank by informativeness
        primary_index = args.primary
        if args.auto_prioritize:
            print("\n[3/5] Ranking sources by informativeness...")
            try:
                scorer = InformativenessScorer()
                ranked = scorer.rank_rocrates(parsers, mapping)
                scorer.print_ranking_report(ranked)

                # Re-order parsers and input_paths by rank
                parsers = [p for p, _, _ in ranked]
                input_paths = [Path(p.rocrate_path) for p in parsers]
                primary_index = 0  # First in ranked list is primary

                print(f"\n✓ Primary source: {input_paths[0].name}")

            except Exception as e:
                print(f"⚠ Warning: Could not rank sources: {e}", file=sys.stderr)
                print("Proceeding with original order...")
        else:
            print(f"\n[3/5] Using sources in provided order (primary index: {primary_index})...")

        # Step 4: Merge RO-Crates
        print("\n[4/5] Merging RO-Crates...")
        try:
            merger = ROCrateMerger(mapping)
            dataset = merger.merge_rocrates(parsers, primary_index=primary_index)
            provenance = merger.get_provenance()
            merge_stats = merger.get_merge_stats()

            print(f"\n✓ Merged {merge_stats['total_unique_fields']} unique fields from {merge_stats['total_sources']} sources")

        except Exception as e:
            print(f"✗ Error merging RO-Crates: {e}", file=sys.stderr)
            return 1

        header_paths = [input_paths[primary_index]] + [
            path for i, path in enumerate(input_paths) if i != primary_index
        ]
        try:
            raw = prepare_d4d_yaml(dataset, output_path, mapping_path,
                                   rocrate_paths=header_paths, provenance=provenance)
            prepared = [(output_path, raw)]
            if not args.no_report:
                report_path = output_path.with_name(f"{output_path.stem}_merge_report.txt")
                prepared.append((report_path, merger.generate_merge_report(parsers).encode("utf-8")))
        except Exception as exc:
            print(f"✗ Error preparing publication: {exc}", file=sys.stderr)
            return 1

    else:
        # ========== SINGLE-FILE MODE ==========
        input_path = Path(args.input)

        if not input_path.exists():
            print(f"✗ Error: RO-Crate file not found: {input_path}", file=sys.stderr)
            return 1

        # Step 2: Parse RO-Crate
        print("\n[2/5] Parsing RO-Crate...")
        try:
            rocrate = ROCrateParser(str(input_path))
            rocrate.require_root_dataset()
        except Exception as e:
            print(f"✗ Error parsing RO-Crate: {e}", file=sys.stderr)
            return 1

        # Step 3: Build D4D structure
        print("\n[3/5] Building D4D structure...")
        try:
            builder = D4DBuilder(mapping)
            dataset = builder.build_dataset(rocrate)
        except Exception as e:
            print(f"✗ Error building D4D: {e}", file=sys.stderr)
            return 1

        try:
            raw = prepare_d4d_yaml(dataset, output_path, mapping_path, rocrate_path=input_path)
            prepared = [(output_path, raw)]
            if not args.no_report:
                report_path = output_path.parent / "transformation_report.txt"
                report = render_transformation_report(rocrate, builder, mapping).encode("utf-8")
                prepared.append((report_path, report))
        except Exception as exc:
            print(f"✗ Error preparing publication: {exc}", file=sys.stderr)
            return 1

    # Common validation step for both modes
    if args.strict:
        # Minimal required fields for D4D
        required = ['title', 'description']
        missing = [f for f in required if not dataset.get(f)]

        if missing:
            print(f"\n✗ Error: Missing required fields: {', '.join(missing)}", file=sys.stderr)
            print("Run without --strict flag or provide missing fields manually", file=sys.stderr)
            return 1

    try:
        if args.validate:
            validator = D4DValidator(str(schema_path))
            detail = diagnostic(raw, validator.validate_d4d_yaml)
            print(validator.get_validation_summary(True, detail))
        publish(prepared, protected=[mapping_path, schema_path,
                                    *(input_paths if args.merge else [input_path])])
    except Exception as exc:
        print(f"✗ Error publishing Dataset: {exc}", file=sys.stderr)
        return 1
    print(f"\n✓ D4D YAML saved: {output_path}")
    if not args.no_report:
        print(f"✓ Report saved: {report_path}")

    # Final summary
    print("\n" + "="*80)
    if args.merge:
        print("Multi-RO-Crate Merge Complete")
    else:
        print("Transformation Complete")
    print("="*80)

    if args.merge:
        print(f"\nSources: {len(args.inputs)} RO-Crate files")
        print(f"Primary: {Path(args.inputs[args.primary]).name if not args.auto_prioritize else input_paths[0].name}")
    else:
        print(f"\nInput:  {Path(args.input).name}")

    print(f"Output: {output_path}")
    print(f"\nConstructed Dataset keys: {len(dataset)}")
    covered_fields = scoring_fields(mapping)
    identity_construction = root_identity_route(mapping)
    populated_count = len(dataset) - int(identity_construction and 'id' in dataset)
    percentage = populated_count / len(covered_fields) * 100 if covered_fields else 0
    print(f"{KEY_BASIS_LABEL}: {populated_count}/{len(covered_fields)} mapped fields")
    print(f"Construction percentage: {percentage:.1f}%")
    print(MEASUREMENT_LIMIT)
    presence = (merger.get_source_presence() if args.merge else
                author_source_presence(mapping, [rocrate], [str(input_path)]))
    print("\n".join(source_presence_lines(presence, raw=False)))
    references = (merger.get_creator_reference_construction() if args.merge else
                  reference_evidence(presence, [builder.get_creator_reference_construction()]))
    if references is not None:
        print("\n".join(reference_lines(references)))
    if identity_construction:
        print("Required Dataset.id construction is excluded from this count.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
