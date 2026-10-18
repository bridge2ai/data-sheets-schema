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

    old_argv = sys.argv                 # bound before the try: the finally reads it (#1501)
    try:
        from schema_stats import main as stats_main

        # Set up args for the schema_stats script
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

#: How long `d4d schema validate` waits for linkml-validate: a bound on a
#: validator that hangs, not a budget for a slow one. The legacy script's 30 s
#: was exceeded on a heavily loaded machine (#4065); `d4d runs select` gives
#: the same merged-schema validation 300 s.
VALIDATE_TIMEOUT_SECONDS = 300


def _validate_d4d_yaml(schema_file, d4d_file):
    """`(is_valid, output)` from this interpreter's linkml-validate (#4188).

    The command used to import `.claude/agents/scripts/validator.py`, which
    runs `poetry run linkml-validate`: in a checkout with no poetry
    environment of its own that created an empty one and ran whichever
    `linkml-validate` came first on PATH, so the verdict depended on the
    caller's PATH. `resources.linkml_validate()` is the one beside this
    interpreter, never a PATH search (#1486, #1530). The verdict, the output
    and the texts for a missing schema, a validator that could not start and
    a timeout are that script's, except that the timeout names this bound
    rather than its 30 s.
    """
    import subprocess

    from data_sheets_schema.resources import linkml_validate

    schema_path = Path(schema_file)
    if not schema_path.exists():
        raise FileNotFoundError(f"D4D schema not found: {schema_file}")
    try:
        result = subprocess.run(
            [*linkml_validate(), "-s", str(schema_path), "-C", "Dataset", str(Path(d4d_file))],
            capture_output=True, text=True, timeout=VALIDATE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return False, f"Validation timeout ({VALIDATE_TIMEOUT_SECONDS}s)"
    except Exception as e:                              # noqa: BLE001
        return False, f"Validation error: {e}"
    return result.returncode == 0, result.stdout + result.stderr


@schema.command()
@click.argument('d4d_file', type=click.Path(exists=True))
@click.option('--schema-file', type=click.Path(exists=True),
              help=f'Schema file path (default: {SCHEMA_FULL_PATH})')
def validate(d4d_file, schema_file):
    """Validate D4D YAML file against schema."""
    require_repo_context("d4d schema validate")

    click.echo(f"✓ Validating {d4d_file}...")

    try:
        if not schema_file:
            schema_file = str(SCHEMA_FULL_PATH)

        is_valid, output = _validate_d4d_yaml(schema_file, d4d_file)

        if is_valid:
            click.echo(f"✓ {d4d_file} is valid!")
        else:
            click.echo(f"❌ {d4d_file} has validation errors:", err=True)
            click.echo(output.rstrip(), err=True)
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

    from data_sheets_schema.schema_sync import (
        IN_SYNC, STALE, UNCHECKED_ADVICE, blocking, check, rebuild_advice)

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
        # A check that could not run is not a stale schema; regenerating would not
        # help it (#2738).
        stale = [r for r in bad if r["status"] == STALE]
        if stale:
            click.echo(f"\n{len(stale)} of {len(rows)} merged schema(s) not current. "
                       f"Rebuild with {rebuild_advice(stale)}, review the diff, and commit "
                       "it before generating: a run started now would record a digest for "
                       "a schema this repository no longer holds.")
        if len(bad) - len(stale):
            click.echo(f"\n{len(bad) - len(stale)} of {len(rows)} merged schema(s) could not be "
                       f"checked; see the reason above. A run started now is refused: "
                       f"{UNCHECKED_ADVICE}.")
    if strict and bad:
        sys.exit(1)
