"""`d4d review` — the review pack for a generated record, and the check of a
review against it (#787)."""
from __future__ import annotations

import sys
from pathlib import Path

import click

from data_sheets_schema.constants import PROJECTS

from data_sheets_schema import backfill_checks as bc


@click.group()
def review():
    """Review a generated record against its instruction, bundle and receipts."""


def _provenance(method: str, label: str, project: str) -> Path:
    from data_sheets_schema import provenance as pv
    return pv.record_path_for(project, method, label, pv.CONCAT_DIR)


@review.command("pack")
@click.option("--method", default="claudecode_agent", show_default=True)
@click.option("--label", required=True)
@click.option("--project", type=click.Choice(PROJECTS), required=True)
@click.option("--instruction", "instruction_file", default=None, type=click.Path(exists=True, dir_okay=False),
              help="the instruction file the launcher sent; otherwise re-rendered from the record's spec")
@click.option("--receipted", default=25, show_default=True, help="receipted slots to sample")
@click.option("--receiptless", default=25, show_default=True, help="receiptless slots to sample")
def pack(method, label, project, instruction_file, receipted, receiptless):
    """Write `{PROJECT}_review_pack.yaml` beside the record: every chunk the
    receipt marked nothing_relevant, a seeded sample of receipted slots with
    their cited passage, the receiptless and reshaped slots, and the
    instruction's rules as a checklist — each item with its pointer and its
    question, and a closed verdict vocabulary per kind."""
    from data_sheets_schema.review_pack import write_pack
    prov = _provenance(method, label, project)
    if not prov.exists():
        raise click.ClickException(f"no provenance record at {prov}")
    out, p = write_pack(prov, Path(instruction_file) if instruction_file else None,
                        {"receipted_slots": receipted, "receiptless_slots": receiptless})
    kinds: dict[str, int] = {}
    for i in p["items"]:
        kinds[i["kind"]] = kinds.get(i["kind"], 0) + 1
    click.echo(f"✓ {out}")
    click.echo("   items: " + ", ".join(f"{k} {v}" for k, v in kinds.items()))
    click.echo(f"   instruction: {p['instruction']['basis']}")
    for g in p["gaps"]:
        click.echo(f"   ⚠️  {g}")


@review.command("check")
@click.option("--method", default="claudecode_agent", show_default=True)
@click.option("--label", required=True)
@click.option("--project", type=click.Choice(PROJECTS), required=True)
@click.option("--write", is_flag=True, help="write the `review` block into the provenance record")
@click.option("--strict", is_flag=True, help="exit 1 on any unanswered item or finding")
def check(method, label, project, write, strict):
    """Check `{PROJECT}_review.yaml` against its pack: every item answered
    once with a verdict from its kind's vocabulary and evidence; counts are
    affirmative and cannot_tell is its own number."""
    import hashlib

    import yaml

    from data_sheets_schema import backfill_checks as bc
    from data_sheets_schema.review_pack import check_review, record_paths
    prov = _provenance(method, label, project)
    if not prov.exists():
        raise click.ClickException(f"no provenance record at {prov}")
    paths = record_paths(prov)
    if not paths["pack"].exists():
        raise click.ClickException(f"no review pack at {paths['pack']}; run `d4d review pack` first")
    if not paths["review"].exists():
        raise click.ClickException(f"no review at {paths['review']}")
    pack = yaml.safe_load(paths["pack"].read_text(encoding="utf-8")) or {}
    pack["_sha256"] = hashlib.sha256(paths["pack"].read_bytes()).hexdigest()
    rev = yaml.safe_load(paths["review"].read_text(encoding="utf-8")) or {}
    block = check_review(pack, rev)
    click.echo(f"   {block['summary']}")
    for k, d in block["by_kind"].items():
        click.echo(f"   {k}: " + ", ".join(f"{v} {n}" for v, n in sorted(d.items())))
    for f in block["findings"][:20]:
        click.echo("   ❌ " + ", ".join(f"{k}={v}" for k, v in f.items()))
    if write:
        block["reviewer"] = {k: rev.get(k) for k in ("reviewer", "model", "reviewed_at") if rev.get(k)}
        block["artifacts"] = {"pack": {"path": str(paths["pack"]), "sha256": pack["_sha256"]},
                              "review": {"path": str(paths["review"]),
                                         "sha256": hashlib.sha256(paths["review"].read_bytes()).hexdigest()}}
        block["recorded_by"] = "d4d review check"
        bc.apply(prov, {"review": block}, overwrite=True)
        click.echo(f"   ✓ review block written to {prov}")
    if strict and (block["findings"] or block["unanswered"]):
        sys.exit(1)

@review.command("agree")
@click.option("--method", default="claudecode_agent", show_default=True)
@click.option("--label", required=True)
@click.option("--project", type=click.Choice(PROJECTS), required=True)
@click.option("--write", is_flag=True, help="write the reliability block into the provenance record's review block")
def agree_cmd(method, label, project, write):
    """Test-retest agreement between {P}_review.yaml and {P}_review_b.yaml
    against the same committed pack: percent agreement, Cohen's kappa on the
    affirmative/adverse/cannot_tell trichotomy, and every disagreement."""
    import hashlib

    import yaml

    from data_sheets_schema.provenance import ProvenanceRecord
    from data_sheets_schema.review_pack import agree, check_review, record_paths
    prov = _provenance(method, label, project)
    if not prov.exists():
        raise click.ClickException(f"no provenance record at {prov}")
    paths = record_paths(prov)
    for k in ("pack", "review", "review_b"):
        if not paths[k].exists():
            raise click.ClickException(f"missing {paths[k]}")
    pack = yaml.safe_load(paths["pack"].read_text(encoding="utf-8")) or {}
    pack["_sha256"] = hashlib.sha256(paths["pack"].read_bytes()).hexdigest()
    a = yaml.safe_load(paths["review"].read_text(encoding="utf-8")) or {}
    b = yaml.safe_load(paths["review_b"].read_text(encoding="utf-8")) or {}
    # A rating pair is only as good as its ratings: an invalid review
    # (duplicate ids, out-of-vocabulary verdicts, unknown items) must not
    # silently enter a reliability figure (#861).
    for name, rev in (("review", a), ("review_b", b)):
        bad = check_review(pack, rev)["findings"]
        if bad:
            raise click.ClickException(
                f"{paths[name]} has {len(bad)} check finding(s) "
                f"(first: {bad[0].get('kind')}); fix the review before pairing")
    rel = agree(pack, a, b)
    click.echo(f"   paired {rel['paired_items']} · class agreement {rel['percent_class_agreement']}% · "
               f"exact {rel['percent_exact_agreement']}% · kappa {rel['kappa_class']} · "
               f"adverse {rel['adverse_a']} vs {rel['adverse_b']}")
    for d in rel["disagreements"]:
        click.echo(f"   ≠ {d['id']} ({d['kind']}): {d['a']} vs {d['b']}")
    if write:
        import yaml as _y
        rec = _y.safe_load(bc._split_header(prov.read_text(encoding="utf-8"))[1]) or {}
        if not isinstance(rec.get("review"), dict):
            raise click.ClickException("no review block to attach reliability to; run `d4d review check --write` first")
        rec["review"]["reliability"] = {**rel,
            "review_b_sha256": hashlib.sha256(paths["review_b"].read_bytes()).hexdigest(),
            "recorded_by": "d4d review agree"}
        ProvenanceRecord(data=rec).write(prov)
        click.echo(f"   ✓ reliability written into {prov}")

