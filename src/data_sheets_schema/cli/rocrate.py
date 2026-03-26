"""RO-Crate command group for D4D CLI.

Commands for working with RO-Crate metadata.
"""

import click
import sys
from pathlib import Path

@click.group()
def rocrate():
    """RO-Crate integration commands."""
    pass

@rocrate.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', type=click.Path(), help='Output file for parsed data')
def parse(input_file, output):
    """Parse RO-Crate JSON-LD file."""
    click.echo(f"📦 Parsing RO-Crate: {input_file}")

    # Import and call the parser script
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".claude" / "agents" / "scripts"))

    try:
        from rocrate_parser import ROCrateParser

        parser = ROCrateParser(input_file)
        entities = parser.get_all_entities()

        if output:
            import json
            with open(output, 'w') as f:
                json.dump(entities, f, indent=2)
            click.echo(f"✓ Parsed {len(entities)} entities to {output}")
        else:
            click.echo(f"✓ Found {len(entities)} entities")
            for entity_id, entity in list(entities.items())[:5]:
                click.echo(f"  - {entity_id}: {entity.get('@type', 'Unknown')}")
            if len(entities) > 5:
                click.echo(f"  ... and {len(entities) - 5} more")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

@rocrate.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), required=True,
              help='Output D4D YAML file')
@click.option('--merge', is_flag=True,
              help='Merge multiple RO-Crates (use --inputs instead of INPUT_FILE)')
@click.option('--inputs', multiple=True, type=click.Path(exists=True),
              help='Multiple input RO-Crate files for merging')
@click.option('--primary', type=click.Path(exists=True),
              help='Primary RO-Crate file (for merging)')
def transform(input_file, output, merge, inputs, primary):
    """Transform RO-Crate to D4D YAML format."""
    if merge:
        if not inputs:
            click.echo("❌ Error: --merge requires --inputs", err=True)
            sys.exit(1)
        click.echo(f"🔄 Transforming {len(inputs)} RO-Crates to D4D (merge mode)...")
    else:
        click.echo(f"🔄 Transforming RO-Crate to D4D: {input_file}")

    # Import and call the transform script
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".claude" / "agents" / "scripts"))

    try:
        from rocrate_to_d4d import main as transform_main

        # Set up args for the transform script
        old_argv = sys.argv
        if merge:
            sys.argv = ['rocrate_to_d4d.py',
                        '--merge',
                        '--inputs'] + list(inputs) + [
                        '-o', output]
            if primary:
                sys.argv.extend(['--primary', primary])
        else:
            sys.argv = ['rocrate_to_d4d.py',
                        '-i', input_file,
                        '-o', output]

        transform_main()
        click.echo(f"✓ D4D YAML saved to {output}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        sys.argv = old_argv

@rocrate.command()
@click.argument('input_files', nargs=-1, type=click.Path(exists=True), required=True)
@click.option('--output', '-o', type=click.Path(), required=True,
              help='Output merged RO-Crate file')
@click.option('--primary', type=click.Path(exists=True),
              help='Primary RO-Crate file (takes precedence in conflicts)')
def merge(input_files, output, primary):
    """Merge multiple RO-Crate files into one."""
    click.echo(f"🔀 Merging {len(input_files)} RO-Crate files...")

    # Import and call the merger script
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".claude" / "agents" / "scripts"))

    try:
        from rocrate_merger import ROCrateMerger

        merger = ROCrateMerger()

        # Load all input files
        for input_file in input_files:
            is_primary = (primary and Path(input_file) == Path(primary))
            merger.add_rocrate(input_file, is_primary=is_primary)
            click.echo(f"  + {input_file}{' (primary)' if is_primary else ''}")

        # Merge and save
        merged = merger.merge()

        import json
        with open(output, 'w') as f:
            json.dump(merged, f, indent=2)

        click.echo(f"✓ Merged RO-Crate saved to {output}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
