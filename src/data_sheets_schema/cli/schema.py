"""Schema command group for D4D CLI.

Commands for schema operations and validation.
"""

import click
import sys
from pathlib import Path
from data_sheets_schema.constants import SCHEMA_FULL_PATH
from data_sheets_schema.cli._repo_utils import setup_repo_imports, require_repo_context

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
    require_repo_context("d4d schema stats")

    click.echo(f"📊 Generating schema statistics (level {level}, {format} format)...")

    # Import and call the schema_stats script
    setup_repo_imports()

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
    require_repo_context("d4d schema validate")

    click.echo(f"✓ Validating {d4d_file}...")

    # Import and call the validator script
    setup_repo_imports()

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


@schema.command("check-digest")
@click.option("--strict", is_flag=True,
              help="exit 1 when a merged schema is stale or cannot be checked")
def check_digest(strict):
    """Is the merged schema a run would consume built from today's source?

    The digest sent to the model, the schema records are validated against and
    the identity slots the pair checker uses all come from the *merged*
    schemas, which are generated artifacts. Editing a module without
    regenerating leaves every record in an arm attesting to a digest that
    describes an older schema than the repository holds — and nothing in the
    record can reveal it, because the record correctly hashes the merged file
    it actually read.

    Rebuilds each merged schema from its source into a temporary directory and
    compares, rather than trusting timestamps: a merged file can be newer than
    its modules and still be wrong (the reason `audit-bundles` works the same
    way, #446).
    """
    import sys

    from data_sheets_schema.schema_sync import IN_SYNC, blocking, check

    rows = check()
    for r in rows:
        mark = {"in_sync": "✓", "stale": "❌", "unchecked": "❌"}[r["status"]]
        click.echo(f" {mark} {r['status']:9} {r['class']:12} "
                   f"digest {str(r.get('digest') or '-')[:12]}  {r['merged']}")
        if r.get("reason"):
            click.echo(f"       {r['reason']}")
        if r.get("rebuilt_at"):
            click.echo(f"       a fresh build is at {r['rebuilt_at']} — "
                       f"diff it against {r['merged']}")

    bad = blocking(rows)
    if not bad:
        click.echo(f"\n{len(rows)} merged schema(s) built from current source.")
    else:
        click.echo(f"\n{len(bad)} of {len(rows)} merged schema(s) not current. "
                   "Run `make regen-all`, review the diff, and commit it before "
                   "generating: a run started now would record a digest for a "
                   "schema this repository no longer holds.")
    if strict and bad:
        sys.exit(1)
