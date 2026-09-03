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

@review.command("disposition")
@click.option("--method", default="claudecode_agent", show_default=True)
@click.option("--label", required=True)
@click.option("--project", type=click.Choice(PROJECTS), required=True)
@click.option("--item", required=True, help="the review item this disposes of (e.g. slot-008, rule-01)")
@click.option("--disposition", type=click.Choice(["retain", "amend"]), required=True)
@click.option("--note", required=True, help="why: what the finding was and what this disposition rests on")
@click.option("--path", "slot_path", default=None, help="amend: the slot path whose value the replacement changes")
@click.option("--replace", "old", default=None,
              help="amend: the text to replace, matched across the file's line wrapping; must occur once")
@click.option("--with", "new", default=None, help="amend: the replacement text")
@click.option("--execute", is_flag=True, help="write; without it, report what would change")
def disposition(method, label, project, item, disposition, note, slot_path, old, new, execute):
    """Record a curator's disposition of one review finding (#903).

    `retain` documents a finding and leaves the record as generated — the
    review block is the record of the defect. `amend` applies one literal
    replacement to the full record (and the core record where it carries the
    same text), records both files' sha256 before and after, and recomputes
    the record's check blocks so they describe the amended bytes. Either way
    the act is written under `dispositions` in the provenance record: a
    generated record edited by hand without that entry is indistinguishable
    from one the generator wrote.

    Evaluations that predate an amendment are not re-attributed: the entry
    names them as predating it.
    """
    import hashlib
    from datetime import datetime, timezone

    import yaml

    from data_sheets_schema.provenance import ProvenanceRecord
    from data_sheets_schema.review_pack import record_paths

    prov = _provenance(method, label, project)
    if not prov.exists():
        raise click.ClickException(f"no provenance record at {prov}")
    paths = record_paths(prov)
    if not paths["review"].exists():
        raise click.ClickException(f"no review at {paths['review']}; a disposition answers a review finding")
    rev = yaml.safe_load(paths["review"].read_text(encoding="utf-8")) or {}
    items = rev.get("items") if isinstance(rev, dict) else rev
    found = next((i for i in (items or []) if isinstance(i, dict) and i.get("id") == item), None)
    if found is None:
        raise click.ClickException(f"{paths['review']} has no item {item!r}")
    entry: dict = {"item": item, "verdict": found.get("verdict"), "disposition": disposition, "note": note,
                   "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "recorded_by": "d4d review disposition"}
    click.echo(f"   {item} ({found.get('verdict')}) → {disposition}")

    if disposition == "amend":
        import re

        from data_sheets_schema.receipts import _resolve_value, populated_leaves
        if not old or new is None or not slot_path:
            raise click.ClickException("amend needs --path, --replace and --with")
        if old == new:
            raise click.ClickException("--replace and --with are identical; nothing to amend")
        # The records are the model's own YAML text, wrapped at its width and
        # not round-tripped by any dumper; the edit is on the raw text, with
        # each whitespace run in --replace matching any run in the file, and
        # is proven afterwards by the parse: exactly one leaf differs, at
        # --path, and it differs by exactly this replacement.
        pattern = re.compile(r"\s+".join(re.escape(part) for part in old.split()))
        files = {}
        for name in ("full", "core"):
            p = paths[name]
            if not p.exists():
                continue
            text = p.read_text(encoding="utf-8")
            hits = list(pattern.finditer(text))
            if name == "full" and len(hits) != 1:
                raise click.ClickException(f"--replace occurs {len(hits)} time(s) in {p}; an amendment names one place")
            if len(hits) > 1:
                raise click.ClickException(f"--replace occurs {len(hits)} times in {p}; refusing an ambiguous edit")
            if not hits:
                continue
            m = hits[0]
            amended = text[:m.start()] + new + text[m.end():]
            try:
                before_doc, after_doc = yaml.safe_load(text), yaml.safe_load(amended)
            except yaml.YAMLError as exc:
                raise click.ClickException(f"the amended {p.name} does not parse as YAML: {exc}") from exc
            leaves_b, leaves_a = dict(populated_leaves(before_doc)), dict(populated_leaves(after_doc))
            changed = {k for k in set(leaves_b) | set(leaves_a) if leaves_b.get(k) != leaves_a.get(k)}
            if changed != {slot_path}:
                raise click.ClickException(
                    f"{p.name}: the edit changes {sorted(changed) or 'nothing'}, not exactly {slot_path!r}; "
                    "the replacement crosses a value boundary or names the wrong path")
            want = " ".join(str(_resolve_value(before_doc, slot_path)[1]).split()).replace(" ".join(old.split()), " ".join(new.split()), 1)
            got = " ".join(str(_resolve_value(after_doc, slot_path)[1]).split())
            if got != want:
                raise click.ClickException(f"{p.name}: the value at {slot_path} after the edit is not the value "
                                           "before it with the replacement applied")
            files[name] = {"path": str(p), "sha256_before": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                           "sha256_after": hashlib.sha256(amended.encode("utf-8")).hexdigest(), "_text": amended}
            click.echo(f"   {name}: one occurrence at {slot_path} → will be replaced")
        entry.update({"path": slot_path, "replace": old, "with": new,
                      "files": {k: {kk: vv for kk, vv in v.items() if kk != "_text"} for k, v in files.items()},
                      "evaluations_predating": sorted(str(p) for p in Path("data/evaluation_llm").glob(
                          f"*/label_aware/{project}_*{label.rsplit('_', 1)[-1]}_evaluation.json")
                          if label.split("_")[0] in p.read_text(encoding="utf-8", errors="ignore")[:4000])})
    if not execute:
        click.echo("   dry run; re-run with --execute to write")
        return

    def append_entry() -> None:
        rec = yaml.safe_load(bc._split_header(prov.read_text(encoding="utf-8"))[1]) or {}
        rec.setdefault("dispositions", []).append(entry)
        if "_validation" in entry:
            rec["validation"] = entry.pop("_validation")
        ProvenanceRecord(data=rec).write(prov)

    if disposition == "amend":
        # The records are written and the entry recorded in one step before
        # anything that can fail: an amended record with no `dispositions`
        # entry is the #657 laundering (#907 review). The recompute and the
        # re-validation follow; if either raises, the entry already names
        # the edit and gains the error.
        for v in files.values():
            Path(v["path"]).write_text(v["_text"], encoding="utf-8")
        append_entry()
        try:
            # the check blocks now describe bytes the run did not write:
            # recompute the ones that read the records (grounding only where
            # the bundle has not drifted — compute() decides; apply() never
            # erases a checked block), never the review block
            blocks = bc.compute(prov)
            bc.apply(prov, {k: v for k, v in blocks.items() if k != "review"}, overwrite=True)
            click.echo("   check blocks recomputed on the amended records")
            # The validation verdict pins the artifacts' md5s (#426), so the
            # amended files would report STALE — the signal for an edit
            # nobody recorded. This edit is recorded, so the verdict is
            # refreshed in the same act, naming this command.
            from data_sheets_schema.api_runner import RunSpec, validate_outputs, validation_block
            spec = RunSpec(project=project, arm="", method=method,
                           bundle=Path("data/preprocessed/concatenated") / f"{project}_preprocessed.txt", label=label)
            problems = validate_outputs(spec)
            rec = yaml.safe_load(bc._split_header(prov.read_text(encoding="utf-8"))[1]) or {}
            rec["validation"] = validation_block(spec, problems, recorded_by="d4d review disposition")
            rec["dispositions"][-1]["validation_after"] = "valid" if not problems else f"{len(problems)} problem(s)"
            ProvenanceRecord(data=rec).write(prov)
            click.echo(f"   re-validated: {rec['dispositions'][-1]['validation_after']}")
        except Exception as exc:                                     # noqa: BLE001
            rec = yaml.safe_load(bc._split_header(prov.read_text(encoding="utf-8"))[1]) or {}
            rec["dispositions"][-1]["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
            ProvenanceRecord(data=rec).write(prov)
            raise click.ClickException(f"amended and recorded, but the recompute/re-validation failed: {exc}; "
                                       "run `d4d provenance backfill-checks --overwrite` and "
                                       "`d4d runs validate --recheck` for this record") from exc
    else:
        append_entry()
    click.echo(f"   ✓ disposition written to {prov}")


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

