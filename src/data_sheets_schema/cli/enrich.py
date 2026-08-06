"""Enrichment commands — deterministic, provenance-marked additions (#378)."""

from pathlib import Path

import click


@click.group()
def enrich():
    """Deterministic post-generation enrichment. Never runs inside generation."""


@enrich.command("orgs")
@click.argument("record", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), default=None,
              help="write the enriched record here (default: dry run). A "
                   "sidecar {output}.enrichment.yaml records what was added "
                   "and from which registry snapshot. The original file is "
                   "never touched — run provenance pins its bytes.")
def orgs_cmd(record, output):
    """Fill Organization ids with B2AI_ORG CURIEs from the vendored registry.

    Strict lookup only (name, full name, or embedded ROR); organizations the
    registry does not know keep their name and no id. Enrichment is not
    extraction: the additions are recorded as such, never silently.
    """
    import yaml as _yaml

    from data_sheets_schema.org_registry import (
        OrgResolver, enrich_record, enrichment_block)

    resolver = OrgResolver()
    text = Path(record).read_text(encoding="utf-8")
    data = _yaml.safe_load(text)
    if not isinstance(data, dict):
        raise click.ClickException(f"{record} is not a mapping")
    _, log = enrich_record(data, resolver)
    if not log:
        click.echo("no organizations resolved; nothing to enrich")
        return
    for e in log:
        click.echo(f"   {e['id']:<14} {e['name']}  ({e['path']})")
    if not output:
        click.echo(f"dry run: {len(log)} organization(s) would be enriched; "
                   "pass -o to write")
        return
    out = Path(output)
    out.write_text(_yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                   encoding="utf-8")
    side = out.with_suffix(out.suffix + ".enrichment.yaml")
    side.write_text(_yaml.safe_dump(enrichment_block(log, resolver),
                                    sort_keys=False), encoding="utf-8")
    click.echo(f"✓ {len(log)} enriched -> {out} (+ {side.name})")
