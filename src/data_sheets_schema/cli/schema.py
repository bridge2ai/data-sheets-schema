"""Schema command group for D4D CLI.

Commands for schema operations and validation.
"""

import click
import sys
from pathlib import Path
from data_sheets_schema.constants import SCHEMA_FULL_PATH

@click.group()
def schema():
    """Schema operations and validation."""
    pass

@schema.command()
@click.option('--level', type=click.IntRange(1, 4), default=1,
              help='Detail level (1=summary, 2=breakdown, 3=detailed, 4=quality)')
@click.option('--format', type=click.Choice(['json', 'markdown', 'csv']),
              default='markdown',
              help='Output format')
@click.option('--output', type=click.Path(),
              help='Output file (default: stdout)')
@click.option('--schema-file', type=click.Path(exists=True),
              help=f'Schema file path (default: {SCHEMA_FULL_PATH})')
def stats(level, format, output, schema_file):
    """Generate schema statistics and metrics."""
    click.echo(f"📊 Generating schema statistics (level {level}, {format} format)...")

    # Import and call the schema_stats script
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".claude" / "agents" / "scripts"))

    try:
        from schema_stats import main as stats_main

        # Set up args for the schema_stats script
        old_argv = sys.argv
        sys.argv = ['schema_stats.py',
                    '--level', str(level),
                    '--format', format]
        if output:
            sys.argv.extend(['--output', output])
        if schema_file:
            sys.argv.extend(['--schema', schema_file])

        stats_main()

        if output:
            click.echo(f"✓ Statistics saved to {output}")
        else:
            click.echo("✓ Statistics generated")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        sys.argv = old_argv

@schema.command()
@click.argument('d4d_file', type=click.Path(exists=True))
@click.option('--schema-file', type=click.Path(exists=True),
              help=f'Schema file path (default: {SCHEMA_FULL_PATH})')
def validate(d4d_file, schema_file):
    """Validate D4D YAML file against schema."""
    click.echo(f"✓ Validating {d4d_file}...")

    # Import and call the validator script
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".claude" / "agents" / "scripts"))

    try:
        from validator import D4DValidator

        if not schema_file:
            schema_file = str(SCHEMA_FULL_PATH)

        validator = D4DValidator(schema_file)
        is_valid, errors = validator.validate_file(d4d_file)

        if is_valid:
            click.echo(f"✓ {d4d_file} is valid!")
        else:
            click.echo(f"❌ {d4d_file} has validation errors:", err=True)
            for error in errors:
                click.echo(f"  - {error}", err=True)
            sys.exit(1)

    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        click.echo("Note: Validator script may not be available", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
