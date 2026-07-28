"""RO-Crate command group for D4D CLI.

Commands for working with RO-Crate metadata.
"""

import click
import sys
from pathlib import Path

from data_sheets_schema.cli._repo_utils import setup_repo_imports, require_repo_context
from data_sheets_schema.constants import PROJECTS
@click.group()
def rocrate():
    """RO-Crate integration commands."""
    pass

@rocrate.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', type=click.Path(), help='Output file for parsed data')
def parse(input_file, output):
    """Parse RO-Crate JSON-LD file."""
    require_repo_context("d4d rocrate parse")

    click.echo(f"📦 Parsing RO-Crate: {input_file}")

    # Import and call the parser script
    setup_repo_imports()

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
@click.argument('input_file', required=False, type=click.Path(exists=True))
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
    require_repo_context("d4d rocrate transform")

    if merge:
        if not inputs:
            raise click.UsageError(
                "--merge requires at least one --inputs PATH.",
                ctx=click.get_current_context(),
            )
        click.echo(f"🔄 Transforming {len(inputs)} RO-Crates to D4D (merge mode)...")
    else:
        if not input_file:
            raise click.UsageError(
                "Missing argument 'INPUT_FILE'.",
                ctx=click.get_current_context(),
            )
        click.echo(f"🔄 Transforming RO-Crate to D4D: {input_file}")

    # Import and call the transform script
    setup_repo_imports()

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
    require_repo_context("d4d rocrate merge")

    click.echo(f"🔀 Merging {len(input_files)} RO-Crate files...")

    # Import and call the merger script
    setup_repo_imports()

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


@rocrate.command()
@click.option('--project', type=click.Choice(PROJECTS), multiple=True,
              help='Project(s) to normalize; repeatable. Default: all available.')
@click.option('--packages-dir', type=click.Path(), default='data/ro-crate_packages',
              show_default=True, help='Root of the per-project crate packages.')
def normalize(project, packages_dir):
    """Normalize upstream RO-Crate packages into D4D-usable artifacts.

    Writes {PROJECT}/processed/ with a schema-valid D4D YAML (deterministic
    fork), a size-reduced crate JSON-LD (de novo fork), and a changes report.
    Raw inputs are never modified.
    """
    from linkml_runtime import SchemaView

    from data_sheets_schema.rocrate_normalize import (
        FULL_SCHEMA, normalize_project,
    )

    root = Path(packages_dir)
    targets = list(project) or [
        p for p in PROJECTS
        if (root / p / 'raw').is_dir() or (root / p / 'crate').is_dir()
    ]
    if not targets:
        click.echo(f"No crate packages found under {root}", err=True)
        sys.exit(1)

    sv = SchemaView(str(FULL_SCHEMA))
    failures = 0
    for name in targets:
        click.echo(f"\n📦 {name}")
        try:
            res = normalize_project(name, root, sv=sv)
        except FileNotFoundError as e:
            click.echo(f"  ⚠️  {e}", err=True)
            failures += 1
            continue
        for label, path in res.outputs.items():
            click.echo(f"  → {label}: {path}")
        for fname, status in res.validation.items():
            head = status.splitlines()[0]
            icon = "✓" if head == "PASS" else "❌"
            click.echo(f"  {icon} {fname}: {head}")
            if head != "PASS":
                failures += 1
                for line in status.splitlines()[1:6]:
                    click.echo(f"      {line}")
        click.echo(f"  {len(res.changes)} change(s) recorded")

    if failures:
        click.echo(f"\n❌ {failures} validation failure(s)", err=True)
        sys.exit(1)
    click.echo("\n✅ Normalization complete")


@rocrate.command()
@click.option('--project', type=click.Choice(PROJECTS), multiple=True,
              help='Project(s) to bundle; repeatable. Default: all normalized.')
@click.option('--packages-dir', type=click.Path(), default='data/ro-crate_packages',
              show_default=True)
def bundle(project, packages_dir):
    """Build the crate-augmented source bundle for the de novo fork.

    Writes data/preprocessed/concatenated/{PROJECT}_preprocessed_with_crate.txt
    from the document bundle plus crate evidence. Artifacts that are already in
    D4D or datasheet form are withheld so this arm extracts rather than copies.
    """
    from data_sheets_schema.rocrate_normalize import build_crate_bundle

    root = Path(packages_dir)
    targets = list(project) or [
        p for p in PROJECTS if (root / p / 'processed').is_dir()
    ]
    if not targets:
        click.echo(f"No normalized crates under {root}; run `d4d rocrate normalize`",
                   err=True)
        sys.exit(1)

    failures = 0
    for name in targets:
        click.echo(f"\n📦 {name}")
        try:
            out, included, withheld = build_crate_bundle(name, root)
        except Exception as e:
            click.echo(f"  ❌ {e}", err=True)
            failures += 1
            continue
        click.echo(f"  → {out} ({out.stat().st_size:,} bytes)")
        for inc in included:
            click.echo(f"  + {inc}")
        for w in withheld:
            click.echo(f"  - {w.split(' — ')[0]} (withheld)")

    if failures:
        sys.exit(1)
    click.echo("\n✅ Crate-augmented bundles written")


@rocrate.command('emit-arm')
@click.option('--version', required=True,
              help='Run label, e.g. 2026-07-24_deterministic-v1')
@click.option('--project', type=click.Choice(PROJECTS), multiple=True,
              help='Project(s); default all normalized.')
@click.option('--packages-dir', type=click.Path(), default='data/ro-crate_packages',
              show_default=True)
def emit_arm(version, project, packages_dir):
    """Publish the deterministic arm to data/d4d_concatenated/rocrate_mapped/.

    Makes the no-model mapping output comparable with the model-generated arms
    under the existing per-method evaluation tooling.
    """
    from data_sheets_schema.rocrate_normalize import emit_deterministic_arm

    root = Path(packages_dir)
    targets = list(project) or [
        p for p in PROJECTS
        if (root / p / 'processed' / f'{p}_crate_d4d.yaml').exists()
    ]
    if not targets:
        click.echo("No normalized crate records found; run `d4d rocrate normalize`",
                   err=True)
        sys.exit(1)

    failures = 0
    for name in targets:
        try:
            out = emit_deterministic_arm(name, version, root)
            click.echo(f"  ✓ {name} → {out}")
        except (FileNotFoundError, FileExistsError) as e:
            click.echo(f"  ❌ {name}: {e}", err=True)
            failures += 1

    if failures:
        sys.exit(1)
    click.echo(f"\n✅ Deterministic arm published under version {version}")


@rocrate.command('map')
@click.option('--project', type=click.Choice(PROJECTS), multiple=True,
              help='Project(s); default all with a crate.')
@click.option('--packages-dir', type=click.Path(), default='data/ro-crate_packages',
              show_default=True)
def map_cmd(project, packages_dir):
    """Map a crate to D4D using this repo's own static mapping table.

    Reads ro-crate-metadata.json (which every crate has) rather than the
    upstream ro-crate-linkml.yaml, so it works uniformly across crates and
    reports the declared mapping quality of every field it fills.
    """
    from linkml_runtime import SchemaView

    from data_sheets_schema.rocrate_map import (
        FULL_SCHEMA, load_mapping, map_project,
    )

    root = Path(packages_dir)
    targets = list(project) or [
        p for p in PROJECTS
        if (root / p / 'raw' / 'ro-crate-metadata.json').exists()
        or (root / p / 'crate' / 'ro-crate-metadata.json').exists()
    ]
    if not targets:
        click.echo(f"No crates with ro-crate-metadata.json under {root}", err=True)
        sys.exit(1)

    sv = SchemaView(str(FULL_SCHEMA))
    rows = load_mapping()
    click.echo(f"Mapping table: {len(rows)} rows")
    failures = 0
    for name in targets:
        click.echo(f"\n📦 {name}")
        try:
            res = map_project(name, root, sv=sv, rows=rows)
        except FileNotFoundError as e:
            click.echo(f"  ❌ {e}", err=True)
            failures += 1
            continue
        c = res.counts()
        click.echo(f"  filled {c.get('filled',0)} | empty {c.get('empty',0)} | "
                   f"unresolvable {c.get('unresolvable',0)} | "
                   f"unplaceable {c.get('unplaceable',0)}")
        for label, path in res.outputs.items():
            click.echo(f"  → {label}: {path}")
        head = res.validation.splitlines()[0]
        click.echo(f"  {'✓' if head == 'PASS' else '❌'} validation: {head}")
        if head != 'PASS':
            failures += 1
            for line in res.validation.splitlines()[1:6]:
                click.echo(f"      {line}")

    if failures:
        sys.exit(1)
    click.echo("\n✅ Static mapping complete")


@rocrate.command('emit-map-arm')
@click.option('--version', required=True, help='Run label for this arm.')
@click.option('--project', type=click.Choice(PROJECTS), multiple=True)
@click.option('--packages-dir', type=click.Path(), default='data/ro-crate_packages',
              show_default=True)
def emit_map_arm(version, project, packages_dir):
    """Publish the our-mapping deterministic arm to d4d_concatenated/."""
    from data_sheets_schema.rocrate_normalize import emit_deterministic_arm

    root = Path(packages_dir)
    targets = list(project) or [
        p for p in PROJECTS
        if (root / p / 'processed' / f'{p}_crate_mapped_d4d.yaml').exists()
    ]
    if not targets:
        click.echo("No mapped records found; run `d4d rocrate map`", err=True)
        sys.exit(1)

    failures = 0
    for name in targets:
        try:
            out = emit_deterministic_arm(name, version, root,
                                         method='rocrate_static_map',
                                         variant='crate_mapped_d4d')
            click.echo(f"  ✓ {name} → {out}")
        except (FileNotFoundError, FileExistsError) as e:
            click.echo(f"  ❌ {name}: {e}", err=True)
            failures += 1
    if failures:
        sys.exit(1)
    click.echo(f"\n✅ our-mapping arm published under {version}")
