#!/usr/bin/env python3
"""
Centralized CLI for D4D ↔ RO-Crate operations.

This module provides a unified command-line interface for all FAIRSCAPE/RO-Crate
integration tasks: parsing, converting, validating, and merging.
"""

import sys
import click
from pathlib import Path
from typing import Optional

# Add src to path for imports
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.fairscape_integration.d4d_to_fairscape import D4DToFairscapeConverter
from src.fairscape_integration.fairscape_to_d4d import FairscapeToD4DConverter
from src.fairscape_integration.utils.validator import D4DValidator
from src.fairscape_integration.utils.rocrate_parser import ROCrateParser
from src.fairscape_integration.utils.mapping_loader import MappingLoader
from src.fairscape_integration.utils.d4d_builder import D4DBuilder
from src.fairscape_integration.utils.rocrate_merger import ROCrateMerger
from src.fairscape_integration.utils.informativeness_scorer import InformativenessScorer


@click.group()
@click.version_option()
def cli():
    """
    D4D ↔ RO-Crate integration tools.

    Provides commands for parsing, converting, validating, and merging
    between D4D YAML and RO-Crate JSON-LD formats.
    """
    pass


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('-o', '--output', type=click.Path(), help='Output file path (default: stdout)')
@click.option('--pretty', is_flag=True, help='Pretty-print JSON output')
def d4d_to_rocrate(input_file: str, output: Optional[str], pretty: bool):
    """
    Convert D4D YAML to RO-Crate JSON-LD.

    Reads a D4D YAML file and converts it to RO-Crate JSON-LD format.

    Example:
        fairscape-cli d4d-to-rocrate data/d4d_concatenated/AI_READI_d4d.yaml -o output.json
    """
    import yaml
    import json

    try:
        # Load D4D YAML
        with open(input_file, 'r') as f:
            d4d_data = yaml.safe_load(f)

        # Convert to RO-Crate
        converter = D4DToFairscapeConverter()
        rocrate = converter.convert(d4d_data)

        # Serialize to JSON
        rocrate_dict = rocrate.model_dump(by_alias=True, exclude_none=True)

        if pretty:
            json_output = json.dumps(rocrate_dict, indent=2)
        else:
            json_output = json.dumps(rocrate_dict)

        # Write output
        if output:
            with open(output, 'w') as f:
                f.write(json_output)
            click.echo(f"✓ RO-Crate written to: {output}")
        else:
            click.echo(json_output)

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('-o', '--output', type=click.Path(), help='Output file path (default: stdout)')
def rocrate_to_d4d(input_file: str, output: Optional[str]):
    """
    Convert RO-Crate JSON-LD to D4D YAML.

    Reads a RO-Crate JSON-LD file and converts it to D4D YAML format.

    Example:
        fairscape-cli rocrate-to-d4d ro-crate-metadata.json -o output.yaml
    """
    import yaml
    import json

    try:
        # Load RO-Crate JSON-LD
        with open(input_file, 'r') as f:
            rocrate_data = json.load(f)

        # Convert to D4D
        converter = FairscapeToD4DConverter()
        d4d_data = converter.convert(rocrate_data)

        # Serialize to YAML
        yaml_output = yaml.dump(d4d_data, default_flow_style=False, sort_keys=False)

        # Write output
        if output:
            with open(output, 'w') as f:
                f.write(yaml_output)
            click.echo(f"✓ D4D YAML written to: {output}")
        else:
            click.echo(yaml_output)

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('yaml_file', type=click.Path(exists=True))
@click.option('-s', '--schema', type=click.Path(exists=True),
              help='Path to D4D schema (default: bundled schema)')
@click.option('-C', '--target-class', default='Dataset',
              help='Target class name (default: Dataset)')
@click.option('--verbose', is_flag=True, help='Show detailed validation output')
def validate(yaml_file: str, schema: Optional[str], target_class: str, verbose: bool):
    """
    Validate D4D YAML against schema.

    Validates a D4D YAML file using linkml-validate.

    Example:
        fairscape-cli validate data/d4d_concatenated/AI_READI_d4d.yaml
    """
    try:
        # Use bundled schema if not specified
        if not schema:
            schema = str(repo_root / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml")

            if not Path(schema).exists():
                click.echo(f"✗ Error: Bundled schema not found at {schema}", err=True)
                click.echo("  Please specify --schema path explicitly", err=True)
                sys.exit(1)

        # Validate
        validator = D4DValidator(schema)
        is_valid, output = validator.validate_d4d_yaml(yaml_file, target_class)

        if is_valid:
            click.echo(f"✓ Validation passed: {yaml_file}")
            if verbose:
                click.echo(output)
            sys.exit(0)
        else:
            click.echo(f"✗ Validation failed: {yaml_file}", err=True)
            click.echo()

            # Show parsed errors and suggestions
            if verbose:
                click.echo(output)
            else:
                summary = validator.get_validation_summary(is_valid, output)
                click.echo(summary)

            sys.exit(1)

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--format', type=click.Choice(['json', 'yaml', 'summary']), default='summary',
              help='Output format (default: summary)')
def info(input_file: str, format: str):
    """
    Show information about a D4D or RO-Crate file.

    Parses a file and displays metadata information.

    Example:
        fairscape-cli info data/d4d_concatenated/AI_READI_d4d.yaml
    """
    import yaml
    import json

    try:
        file_path = Path(input_file)

        # Detect file type
        if file_path.suffix in ['.yaml', '.yml']:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
            file_type = "D4D YAML"
        elif file_path.suffix == '.json':
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Check if it's RO-Crate by looking for @graph
            if '@graph' in data:
                file_type = "RO-Crate JSON-LD"
            else:
                file_type = "JSON"
        else:
            click.echo(f"✗ Unsupported file type: {file_path.suffix}", err=True)
            sys.exit(1)

        # Display information
        if format == 'json':
            click.echo(json.dumps(data, indent=2))
        elif format == 'yaml':
            click.echo(yaml.dump(data, default_flow_style=False))
        else:  # summary
            click.echo(f"File: {file_path}")
            click.echo(f"Type: {file_type}")
            click.echo(f"Size: {file_path.stat().st_size:,} bytes")
            click.echo()

            # Show key fields
            if file_type == "D4D YAML":
                click.echo("D4D Metadata:")
                for key in ['id', 'title', 'description', 'version', 'license']:
                    if key in data:
                        value = str(data[key])
                        if len(value) > 80:
                            value = value[:77] + "..."
                        click.echo(f"  {key}: {value}")

                # Show file collections if present
                if 'file_collections' in data:
                    click.echo(f"  file_collections: {len(data['file_collections'])} collection(s)")

            elif file_type == "RO-Crate JSON-LD":
                graph = data.get('@graph', [])
                click.echo(f"RO-Crate Metadata:")
                click.echo(f"  @graph entities: {len(graph)}")

                # Find root dataset
                root = next((e for e in graph if e.get('@id') == './'), None)
                if root:
                    for key in ['name', 'description', 'version', 'license']:
                        if key in root:
                            value = str(root[key])
                            if len(value) > 80:
                                value = value[:77] + "..."
                            click.echo(f"  {key}: {value}")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--verbose', is_flag=True, help='Show detailed property information')
def parse(input_file: str, verbose: bool):
    """
    Parse and inspect RO-Crate JSON-LD file.

    Displays metadata, entities, and properties from an RO-Crate file.

    Example:
        fairscape-cli parse ro-crate-metadata.json --verbose
    """
    try:
        parser = ROCrateParser(input_file, verbose=False)

        click.echo(f"RO-Crate File: {input_file}")
        click.echo(f"File Size: {Path(input_file).stat().st_size:,} bytes")
        click.echo()

        # Show root dataset
        root = parser.get_root_dataset()
        if root:
            click.echo("Root Dataset:")
            click.echo(f"  @id: {root.get('@id')}")
            click.echo(f"  @type: {root.get('@type')}")

            for key in ['name', 'description', 'version', 'license']:
                if key in root:
                    value = str(root[key])
                    if len(value) > 100 and not verbose:
                        value = value[:97] + "..."
                    click.echo(f"  {key}: {value}")
            click.echo()

        # Show entity counts by type
        graph = parser.graph
        type_counts = {}
        for entity in graph:
            entity_type = entity.get('@type')
            if isinstance(entity_type, str):
                types = [entity_type]
            else:
                types = entity_type if isinstance(entity_type, list) else []

            for t in types:
                type_counts[t] = type_counts.get(t, 0) + 1

        click.echo(f"Total Entities: {len(graph)}")
        click.echo("Entity Types:")
        for entity_type in sorted(type_counts.keys()):
            click.echo(f"  {entity_type}: {type_counts[entity_type]}")
        click.echo()

        # Show all properties if verbose
        if verbose:
            all_props = parser.extract_all_properties()
            click.echo(f"All Properties ({len(all_props)}):")
            for prop, value in sorted(all_props.items())[:50]:  # Limit to 50
                value_str = str(value)
                if len(value_str) > 80:
                    value_str = value_str[:77] + "..."
                click.echo(f"  {prop}: {value_str}")
            if len(all_props) > 50:
                click.echo(f"  ... and {len(all_props) - 50} more properties")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_files', nargs=-1, type=click.Path(exists=True), required=True)
@click.option('-o', '--output', type=click.Path(), required=True,
              help='Output D4D YAML file')
@click.option('-m', '--mapping', type=click.Path(exists=True), required=True,
              help='TSV mapping file')
@click.option('--primary', type=int, default=0,
              help='Index of primary source (default: 0)')
@click.option('--report', is_flag=True,
              help='Generate merge report')
@click.option('--verbose', is_flag=True, help='Show merge progress')
def merge(input_files, output, mapping, primary, report, verbose):
    """
    Merge multiple RO-Crate files into single D4D YAML.

    Intelligently merges multiple RO-Crate sources using field prioritization
    and conflict resolution strategies.

    Example:
        fairscape-cli merge parent.json child1.json child2.json \\
            -o merged.yaml -m mapping.tsv --report
    """
    import yaml

    try:
        # Load mapping
        mapping_loader = MappingLoader(mapping, verbose=False)

        # Parse all RO-Crates
        parsers = []
        for input_file in input_files:
            parser = ROCrateParser(input_file, verbose=False)
            parsers.append(parser)

        if verbose:
            click.echo(f"Loaded {len(parsers)} RO-Crate files")

        # Merge
        merger = ROCrateMerger(mapping_loader, verbose=verbose)
        dataset = merger.merge_rocrates(parsers, primary_index=primary)

        # Write output
        output_path = Path(output)
        with open(output_path, 'w') as f:
            yaml.dump(dataset, f, default_flow_style=False, sort_keys=False)

        click.echo(f"✓ Merged D4D YAML written to: {output}")

        # Show statistics
        stats = merger.get_merge_stats()
        click.echo()
        click.echo("Merge Statistics:")
        click.echo(f"  Total sources: {stats['total_sources']}")
        click.echo(f"  Unique fields: {stats['total_unique_fields']}")
        click.echo(f"  From primary: {stats['fields_from_primary']}")
        click.echo(f"  From secondary: {stats['fields_from_secondary']}")
        click.echo(f"  Combined: {stats['fields_combined']}")
        click.echo(f"  Merged arrays: {stats['fields_merged_as_arrays']}")

        # Generate merge report if requested
        if report:
            merger.save_merge_report(output_path, parsers)

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_files', nargs=-1, type=click.Path(exists=True), required=True)
@click.option('-m', '--mapping', type=click.Path(exists=True), required=True,
              help='TSV mapping file')
def rank(input_files, mapping):
    """
    Rank RO-Crate files by informativeness for D4D.

    Scores and ranks multiple RO-Crate files by their potential to contribute
    useful information to a D4D datasheet.

    Example:
        fairscape-cli rank file1.json file2.json file3.json -m mapping.tsv
    """
    try:
        # Load mapping
        mapping_loader = MappingLoader(mapping, verbose=False)

        # Parse all RO-Crates
        parsers = []
        for input_file in input_files:
            parser = ROCrateParser(input_file, verbose=False)
            parsers.append(parser)

        # Rank
        scorer = InformativenessScorer(verbose=False)
        ranked = scorer.rank_rocrates(parsers, mapping_loader)

        # Display ranking
        scorer.print_ranking_report(ranked)

        # Summary recommendation
        click.echo()
        click.echo("Recommendation:")
        click.echo("Process RO-Crates in this order for best D4D coverage:")
        for parser, scores, rank in ranked:
            source_name = Path(parser.rocrate_path).name
            click.echo(f"  {rank}. {source_name} (score: {scores['total_score']:.3f})")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('-o', '--output', type=click.Path(), required=True,
              help='Output D4D YAML file')
@click.option('-m', '--mapping', type=click.Path(exists=True), required=True,
              help='TSV mapping file')
@click.option('--report', is_flag=True,
              help='Generate transformation report')
@click.option('--validate', is_flag=True,
              help='Validate output after transformation')
def transform(input_file, output, mapping, report, validate):
    """
    Transform RO-Crate to D4D YAML using mapping file.

    Uses TSV mapping file to transform RO-Crate JSON-LD to D4D YAML with
    proper field transformations and type conversions.

    Example:
        fairscape-cli transform input.json -o output.yaml -m mapping.tsv --validate
    """
    import yaml

    try:
        # Load mapping
        mapping_loader = MappingLoader(mapping, verbose=False)

        # Parse RO-Crate
        parser = ROCrateParser(input_file, verbose=False)

        # Build D4D dataset
        builder = D4DBuilder(mapping_loader, verbose=False)
        dataset = builder.build_dataset(parser)

        # Write output
        output_path = Path(output)
        with open(output_path, 'w') as f:
            yaml.dump(dataset, f, default_flow_style=False, sort_keys=False)

        click.echo(f"✓ D4D YAML written to: {output}")

        # Show statistics
        covered_fields = mapping_loader.get_covered_fields()
        click.echo(f"  Fields populated: {len(dataset)}/{len(covered_fields)}")
        click.echo(f"  Coverage: {len(dataset)/len(covered_fields)*100:.1f}%")

        # Generate transformation report if requested
        if report:
            report_path = output_path.parent / f"{output_path.stem}_report.txt"

            with open(report_path, 'w') as f:
                f.write("="*80 + "\n")
                f.write("RO-Crate to D4D Transformation Report\n")
                f.write("="*80 + "\n\n")

                f.write("SUMMARY\n")
                f.write("-"*80 + "\n")
                f.write(f"Input: {input_file}\n")
                f.write(f"Output: {output}\n")
                f.write(f"Mapping: {mapping}\n")
                f.write(f"Fields populated: {len(dataset)}/{len(covered_fields)}\n")
                f.write(f"Coverage: {len(dataset)/len(covered_fields)*100:.1f}%\n\n")

                # Show unmapped properties
                mapped_props = mapping_loader.get_all_mapped_rocrate_properties()
                unmapped = parser.get_unmapped_properties(mapped_props)

                f.write("UNMAPPED RO-CRATE PROPERTIES\n")
                f.write("-"*80 + "\n")
                f.write(f"Found {len(unmapped)} properties with no D4D mapping:\n\n")

                for prop_path, sample_value in sorted(unmapped.items()):
                    f.write(f"  • {prop_path}\n")
                    f.write(f"    Sample: {sample_value}\n\n")

            click.echo(f"✓ Transformation report saved: {report_path}")

        # Validate if requested
        if validate:
            schema = str(repo_root / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml")
            validator = D4DValidator(schema)
            is_valid, validation_output = validator.validate_d4d_yaml(str(output_path))

            if is_valid:
                click.echo(f"✓ Validation passed")
            else:
                click.echo(f"✗ Validation failed", err=True)
                click.echo(validation_output)
                sys.exit(1)

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


def main():
    """Entry point for CLI."""
    cli()


if __name__ == '__main__':
    main()
