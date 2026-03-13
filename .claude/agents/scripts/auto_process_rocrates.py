#!/usr/bin/env python3
"""
Auto-Process RO-Crates - Automated discovery and processing of RO-Crate files.

This script automatically:
1. Discovers all RO-Crate files in a directory
2. Ranks them by informativeness
3. Processes them using selected strategy (merge, concatenate, or hybrid)

Usage:
    # Auto-discover and merge all RO-Crates in directory
    python auto_process_rocrates.py \\
        --input-dir data/ro-crate/CM4AI \\
        --output data/d4d_concatenated/rocrate/CM4AI_d4d.yaml \\
        --mapping data/ro-crate_mapping/mapping.tsv \\
        --strategy merge

    # Concatenate top 3 most informative RO-Crates
    python auto_process_rocrates.py \\
        --input-dir data/ro-crate/CM4AI \\
        --output data/d4d_concatenated/rocrate/CM4AI_d4d.yaml \\
        --mapping data/ro-crate_mapping/mapping.tsv \\
        --strategy concatenate \\
        --top-n 3
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple

from informativeness_scorer import InformativenessScorer
from mapping_loader import MappingLoader
from rocrate_parser import ROCrateParser
from rocrate_merger import ROCrateMerger
from d4d_builder import D4DBuilder


def discover_rocrates(input_dir: Path) -> List[Path]:
    """
    Discover all RO-Crate JSON files in a directory.

    Args:
        input_dir: Directory to search

    Returns:
        List of RO-Crate file paths
    """
    patterns = [
        '*ro-crate-metadata.json',
        '*-ro-crate-metadata.json',
        'ro-crate-metadata.json'
    ]

    rocrate_files = []
    for pattern in patterns:
        rocrate_files.extend(input_dir.glob(pattern))

    # Deduplicate and sort
    rocrate_files = sorted(set(rocrate_files))

    return rocrate_files


def rank_rocrates(
    rocrate_paths: List[Path],
    mapping_loader: MappingLoader
) -> List[Tuple[Path, float, int]]:
    """
    Rank RO-Crates by informativeness.

    Args:
        rocrate_paths: List of RO-Crate file paths
        mapping_loader: MappingLoader instance

    Returns:
        List of (path, score, rank) tuples sorted by rank
    """
    print(f"\nLoading and ranking {len(rocrate_paths)} RO-Crate files...")

    # Parse all RO-Crates
    parsers = []
    for path in rocrate_paths:
        try:
            parser = ROCrateParser(str(path))
            if parser.get_root_dataset():
                parsers.append(parser)
            else:
                print(f"⚠ Warning: No root Dataset in {path.name}, skipping")
        except Exception as e:
            print(f"⚠ Warning: Could not parse {path.name}: {e}")
            continue

    if not parsers:
        raise ValueError("No valid RO-Crate files found")

    # Score and rank
    scorer = InformativenessScorer()
    ranked_parsers = scorer.rank_rocrates(parsers, mapping_loader)

    # Convert back to paths with scores
    ranked_paths = []
    for parser, scores, rank in ranked_parsers:
        path = Path(parser.rocrate_path)
        score = scores['total_score']
        ranked_paths.append((path, score, rank))

    return ranked_paths


def concatenate_rocrates(
    rocrate_paths: List[Path],
    output_path: Path
) -> Path:
    """
    Concatenate multiple RO-Crate files into single JSON.

    Args:
        rocrate_paths: List of RO-Crate file paths
        output_path: Output path for concatenated file

    Returns:
        Path to concatenated file
    """
    print(f"\nConcatenating {len(rocrate_paths)} RO-Crate files...")

    concatenated = {
        "@context": "https://w3id.org/ro/crate/1.1/context",
        "@graph": []
    }

    for i, path in enumerate(rocrate_paths):
        print(f"  [{i+1}/{len(rocrate_paths)}] {path.name}")

        with open(path, 'r', encoding='utf-8') as f:
            rocrate_data = json.load(f)

        # Add source marker
        graph = rocrate_data.get('@graph', [])
        for entity in graph:
            # Tag each entity with its source file
            if '@id' not in entity:
                continue
            entity['_source'] = path.name

        concatenated['@graph'].extend(graph)

    # Save concatenated file
    concat_path = output_path.parent / f"{output_path.stem}_concatenated.json"
    with open(concat_path, 'w', encoding='utf-8') as f:
        json.dump(concatenated, f, indent=2)

    print(f"\n✓ Concatenated RO-Crate saved: {concat_path}")
    return concat_path


def main():
    """Main orchestrator for automated RO-Crate processing."""
    parser = argparse.ArgumentParser(
        description="Automatically discover and process RO-Crate files",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '-i', '--input-dir',
        required=True,
        help='Directory containing RO-Crate files'
    )

    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output path for D4D YAML file'
    )

    parser.add_argument(
        '-m', '--mapping',
        required=True,
        help='Path to mapping TSV file'
    )

    parser.add_argument(
        '--strategy',
        choices=['merge', 'concatenate', 'hybrid'],
        default='merge',
        help='Processing strategy (default: merge)'
    )

    parser.add_argument(
        '--top-n',
        type=int,
        help='Process only top N most informative RO-Crates'
    )

    parser.add_argument(
        '--min-score',
        type=float,
        help='Minimum informativeness score threshold'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate output against D4D schema'
    )

    parser.add_argument(
        '--schema',
        default='src/data_sheets_schema/schema/data_sheets_schema_all.yaml',
        help='Path to D4D schema for validation'
    )

    args = parser.parse_args()

    # Validate paths
    input_dir = Path(args.input_dir)
    output_path = Path(args.output)
    mapping_path = Path(args.mapping)

    if not input_dir.exists():
        print(f"✗ Error: Input directory not found: {input_dir}", file=sys.stderr)
        return 1

    if not mapping_path.exists():
        print(f"✗ Error: Mapping TSV not found: {mapping_path}", file=sys.stderr)
        return 1

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("="*80)
    print("Automated RO-Crate Processing")
    print("="*80)
    print(f"\nStrategy: {args.strategy}")
    print(f"Input:    {input_dir}")
    print(f"Output:   {output_path}")

    # Step 1: Discover RO-Crates
    print("\n[1/5] Discovering RO-Crate files...")
    rocrate_paths = discover_rocrates(input_dir)

    if not rocrate_paths:
        print(f"✗ Error: No RO-Crate files found in {input_dir}", file=sys.stderr)
        return 1

    print(f"Found {len(rocrate_paths)} RO-Crate files:")
    for path in rocrate_paths:
        file_size = path.stat().st_size / 1024  # KB
        print(f"  • {path.name} ({file_size:.1f} KB)")

    # Step 2: Load mapping
    print("\n[2/5] Loading mapping...")
    try:
        mapping = MappingLoader(str(mapping_path))
    except Exception as e:
        print(f"✗ Error loading mapping: {e}", file=sys.stderr)
        return 1

    # Step 3: Rank by informativeness
    print("\n[3/5] Ranking by informativeness...")
    try:
        ranked = rank_rocrates(rocrate_paths, mapping)
    except Exception as e:
        print(f"✗ Error ranking RO-Crates: {e}", file=sys.stderr)
        return 1

    # Display rankings
    print("\nRankings:")
    for path, score, rank in ranked:
        print(f"  {rank}. {path.name} (score: {score:.3f})")

    # Step 4: Filter by top-n or min-score
    selected_paths = [path for path, _, _ in ranked]

    if args.top_n:
        selected_paths = selected_paths[:args.top_n]
        print(f"\n✓ Selected top {len(selected_paths)} RO-Crates")

    if args.min_score:
        selected_paths = [
            path for path, score, _ in ranked
            if score >= args.min_score
        ]
        print(f"\n✓ Selected {len(selected_paths)} RO-Crates above score threshold {args.min_score}")

    # Step 5: Process based on strategy
    print(f"\n[4/5] Processing with '{args.strategy}' strategy...")

    if args.strategy == 'merge':
        # Direct field-by-field merge
        from rocrate_to_d4d import save_d4d_yaml

        parsers = [ROCrateParser(str(p)) for p in selected_paths]
        merger = ROCrateMerger(mapping)
        dataset = merger.merge_rocrates(parsers, primary_index=0)
        provenance = merger.get_provenance()

        save_d4d_yaml(
            dataset,
            output_path,
            mapping_path,
            rocrate_paths=selected_paths,
            provenance=provenance
        )

        merger.save_merge_report(output_path, parsers)

    elif args.strategy == 'concatenate':
        # Concatenate then transform
        from rocrate_to_d4d import save_d4d_yaml

        concat_path = concatenate_rocrates(selected_paths, output_path)

        # Transform concatenated file
        parser = ROCrateParser(str(concat_path))
        builder = D4DBuilder(mapping)
        dataset = builder.build_dataset(parser)

        save_d4d_yaml(
            dataset,
            output_path,
            mapping_path,
            rocrate_path=concat_path
        )

    elif args.strategy == 'hybrid':
        # Merge primary, concatenate secondaries
        print("\n  Hybrid approach:")
        print(f"    - Primary (merge): {selected_paths[0].name}")

        if len(selected_paths) > 1:
            print(f"    - Secondaries (concatenate): {len(selected_paths)-1} files")

            # Concatenate secondaries
            concat_path = concatenate_rocrates(selected_paths[1:], output_path)

            # Merge primary with concatenated secondaries
            from rocrate_to_d4d import save_d4d_yaml

            parsers = [
                ROCrateParser(str(selected_paths[0])),
                ROCrateParser(str(concat_path))
            ]
            merger = ROCrateMerger(mapping)
            dataset = merger.merge_rocrates(parsers, primary_index=0)
            provenance = merger.get_provenance()

            save_d4d_yaml(
                dataset,
                output_path,
                mapping_path,
                rocrate_paths=[selected_paths[0], concat_path],
                provenance=provenance
            )

            merger.save_merge_report(output_path, parsers)

        else:
            # Only one file, treat as single-file mode
            parser = ROCrateParser(str(selected_paths[0]))
            builder = D4DBuilder(mapping)
            dataset = builder.build_dataset(parser)

            from rocrate_to_d4d import save_d4d_yaml
            save_d4d_yaml(
                dataset,
                output_path,
                mapping_path,
                rocrate_path=selected_paths[0]
            )

    # Step 6: Validate if requested
    if args.validate:
        print("\n[5/5] Validating D4D YAML...")
        schema_path = Path(args.schema)

        if not schema_path.exists():
            print(f"⚠ Warning: Schema not found: {schema_path}")
        else:
            from validator import D4DValidator

            validator = D4DValidator(str(schema_path))
            is_valid, output = validator.validate_d4d_yaml(str(output_path))

            print(validator.get_validation_summary(is_valid, output))

            if not is_valid:
                error_path = output_path.parent / f"{output_path.stem}_validation_errors.txt"
                with open(error_path, 'w') as f:
                    f.write(output)
                print(f"\n⚠ Validation errors saved to: {error_path}")

    # Final summary
    print("\n" + "="*80)
    print("Processing Complete")
    print("="*80)
    print(f"\nProcessed: {len(selected_paths)} RO-Crate files")
    print(f"Strategy:  {args.strategy}")
    print(f"Output:    {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
