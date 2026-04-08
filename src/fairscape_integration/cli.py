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


def main():
    """Entry point for CLI."""
    cli()


if __name__ == '__main__':
    main()
