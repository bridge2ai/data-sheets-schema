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

# Import our modules
from mapping_loader import MappingLoader
from rocrate_parser import ROCrateParser
from d4d_builder import D4DBuilder
from validator import D4DValidator
from rocrate_merger import ROCrateMerger
from informativeness_scorer import InformativenessScorer


def generate_transformation_report(
    rocrate_parser: ROCrateParser,
    d4d_builder: D4DBuilder,
    mapping_loader: MappingLoader,
    output_dir: Path
) -> Path:
    """Generate report of unmapped fields and transformation summary."""
    report_path = output_dir / "transformation_report.txt"

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("RO-Crate to D4D Transformation Report\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("="*80 + "\n\n")

        # Transformation summary
        covered_fields = mapping_loader.get_covered_fields()
        dataset = d4d_builder.get_dataset()

        f.write("TRANSFORMATION SUMMARY\n")
        f.write("-"*80 + "\n")
        f.write(f"Total D4D fields in mapping: {len(covered_fields)}\n")
        f.write(f"Fields populated from RO-Crate: {len(dataset)}\n")
        f.write(f"Coverage: {len(dataset)}/{len(covered_fields)} ")
        f.write(f"({len(dataset)/len(covered_fields)*100:.1f}%)\n\n")

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
            f.write("iterations to improve D4D coverage.\n")

    print(f"\n✓ Transformation report saved: {report_path}")
    return report_path


def save_d4d_yaml(
    dataset: Dict[str, Any],
    output_path: Path,
    mapping_path: Path,
    rocrate_path: Path = None,
    rocrate_paths: List[Path] = None,
    provenance: Dict[str, List[str]] = None
):
    """Save D4D dataset to YAML file with metadata header."""
    with open(output_path, 'w', encoding='utf-8') as f:
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

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

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
                if not parser.get_root_dataset():
                    print(f"⚠ Warning: No root Dataset in {input_path.name}, skipping")
                    continue
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

        # Save with provenance
        print("\n[5/5] Saving merged D4D YAML...")
        try:
            save_d4d_yaml(
                dataset,
                output_path,
                mapping_path,
                rocrate_paths=input_paths,
                provenance=provenance
            )
        except Exception as e:
            print(f"✗ Error saving YAML: {e}", file=sys.stderr)
            return 1

        # Generate merge report
        if not args.no_report:
            try:
                merger.save_merge_report(output_path, parsers)
            except Exception as e:
                print(f"⚠ Warning: Could not generate merge report: {e}", file=sys.stderr)

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
        except Exception as e:
            print(f"✗ Error parsing RO-Crate: {e}", file=sys.stderr)
            return 1

        if not rocrate.get_root_dataset():
            print("✗ Error: No root Dataset found in RO-Crate", file=sys.stderr)
            return 1

        # Step 3: Build D4D structure
        print("\n[3/5] Building D4D structure...")
        try:
            builder = D4DBuilder(mapping)
            dataset = builder.build_dataset(rocrate)
        except Exception as e:
            print(f"✗ Error building D4D: {e}", file=sys.stderr)
            return 1

        # Step 4: Save D4D YAML
        print("\n[4/5] Saving D4D YAML...")
        try:
            save_d4d_yaml(dataset, output_path, mapping_path, rocrate_path=input_path)
        except Exception as e:
            print(f"✗ Error saving YAML: {e}", file=sys.stderr)
            return 1

        # Step 5: Generate report
        print("\n[5/5] Generating reports...")
        if not args.no_report:
            try:
                generate_transformation_report(rocrate, builder, mapping, output_path.parent)
            except Exception as e:
                print(f"⚠ Warning: Could not generate report: {e}", file=sys.stderr)

    # Common validation step for both modes
    if args.strict:
        # Minimal required fields for D4D
        required = ['title', 'description']
        missing = [f for f in required if not dataset.get(f)]

        if missing:
            print(f"\n✗ Error: Missing required fields: {', '.join(missing)}", file=sys.stderr)
            print("Run without --strict flag or provide missing fields manually", file=sys.stderr)
            return 1

    if args.validate:
        if not schema_path.exists():
            print(f"⚠ Warning: Schema not found, skipping validation: {schema_path}", file=sys.stderr)
        else:
            print("\n" + "="*80)
            print("Validating D4D YAML...")
            print("="*80 + "\n")

            try:
                validator = D4DValidator(str(schema_path))
                is_valid, output = validator.validate_d4d_yaml(str(output_path))

                print(validator.get_validation_summary(is_valid, output))

                if not is_valid:
                    # Save validation errors to file
                    error_path = output_path.parent / f"{output_path.stem}_validation_errors.txt"
                    with open(error_path, 'w') as f:
                        f.write(output)
                    print(f"\n⚠ Validation errors saved to: {error_path}")

                    if args.strict:
                        return 1

            except Exception as e:
                print(f"⚠ Warning: Validation failed: {e}", file=sys.stderr)

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
    print(f"\nFields populated: {len(dataset)}")
    print(f"Coverage: {len(dataset)}/{len(mapping.get_covered_fields())} mapped fields")
    print(f"Percentage: {len(dataset)/len(mapping.get_covered_fields())*100:.1f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
