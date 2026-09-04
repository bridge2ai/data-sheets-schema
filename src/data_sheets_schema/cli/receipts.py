"""`d4d receipts` — check a run's coverage receipt and record the result (#708)."""
from __future__ import annotations

import sys
from pathlib import Path

import click

from data_sheets_schema.constants import PROJECTS


@click.group()
def receipts():
    """Coverage and claim receipts: what the agent says it read, checked."""


def _run_paths(method: str, label: str, project: str) -> dict[str, Path]:
    from data_sheets_schema.provenance import CONCAT_DIR
    base = method[:-5] if method.endswith("_core") else method
    core_dir = CONCAT_DIR / f"{base}_core" / label
    return {"core_dir": core_dir,
            "full": CONCAT_DIR / base / label / f"{project}_d4d.yaml",
            "provenance": core_dir / f"{project}_provenance.yaml"}


@receipts.command("check")
@click.option("--method", default=None, help="run directory family; defaults to the one the label lives in (claudecode_agent or claudecode_api, #934)")
@click.option("--label", required=True)
@click.option("--project", type=click.Choice(PROJECTS), required=True)
@click.option("--write", is_flag=True,
              help="write the `receipts` block into the provenance record and the "
                   "claim-receipt sidecar beside it")
@click.option("--strict", is_flag=True,
              help="exit 1 on any unreviewed chunk, unverified snippet or finding")
@click.option("--bundle", "bundle_opt", default=None, type=click.Path(exists=True, dir_okay=False),
              help="the bundle the run read; needed only before the provenance record "
                   "exists and the full record's header does not name it")
def check(method, label, project, write, strict, bundle_opt):
    """Validate `{PROJECT}_coverage_receipt.yaml` against the chunk manifest,
    the bundle and the full record, with affirmative counts.

    Prints `chunks N/N reviewed · snippets M/M verified · slots S/T with a
    receipt` and every finding. A receipt that is absent is reported as
    unchecked, never as clean; whether that is a defect depends on whether
    the run's procedure was to write one, which the provenance record says
    (`inputs.receipt_expected`).
    """
    from data_sheets_schema.cli.method import resolve_method
    method = method or resolve_method(label, project)
    import yaml

    from data_sheets_schema import backfill_checks as bc
    from data_sheets_schema import receipts as rc

    p = _run_paths(method, label, project)
    if p["provenance"].exists():
        record = yaml.safe_load(bc._split_header(p["provenance"].read_text(encoding="utf-8"))[1]) or {}
        inputs = record.get("inputs") or {}
        bundle = bc.declared_bundle(record)
        md5, expected = inputs.get("bundle_md5"), bool(inputs.get("receipt_expected"))
    else:
        # Before the record exists — Phase 1 runs this before Phase 2 (#730).
        # Everything the check needs is on disk; the bundle comes from the
        # full record's own header, and its md5 from the bytes there now.
        if write:
            raise click.ClickException(f"no provenance record at {p['provenance']} to write into; "
                                       "run without --write until the record step")
        from data_sheets_schema.provenance import _md5, parse_header
        header = parse_header(p["full"])
        declared = bundle_opt or header.get("Source bundle") or header.get("Source")
        if not declared:
            raise click.ClickException(f"no provenance record yet and {p['full']} names no "
                                       "`# Source bundle:`; pass --bundle")
        bundle = Path(declared)
        md5 = _md5(bundle) if bundle.exists() else None
        expected = True
        click.echo(f"   · no provenance record yet; checking against {bundle} as on disk")
    block = rc.block_for(p["full"], rc.receipt_path(p["core_dir"], project), bundle, md5, expected)
    if not block.get("checked"):
        click.echo(f"   · unchecked: {block['reason']}"
                   + ("" if block["expected"] else " (this run's procedure wrote none)"))
    else:
        click.echo(f"   {block['summary']}")
        for f in block["findings"]:
            click.echo("   ❌ " + ", ".join(f"{k}={v}" for k, v in f.items()))
        for nc in block["non_checks"]:
            click.echo(f"   · not checked here: {nc}")
    if write:
        block["recorded_by"] = "d4d receipts check"
        bc.apply(p["provenance"], {"receipts": block}, overwrite=True)
        click.echo(f"   ✓ receipts block written to {p['provenance']}")
        if block.get("checked"):
            receipt = rc.load_receipt(rc.receipt_path(p["core_dir"], project))
            full = yaml.safe_load(p["full"].read_text(encoding="utf-8")) or {}
            out = rc.claims_path(p["core_dir"], project)
            out.write_text(yaml.safe_dump(rc.claim_receipts(receipt, full), sort_keys=False,
                                          allow_unicode=True), encoding="utf-8")
            click.echo(f"   ✓ claim receipts written to {out}")
    # A run whose procedure wrote no receipt is not failed by --strict: the
    # block is not a metric for it (#727). Expected-and-unchecked is.
    if strict and block.get("expected") and not block.get("checked"):
        sys.exit(1)
    if strict and block.get("checked") and strict_failure(block):
        sys.exit(1)


def strict_failure(block: dict) -> bool:
    """What `--strict` fails on: exactly the gate's receipt floors (#881).

    The first version read `findings` wholesale, so a clean run with
    wrong-chunk attributions — reported, never gated (#763) — strict-failed
    while the canary gate passed it. One definition, `canary.receipt_floors`,
    for both.
    """
    from data_sheets_schema.canary import receipt_floors
    return any(v > 0 for v in receipt_floors(block).values())


@receipts.command("invert")
@click.option("--receipt", "receipt_file", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("--full", "full_file", default=None, type=click.Path(exists=True, dir_okay=False),
              help="with the full record, name each claim's derived-core path")
@click.option("--out", "out_file", default=None, type=click.Path(dir_okay=False))
def invert(receipt_file, full_file, out_file):
    """Write the claim receipts (by slot) for a coverage receipt (by chunk)."""
    import yaml

    from data_sheets_schema import receipts as rc
    receipt = rc.load_receipt(Path(receipt_file))
    full = (yaml.safe_load(Path(full_file).read_text(encoding="utf-8")) or {}) if full_file else None
    text = yaml.safe_dump(rc.claim_receipts(receipt, full), sort_keys=False, allow_unicode=True)
    if out_file:
        Path(out_file).write_text(text, encoding="utf-8")
        click.echo(f"✓ {out_file}")
    else:
        click.echo(text, nl=False)
