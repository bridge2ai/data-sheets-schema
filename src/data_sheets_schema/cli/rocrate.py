"""RO-Crate command group for D4D CLI.

Commands for working with RO-Crate metadata.
"""

import click

from data_sheets_schema.registry import project_choice, projects_for
import sys
from collections import Counter
from pathlib import Path

from data_sheets_schema.cli._repo_utils import (
    get_repo_root, setup_repo_imports, require_repo_context,
)


def _outcome_line(refused: int, invalid: int, failed: int = 0) -> str:
    """One summary line counting refused crates apart from records that failed
    validation: a crate that could not be read was never validated (#3359)."""
    line = (f"{refused} crate(s) refused (missing or unreadable), "
            f"{invalid} validation failure(s)")
    return line + (f", {failed} project error(s)" if failed else "")


def _once_each(project: tuple[str, ...]) -> list[str]:
    """The --project names in the order first given, each once (#4165).

    `project_choice` returns the names as typed, so a repeated one ran its
    project again: an emit command refused the record its first pass had just
    published, and a run that published every project exited 1. Each repeated
    name gets one stderr line. With no --project the names come from the
    manifest's keys, which cannot repeat."""
    for name, times in Counter(project).items():
        if times > 1:
            click.echo(f"⚠️  --project {name} was given {times} times; it runs once",
                       err=True)
    return list(dict.fromkeys(project))


def _reason(exc: Exception, refusals: tuple[type[Exception], ...]) -> str:
    """The reason a per-project error line gives (#4148). An expected refusal
    is its own message. Any other error is named by its type, since a KeyError's
    message is only the key, and an empty message never leaves the line bare."""
    text = str(exc)
    if text and isinstance(exc, refusals):
        return text
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


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
        from data_sheets_schema.rocrate_map import TRANSCODE_HINT, read_crate_json
        from rocrate_parser import ROCrateParser

        # The parser setup_repo_imports finds is the copy under
        # .claude/agents/scripts, which opens the crate as UTF-8 itself, so a
        # crate that is not UTF-8 ended this command with a bare
        # UnicodeDecodeError. The crate is read first as `fairscape-cli
        # parse` reads one (`read_crate_json`): such a crate is refused with
        # a CrateEncodingError that names the first byte that does not
        # decode and says to transcode it, reported below like any other
        # error (#4186).
        read_crate_json(Path(input_file), hint=TRANSCODE_HINT)
        parser = ROCrateParser(input_file)
        # Inspection may show a rootless graph, but must not imply a child
        # dataset was selected as its root.
        try:
            parser.require_root_dataset()
        except ValueError as exc:
            click.echo(f"⚠️  {exc}", err=True)
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
@click.option('--mapping', 'mapping_file',
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help='Explicit legacy mapping TSV; omitted uses d4d_rocrate_mapping_v2_semantic.tsv')
def transform(input_file, output, merge, inputs, primary, mapping_file=None):
    """Transform RO-Crate to D4D YAML format."""
    require_repo_context("d4d rocrate transform")

    if merge:
        if not inputs:
            raise click.UsageError(
                "--merge requires at least one --inputs PATH.",
                ctx=click.get_current_context(),
            )
        primary_index = 0
        if primary:
            matches = [i for i, path in enumerate(inputs)
                       if Path(path).resolve() == Path(primary).resolve()]
            if not matches:
                raise click.UsageError(
                    "--primary must name one of the --inputs files.",
                    ctx=click.get_current_context(),
                )
            primary_index = matches[0]
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

    old_argv = sys.argv
    try:
        from rocrate_to_d4d import main as transform_main

        # Set up args for the transform script
        mapping = (mapping_file if mapping_file is not None else
                   get_repo_root() / "data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv")
        if merge:
            sys.argv = ['rocrate_to_d4d.py',
                        '--merge',
                        '--inputs'] + list(inputs) + [
                        '-o', output, '--mapping', str(mapping)]
            if primary:
                sys.argv.extend(['--primary', str(primary_index)])
        else:
            sys.argv = ['rocrate_to_d4d.py',
                        '-i', input_file,
                        '-o', output, '--mapping', str(mapping)]

        status = transform_main()
        if status:
            raise SystemExit(status)
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
              help='Retained option; this retired command never writes an output.')
@click.option('--primary', type=click.Path(exists=True),
              help='Retained option; no raw merge or conflict precedence is applied.')
def merge(input_files, output, primary):
    """Retired: raw RO-Crate merging is unsupported (#4593).

    The command and options remain recognizable so callers receive an explicit
    refusal. Dataset transformation and graph concatenation are different
    operations and cannot supply this command's missing identity/root contract.
    """
    raise click.ClickException(
        "Raw RO-Crate merging is retired (#4593): no supported identity, root "
        "and conflict policy is defined. This command cannot produce merged "
        "RO-Crate JSON. Keep source crates separate; see "
        "https://github.com/bridge2ai/data-sheets-schema/issues/4593."
    )


@rocrate.command()
@click.option('--project', callback=project_choice, multiple=True,
              help='Project(s) to normalize; repeatable. Default: all available.')
@click.option('--packages-dir', type=click.Path(), default='data/ro-crate_packages',
              show_default=True, help='Root of the per-project crate packages.')
def normalize(project, packages_dir):
    """Normalize upstream RO-Crate packages into D4D-usable artifacts.

    Writes {PROJECT}/processed/ with a schema-valid D4D YAML (deterministic
    fork), a size-reduced crate JSON-LD (de novo fork), and a changes report.
    Raw inputs are never modified.
    """
    require_repo_context("d4d rocrate normalize")     # the mapping table and packages are the corpus (#1551); below the docstring (#1590)
    from linkml_runtime import SchemaView

    from data_sheets_schema.rocrate_map import CrateEncodingError
    from data_sheets_schema.rocrate_normalize import (
        FULL_SCHEMA, normalize_project,
    )

    root = Path(packages_dir)
    targets = _once_each(project) or [
        p for p in projects_for(click.get_current_context())
        if (root / p / 'raw').is_dir() or (root / p / 'crate').is_dir()
    ]
    if not targets:
        click.echo(f"No crate packages found under {root}", err=True)
        sys.exit(1)

    from data_sheets_schema.resources import resource_path
    sv = SchemaView(str(resource_path(FULL_SCHEMA)))       # from any directory (#1485)
    refused = invalid = failed = 0                         # counted apart (#3359, #4177)
    for name in targets:
        click.echo(f"\n📦 {name}")
        try:
            res = normalize_project(name, root, sv=sv)
        except (FileNotFoundError, CrateEncodingError) as e:   # report, go on (#2969)
            click.echo(f"  ⚠️  {name}: {_reason(e, (FileNotFoundError, CrateEncodingError))}", err=True)
            refused += 1
            continue
        except Exception as e:
            click.echo(f"  ❌ {name}: {_reason(e, ())}", err=True)
            failed += 1
            continue
        for label, path in res.outputs.items():
            click.echo(f"  → {label}: {path}")
        for fname, status in res.validation.items():
            head = status.splitlines()[0]
            icon = "✓" if head == "PASS" else "❌"
            click.echo(f"  {icon} {fname}: {head}")
            if head != "PASS":
                invalid += 1
                for line in status.splitlines()[1:6]:
                    click.echo(f"      {line}")
        click.echo(f"  {len(res.changes)} change(s) recorded")

    if refused or invalid or failed:
        click.echo(f"\n❌ {_outcome_line(refused, invalid, failed)}", err=True)
        sys.exit(1)
    click.echo("\n✅ Normalization complete")


@rocrate.command()
@click.option('--project', callback=project_choice, multiple=True,
              help='Project(s) to bundle; repeatable. Default: all normalized.')
@click.option('--packages-dir', type=click.Path(), default='data/ro-crate_packages',
              show_default=True)
def bundle(project, packages_dir):
    """Build the crate-augmented source bundle for the de novo fork.

    Writes data/preprocessed/concatenated/{PROJECT}_preprocessed_with_crate.txt
    from the document bundle plus crate evidence. Artifacts that are already in
    D4D or datasheet form are withheld so this arm extracts rather than copies.
    """
    from data_sheets_schema.rocrate_normalize import DeNovoPolicyError, build_crate_bundle

    root = Path(packages_dir)
    targets = _once_each(project) or [
        p for p in projects_for(click.get_current_context()) if (root / p / 'processed').is_dir()
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
            click.echo(f"  ❌ {name}: {_reason(e, (FileNotFoundError, DeNovoPolicyError))}", err=True)
            failures += 1
            continue
        click.echo(f"  → {out} ({out.stat().st_size:,} bytes)")
        for inc in included:
            click.echo(f"  + {inc}")
        for w in withheld:
            click.echo(f"  - {w.split(' — ')[0]} (withheld)")

    if failures:                                           # the total, not a bare exit (#3638)
        click.echo(f"\n❌ {failures} of {len(targets)} bundle(s) not written", err=True)
        sys.exit(1)
    click.echo("\n✅ Crate-augmented bundles written")


@rocrate.command('emit-arm')
@click.option('--version', required=True,
              help='Run label, e.g. 2026-07-24_deterministic-v1')
@click.option('--project', callback=project_choice, multiple=True,
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
    targets = _once_each(project) or [
        p for p in projects_for(click.get_current_context())
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
        except Exception as e:                             # as bundle: count it, go on (#4147)
            click.echo(f"  ❌ {name}: {_reason(e, (FileNotFoundError, FileExistsError))}",
                       err=True)
            failures += 1
            continue
        click.echo(f"  ✓ {name} → {out}")

    if failures:                                           # the total, not a bare exit (#3638)
        click.echo(f"\n❌ {failures} of {len(targets)} project(s) not published", err=True)
        sys.exit(1)
    click.echo(f"\n✅ Deterministic arm published under version {version}")


@rocrate.command('map')
@click.option('--project', callback=project_choice, multiple=True,
              help='Project(s); default all with a crate.')
@click.option('--packages-dir', type=click.Path(), default='data/ro-crate_packages',
              show_default=True)
def map_cmd(project, packages_dir):
    """Map a crate to D4D using this repo's own static mapping table.

    Reads ro-crate-metadata.json (which every crate has) rather than the
    upstream ro-crate-linkml.yaml, so it works uniformly across crates and
    reports the declared mapping quality of every field it fills.
    """
    require_repo_context("d4d rocrate map")
    from linkml_runtime import SchemaView

    from data_sheets_schema.rocrate_map import (
        FULL_SCHEMA, CrateEncodingError, load_mapping, map_project,
    )

    root = Path(packages_dir)
    targets = _once_each(project) or [
        p for p in projects_for(click.get_current_context())
        if (root / p / 'raw' / 'ro-crate-metadata.json').exists()
        or (root / p / 'crate' / 'ro-crate-metadata.json').exists()
    ]
    if not targets:
        click.echo(f"No crates with ro-crate-metadata.json under {root}", err=True)
        sys.exit(1)

    from data_sheets_schema.resources import resource_path
    sv = SchemaView(str(resource_path(FULL_SCHEMA)))       # from any directory (#1485)
    rows = load_mapping()
    click.echo(f"Mapping table: {len(rows)} rows")
    refused = invalid = failed = 0                         # counted apart (#3359, #4177)
    for name in targets:
        click.echo(f"\n📦 {name}")
        try:
            res = map_project(name, root, sv=sv, rows=rows)
        except (FileNotFoundError, CrateEncodingError) as e:   # report, go on (#2969)
            click.echo(f"  ❌ {name}: {_reason(e, (FileNotFoundError, CrateEncodingError))}", err=True)
            refused += 1
            continue
        except Exception as e:
            click.echo(f"  ❌ {name}: {_reason(e, ())}", err=True)
            failed += 1
            continue
        c = res.counts()
        click.echo(f"  filled {c.get('filled',0)} | subsumed {c.get('subsumed',0)} | "
                   f"empty {c.get('empty',0)} | "
                   f"unresolvable {c.get('unresolvable',0)} | "
                   f"unplaceable {c.get('unplaceable',0)}")
        for label, path in res.outputs.items():
            click.echo(f"  → {label}: {path}")
        head = res.validation.splitlines()[0]
        click.echo(f"  {'✓' if head == 'PASS' else '❌'} validation: {head}")
        if head != 'PASS':
            invalid += 1
            for line in res.validation.splitlines()[1:6]:
                click.echo(f"      {line}")

    if refused or invalid or failed:
        click.echo(f"\n❌ {_outcome_line(refused, invalid, failed)}", err=True)
        sys.exit(1)
    click.echo("\n✅ Static mapping complete")


@rocrate.command('emit-map-arm')
@click.option('--version', required=True, help='Run label for this arm.')
@click.option('--project', callback=project_choice, multiple=True)
@click.option('--packages-dir', type=click.Path(), default='data/ro-crate_packages',
              show_default=True)
def emit_map_arm(version, project, packages_dir):
    """Publish the our-mapping deterministic arm to d4d_concatenated/."""
    from data_sheets_schema.rocrate_normalize import emit_deterministic_arm

    root = Path(packages_dir)
    targets = _once_each(project) or [
        p for p in projects_for(click.get_current_context())
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
        except Exception as e:                             # as bundle: count it, go on (#4147)
            click.echo(f"  ❌ {name}: {_reason(e, (FileNotFoundError, FileExistsError))}",
                       err=True)
            failures += 1
            continue
        click.echo(f"  ✓ {name} → {out}")
    if failures:                                           # the total, not a bare exit (#3638)
        click.echo(f"\n❌ {failures} of {len(targets)} project(s) not published", err=True)
        sys.exit(1)
    click.echo(f"\n✅ our-mapping arm published under {version}")
