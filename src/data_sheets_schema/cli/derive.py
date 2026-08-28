"""`d4d derive` — records computed from other records, never generated."""
from __future__ import annotations

from pathlib import Path

import click


@click.group()
def derive():
    """Derive records deterministically from other records (#694)."""


@derive.command("core")
@click.option("--full", "full_path", required=True, type=click.Path(exists=True, dir_okay=False),
              help="the audited full record to project from")
@click.option("--out", "core_path", required=True, type=click.Path(dir_okay=False),
              help="where to write the derived core record")
@click.option("--validate/--no-validate", default=True, show_default=True,
              help="run linkml-validate on the result against CoreDataset")
@click.option("--phase4-complete", is_flag=True, default=False,
              help="write the `# Phase 4 reconciliation: completed` header line — "
                   "only when re-deriving after Phase 4 has actually run")
def derive_core_cmd(full_path, core_path, validate, phase4_complete):
    """Write the core record implied by a full record.

    Every schema-identical shared slot is copied from the full record,
    `resources` is projected by id, `distributions` is built from
    `file_collections` and their `File` entries over the slots the classes
    share, and `dialect` is derived only where every file agrees on one
    (else absent). The result is a pure function of
    the full record and the two schemas: pair consistency holds by
    construction and no fact is introduced. Prints the derivation facts the
    provenance record should carry.
    """
    import json
    import subprocess

    from data_sheets_schema.derive_core import write_core

    full, core = Path(full_path), Path(core_path)
    facts = write_core(full, core, phase4_complete=phase4_complete)
    click.echo(f"✓ {core}")
    click.echo(json.dumps(facts))
    if validate:
        from data_sheets_schema.derive_core import CORE_SCHEMA_REL
        r = subprocess.run(["linkml-validate", "-s", CORE_SCHEMA_REL,
                            "-C", "CoreDataset", str(core)],
                           capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        if r.returncode != 0 or "No issues found" not in out:
            raise click.ClickException(
                f"derived core does not validate against CoreDataset — the full "
                f"record it was projected from carries a shape the core schema "
                f"rejects; fix the full record, not the core:\n{out[-800:]}")
        click.echo("  linkml-validate: No issues found")
