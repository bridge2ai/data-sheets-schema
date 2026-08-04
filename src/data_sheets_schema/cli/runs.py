"""Run-tracking commands for the D4D CLI."""

import click
from pathlib import Path


@click.group()
def runs():
    """Track and compare parallel D4D generation runs."""
    pass


@runs.command()
@click.option('--label', 'labels', multiple=True,
              help='Run label(s) to archive; repeatable.')
@click.option('--unattested', is_flag=True,
              help='Archive runs with a gap in something that determines the output.')
@click.option('--project', 'project', multiple=True,
              help='Archive only these projects within the labels; repeatable.')
@click.option('--reason', default=None, help='Recorded in the archive README.')
@click.option('--execute', is_flag=True,
              help='Actually move. Without it, only report what would move.')
def archive(labels, unattested, project, reason, execute):
    """Move runs out of analysis into data/ATTIC, without deleting them.

    `discover()` walks data/d4d_concatenated, so a move to ATTIC removes a run
    from every analysis path at once. Nothing is deleted and the layout is
    preserved, so `d4d runs restore` is the same move reversed.

    Selection is by attestation, not by `record_mode`. Archiving everything
    merely "reconstructed" would remove the 2026-07-27 tuned arm, whose records
    pin the bundle by verified md5, the schema, the model and every output hash,
    and whose only gap is the hardware. `--unattested` targets the runs that
    genuinely cannot be placed: the 2026-04 and 2026-07-23 series, whose bundles
    were first committed on 2026-07-28, so the bytes they consumed are
    unverifiable rather than merely unrecorded.

    Prefer `--require-attested` on compare/arm-delta, which excludes the same
    runs per-analysis without moving anything.
    """
    from data_sheets_schema.runs import (
        NO_RECORD, PARTIAL, archive_runs, attestation, discover,
    )

    targets = set(labels)
    unplaceable: set[str] = set()
    if unattested:
        for run in discover():
            # Deterministic mappings are not stochastic generations and carry no
            # generation provenance by design; the validate sweep already skips
            # them for the same reason.
            if run.is_core or run.deterministic:
                continue
            for proj in run.projects:
                # PARTIAL only — never NO_RECORD. A run with no provenance at
                # all is a different problem, and archiving is not its answer:
                # the merged records have none because provenance.py cannot yet
                # express a derived record, which is tracked work rather than an
                # unattestable run.
                if attestation(run.method, run.label, proj) == PARTIAL:
                    targets.add(run.label)
                    unplaceable.add(proj)

    # Name the projects rather than skipping mixed labels. A label is not a unit
    # of attestation, and an earlier version dropped whole labels to avoid
    # collateral — which left CM4AI's crateonly records in the corpus because
    # CHORUS and VOICE share their label. Moving by project takes exactly the
    # unplaceable records.
    if unattested and not project:
        project = tuple(sorted(unplaceable))
        if project:
            click.echo(f"   archiving only: {', '.join(project)}")
    if not targets:
        # Distinguish "you asked for nothing" from "nothing matched". Reporting
        # a clean corpus as a usage error reads as though the command were
        # invoked wrongly.
        if unattested:
            click.echo("No unattestable runs found — every run in the corpus "
                       "can be placed. Nothing to archive.")
        else:
            click.echo("Nothing selected. Pass --label or --unattested.")
        return

    default_reason = (
        "These runs have a gap in something that determines their output — most "
        "often an input bundle whose consumed bytes cannot be verified, because "
        "the bundles were first committed after the runs executed. Runs whose "
        "provenance was merely reconstructed, but which pin their inputs, "
        "schema, model and outputs, are NOT archived: they can be placed and "
        "reproduced, and only their hardware is unrecorded.")
    res = archive_runs(sorted(targets), reason=reason or default_reason,
                       projects=list(project) or None, dry_run=not execute)
    if res["matched_nothing"]:
        click.echo(f"No records matched. Labels: {', '.join(sorted(targets))}"
                   + (f"; projects: {', '.join(project)}" if project else "")
                   + ".\nNothing was archived and no note was written — check "
                     "the names.")
        return

    verb = "Moved" if execute else "Would move"
    click.echo(f"{verb} {res['count']} record file(s) across "
               f"{len(targets)} label(s) -> {res['archive']}")
    for src, dest in res["moved"]:
        click.echo(f"   {src}")
    if res["would_empty"]:
        click.echo(f"\n{'Removed' if execute else 'Would remove'} "
                   f"{len(res['would_empty'])} emptied director(ies):")
        for d in res["would_empty"]:
            click.echo(f"   {d}")
    if not execute:
        click.echo("\nDry run. Re-run with --execute to move them.")


@runs.command()
@click.option('--label', 'labels', multiple=True,
              help='Run label(s) to restore; default all archived.')
@click.option('--project', 'projects', multiple=True,
              help='Restore only these projects; default all.')
@click.option('--execute', is_flag=True)
def restore(labels, projects, execute):
    """Move archived records back into data/d4d_concatenated."""
    from data_sheets_schema.runs import restore_runs
    res = restore_runs(list(labels), projects=list(projects) or None,
                       dry_run=not execute)
    verb = "Restored" if execute else "Would restore"
    click.echo(f"{verb} {res['count']} record file(s)")
    for src, dest in res["moved"]:
        click.echo(f"   {dest}")
    if not execute and res["count"]:
        click.echo("\nDry run. Re-run with --execute.")


@runs.command("canonical")
@click.option("--project", default=None, help="Report one project only.")
@click.option("--config", default=None,
              help="Only runs whose label starts with this, e.g. "
                   "2026-07-31_claude-opus-5-generic-v2.")
@click.option("--paths-only", is_flag=True,
              help="Print record paths and nothing else, for piping.")
@click.option("--missing", is_flag=True,
              help="List projects that have no canonical record instead.")
def canonical_cmd(project, config, paths_only, missing):
    """Which record is the datasheet, per project.

    `select` marks a replicate canonical and nothing read the mark (#306), so
    the question it answers was answerable only by someone who knew to open
    provenance. This reads it.

    A project with no eligible replicate is absent rather than guessed at, and
    `--missing` names those — the count that matters for scoping an evaluation
    is how many projects *have* one, which is three of four while no VOICE
    replicate validates (#292).
    """
    from data_sheets_schema.constants import PROJECTS
    from data_sheets_schema.runs import canonical_runs

    found = canonical_runs(config=config)
    if project:
        found = {k: v for k, v in found.items() if k == project}

    if missing:
        gap = [p for p in PROJECTS if p not in canonical_runs(config=config)]
        if project:
            gap = [p for p in gap if p == project]
        for p in gap:
            click.echo(p)
        if not gap:
            click.echo("Every project has a canonical record.", err=True)
        return

    if not found:
        click.echo("No canonical record found. Run `d4d runs select --execute`.",
                   err=True)
        raise SystemExit(1)

    if paths_only:
        for entry in found.values():
            for key in ("full", "core"):
                if entry.get(key):
                    click.echo(entry[key])
        return

    for name, entry in found.items():
        click.echo(f"{name}")
        click.echo(f"   label     {entry['label']}")
        click.echo(f"   full      {entry['full']}")
        click.echo(f"   core      {entry['core']}")
        click.echo(f"   chosen    from {entry['candidates']} candidates — "
                   f"{entry['criterion']}")
    gap = [p for p in PROJECTS if p not in found and not project]
    if gap:
        click.echo(f"\nNo canonical record: {', '.join(gap)}", err=True)


@runs.command("check")
@click.option("--method", default=None)
@click.option("--label", default=None)
@click.option("--project", default=None)
@click.option("--strict", is_flag=True,
              help="Exit non-zero if any run fails, for use as a gate.")
def check_cmd(method, label, project, strict):
    """Verify runs satisfy the live-provenance requirement.

    Runs labelled on or after the cutoff must have written their own provenance.
    Earlier runs are reported as not-required rather than failed: 33 of them are
    fully attested despite being reconstructed, and failing those retroactively
    would discard placeable evidence to enforce a rule that postdates them.

    Use `--strict` after a generation run so a missing record fails the step
    rather than being noticed later.
    """
    from data_sheets_schema.runs import check_provenance, discover, is_complete

    rows = []
    for run in discover():
        if run.is_core or run.deterministic:
            continue
        if method and run.method != method:
            continue
        if label and run.label != label:
            continue
        for proj in run.projects:
            if project and proj != project:
                continue
            if not is_complete(run.method, run.label, proj):
                continue
            rows.append(check_provenance(run.method, run.label, proj))

    failed = [r for r in rows if not r["ok"]]
    required = [r for r in rows if r["required"]]
    for r in failed:
        click.echo(f"   ❌ {r['project']:9} {r['label']:44} {r['reason']}")
    click.echo(f"\n{len(rows)} run(s) checked, {len(required)} subject to the "
               f"requirement, {len(failed)} failing")
    if not failed:
        click.echo("All runs subject to the live-provenance requirement satisfy it.")
    if strict and failed:
        raise SystemExit(1)


@runs.command('list')
@click.option('--arm', default=None, help='Filter by arm.')
@click.option('--full-only', is_flag=True, help='Hide the _core companions.')
def list_runs(arm, full_only):
    """List every generation run found on disk."""
    from data_sheets_schema.runs import discover, needs_replicate_label

    found = discover()
    if arm:
        found = [r for r in found if r.arm == arm]
    if full_only:
        found = [r for r in found if not r.is_core]
    if not found:
        click.echo("No runs found."); return

    click.echo(f"{'arm':<23}{'method':<36}{'label':<34}{'index':>6}  projects")
    for r in found:
        if r.deterministic:
            rep = 'det'
        elif r.legacy_revision is not None:
            rep = f'rev{r.legacy_revision}'
        else:
            rep = f'rep{r.replicate}' if r.replicate else '—'
        click.echo(f"{r.arm:<23}{r.method:<36}{r.label:<34}{rep:>6}  "
                   f"{','.join(r.projects)}")

    legacy = [r for r in found if r.legacy_revision is not None]
    if legacy:
        click.echo(f"\n  rev{{N}} = legacy `-r{{N}}` label meaning a REVISION "
                   "(changed pipeline), not a replicate.")
        click.echo("  Those runs are not comparable to each other as samples.")


@runs.command()
@click.option('--method', required=True, help='e.g. claudecode_agent')
@click.option('--project', required=True)
@click.option('--label', 'labels', multiple=True,
              help='Run labels to compare; default all for that method.')
@click.option('--require-live', is_flag=True,
              help='Exclude runs that did not write their own provenance. '
                   'Usually too strict — prefer --require-attested.')
@click.option('--require-attested', is_flag=True,
              help='Exclude runs with a gap in something that determines the output.')
def compare(method, project, labels, require_live, require_attested):
    """Compare slot coverage across replicates of one method."""
    from data_sheets_schema.runs import compare as do_compare, discover

    if not labels:
        labels = [r.label for r in discover() if r.method == method]
    result = do_compare(method, project, list(labels),
                        require_live=require_live,
                        require_attested=require_attested)
    if 'error' in result:
        click.echo(f"❌ {result['error']}", err=True)
        raise SystemExit(1)

    if not result['same_procedure']:
        click.echo("⚠️  THESE ARE NOT REPLICATES — the runs used different "
                   "procedures.\n   Their differences measure the pipeline "
                   "change, not sampling variance.\n")
        for lab, fp in result['procedures'].items():
            desc = fp.get('Generation Method') or fp.get('Agent runtime') or '?'
            click.echo(f"     {lab:<36} {desc}")
        click.echo("")

    if result.get('excluded_not_live'):
        click.echo(f"⚠️  excluded, provenance reconstructed not observed: "
                   f"{', '.join(result['excluded_not_live'])}\n")
    elif result.get('excluded_unattested'):
        click.echo(f"⚠️  excluded, output-determining fields incomplete: "
                   f"{', '.join(result['excluded_unattested'])}\n")
    elif result.get('unattested'):
        click.echo(f"⚠️  {len(result['unattested'])} run(s) cannot be fully "
                   f"placed: {', '.join(result['unattested'])}")
        click.echo("   Re-run with --require-attested to exclude them.\n")
    elif result.get('reconstructed'):
        # Reported even when not excluding: an agreement figure over
        # reconstructed records rests on conditions nobody observed, and the
        # reader should see that without having asked.
        click.echo(f"ℹ️  {len(result['reconstructed'])} of "
                   f"{len(result['provenance_modes'])} runs have reconstructed "
                   f"provenance, but all are fully attested — inputs, schema, "
                   f"model and outputs are pinned.")
        click.echo("   Only the hardware is unrecorded, which cannot affect a "
                   "generation.\n")

    if result.get('excluded_derived'):
        # Say it, rather than letting the record vanish. A silent exclusion
        # leaves the operator to wonder whether the merge ran at all.
        click.echo(f"ℹ️  excluded as derived (built from the runs being "
                   f"compared, so including it would bias the agreement it is "
                   f"measured against): "
                   f"{', '.join(result['excluded_derived'])}\n")

    if result.get('excluded_incomplete'):
        click.echo(f"⚠️  excluded as still running / incomplete: "
                   f"{', '.join(result['excluded_incomplete'])}\n")

    click.echo(f"{project} — {method}")
    for lab, n in result['counts'].items():
        click.echo(f"  {lab:<36} {n:>3} slots")
    click.echo(f"\n  stable across all runs: {len(result['stable'])}")
    click.echo(f"  varying:                {len(result['varying'])}")
    click.echo(f"  agreement:              {result['agreement']:.1%}")
    if result['varying']:
        click.echo(f"\n  slots not present in every run:\n    {', '.join(result['varying'])}")


@runs.command("validate")
@click.option("--method", help="limit to one method (default: all discovered)")
@click.option("--project", help="limit to one project")
@click.option("--label", help="limit to one run label")
@click.option("--recheck", is_flag=True,
              help="re-validate runs whose provenance already records a result")
@click.option("--dry-run", is_flag=True, help="list what would be validated")
def validate_cmd(method, project, label, recheck, dry_run):
    """Record whether each run's records validate, into its provenance.

    `is_complete()` only checks that three files exist, so an invalid record is
    "complete" and gets analysed. Validity is read from provenance rather than
    computed on demand — the corpus holds 100+ records and each validation costs
    seconds, so validating inside `compare()` would make it unusable. This sweep
    populates that field once.

    A run with no recorded result is UNVERIFIED, never assumed valid.
    """
    import yaml as _yaml
    from data_sheets_schema.api_runner import (
        RunSpec, validate_outputs, validation_block,
    )
    from data_sheets_schema.provenance import (
        ProvenanceRecord, record_path_for,
    )
    from data_sheets_schema.runs import (
        STALE, UNVERIFIED, discover, is_complete, validation_status,
    )

    targets = []
    for run in discover():
        if run.is_core or run.deterministic:
            continue          # core records are validated with their full pair
        if method and run.method != method:
            continue
        if label and run.label != label:
            continue
        for proj in run.projects:
            if project and proj != project:
                continue
            if not is_complete(run.method, run.label, proj):
                continue
            status = validation_status(run.method, run.label, proj)
            # STALE is re-validated like UNVERIFIED: its verdict
            # describes bytes the file no longer has.
            if not recheck and status not in (UNVERIFIED, STALE):
                continue
            targets.append((run.method, run.label, proj))

    click.echo(f"🔍 {len(targets)} run(s) to validate")
    if dry_run:
        for m, l, p in targets:
            click.echo(f"   {p:9} {m:34} {l}")
        return

    passed = failed = norec = 0
    for m, l, p in targets:
        spec = RunSpec(project=p, arm="", method=m,
                       bundle=Path("data/preprocessed/concatenated") /
                              f"{p}_preprocessed.txt", label=l)
        problems = validate_outputs(spec)
        rec = record_path_for(p, m, l)
        icon = "✓" if not problems else "❌"
        click.echo(f"   {icon} {p:9} {l}")
        for q in problems:
            click.echo(f"        {q.get('error','')[:130]}")
        if not rec.exists():
            # Do not invent a provenance record here. It would have to assert a
            # model, inputs and a mode this command cannot observe, which is the
            # class of false claim provenance.py exists to prevent.
            norec += 1
            continue
        data = _yaml.safe_load(rec.read_text(encoding="utf-8")) or {}
        # validation_block, not an inline dict: it binds the verdict to the
        # artifacts' md5s so a record edited afterwards reports STALE instead of
        # carrying a verdict about bytes that no longer exist.
        data["validation"] = validation_block(spec, problems,
                                              recorded_by="d4d runs validate")
        # Rewrite through Record.write so the file keeps its header. Dumping
        # `data` directly loses the two leading comment lines that point a
        # reader at the module defining this format — safe_load drops comments
        # and safe_dump cannot restore them. An earlier sweep stripped them
        # from 97 records this way.
        ProvenanceRecord(data=data).write(rec)
        passed += 1 if not problems else 0
        failed += 1 if problems else 0

    click.echo(f"\n{passed} valid, {failed} invalid, "
               f"{norec} with no provenance record to update")
    if norec:
        click.echo("Runs without a provenance record stay UNVERIFIED. Backfill "
                   "one with `d4d provenance backfill` first.")


@runs.command("merge")
@click.option("--method", default="claudecode_agent",
              help="Method directory the replicates live under.")
@click.option("--project", required=True)
@click.option("--label", "labels", multiple=True,
              help="Replicate labels to merge. Omit to use every replicate of "
                   "--config.")
@click.option("--config", default=None,
              help="Merge every replicate sharing this config prefix, e.g. "
                   "2026-07-31_claude-opus-5-generic-v2.")
@click.option("--out-label", default=None,
              help="Label to write the merged record under "
                   "(default: <config>_merged).")
@click.option("--unguarded", is_flag=True,
              help="Merge referent-bearing fields too. Off by default: "
                   "replicates can describe different releases, and splicing "
                   "a version from one into a record built on another states "
                   "something no replicate said.")
@click.option("--execute", is_flag=True,
              help="Write the record. Without this, report and write nothing.")
def merge_cmd(method, project, labels, config, out_label, unguarded, execute):
    """Combine replicates into one record that maximises coverage.

    Replicates differ in *coverage* more than in quality — each populates slots
    the others miss — so a union covers more of the schema than any single
    replicate, without preferring one on a score that could not discriminate
    them (#176).

    The merged record is `record_mode: derived`, never `live`: it is not
    something a model produced, and provenance names every contributor by hash
    and states the rule that combined them.

    **`d4d runs select` is the recommended way to get a shippable record, and
    it argues against this command.** Replicates state different facts on
    47-63% of the slots they share, so a union splices across referents — one
    replicate's participant count beside another's DOI — to gain 1-5 slots.
    That objection is about coherence and this command's case is about
    coverage; both are true, and the two commands existing without naming each
    other is how a reader ends up believing whichever help text they opened.
    Use this when a union is what you want and you can defend the splice.
    """
    import yaml as _yaml
    from data_sheets_schema.merge import union_merge, write_merge

    from data_sheets_schema.runs import CONCAT_DIR
    base_dir = CONCAT_DIR / method
    if config and not labels:
        labels = tuple(sorted(
            p.name for p in base_dir.glob(f"{config}_rep*") if p.is_dir()))
    if not labels:
        raise click.ClickException(
            "give --label at least twice, or --config to take every replicate")
    if len(labels) < 2:
        raise click.ClickException(
            f"merging needs at least two replicates; got {len(labels)}")

    records, sources = {}, {}
    for lab in labels:
        path = base_dir / lab / f"{project}_d4d.yaml"
        if not path.exists():
            raise click.ClickException(f"no record at {path}")
        loaded = _yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise click.ClickException(f"{path} is not a record")
        records[lab], sources[lab] = loaded, path

    try:
        result = union_merge(records, project=project, source_paths=sources,
                             guarded=not unguarded)
    except ValueError as exc:
        # `check_sources` refuses to combine runs whose conditions cannot be
        # established — a derived record inherits its contributors' standing,
        # so merging an unattested run would launder it. That is a refusal to
        # report, not a crash to print a traceback for.
        raise click.ClickException(str(exc)) from exc

    click.echo(f"{project} — {len(records)} replicates under {method}")
    for lab in sorted(records):
        contributed = sum(1 for v in result.source_of.values() if v == lab)
        click.echo(f"   {lab:52s} {len(records[lab]):3d} slots, "
                   f"{contributed:3d} contributed")
    union = len(result.record)
    best = max(len(r) for r in records.values())
    click.echo(f"   {'merged':52s} {union:3d} slots "
               f"(+{union - best} over the best single replicate)")
    if result.contested:
        click.echo(f"\n{result.contested} slot(s) are held by more than one "
                   f"replicate. Without a scorer the base's value is used for "
                   f"each, so the merge is the base record plus the slots only "
                   f"the others had — it does not adjudicate between differing "
                   f"values.")
    if result.guarded:
        click.echo("Referent-bearing fields taken from the base replicate only "
                   f"({result.base}); --unguarded to merge them too.")

    out = out_label or f"{(config or labels[0].rsplit('_rep', 1)[0])}_merged"
    target = base_dir / out / f"{project}_d4d.yaml"
    if not execute:
        click.echo(f"\nDry run. Would write {target}")
        click.echo("Re-run with --execute to write it.")
        return
    write_merge(result, target, sources=sources, project=project,
                method=method, label=out)
    click.echo(f"\nWrote {target}")
    click.echo("record_mode: derived — not a generated record. `d4d runs "
               "compare` excludes it from agreement figures and says so, "
               "because it is built from the runs those figures measure.")


def _validates_one(record: Path, schema: str, cls: str) -> bool:
    import subprocess
    try:
        return subprocess.run(
            ["poetry", "run", "linkml-validate", "-s", schema, "-C", cls,
             str(record)], capture_output=True, text=True,
            timeout=300).returncode == 0
    except Exception:                                   # noqa: BLE001
        return False


def _validates(record: Path) -> tuple[bool, str]:
    """Both records a run ships, not just the full one.

    Marking a run canonical marks its core record too, so judging it on the full
    record alone can bless a run that cannot ship half of itself. CM4AI rep1 in
    the 2026-07-31 generic-v2 config is exactly that — full valid, core invalid
    — and it is only excluded today because it loses on coverage (#237).

    Returns (ok, detail) so the report can say *which* record failed; "invalid"
    alone sends the reader to the wrong file.
    """
    full_schema = "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
    core_schema = "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml"
    core = (record.parent.parent.parent / f"{record.parent.parent.name}_core"
            / record.parent.name / f"{record.name[:-len('_d4d.yaml')]}_d4d_core.yaml")
    full_ok = _validates_one(record, full_schema, "Dataset")
    if not core.exists():
        return False, "no core record"
    core_ok = _validates_one(core, core_schema, "CoreDataset")
    if full_ok and core_ok:
        return True, "valid"
    if not full_ok and not core_ok:
        return False, "invalid (full and core)"
    return False, f"invalid ({'full' if not full_ok else 'core'})"


@runs.command("select")
@click.option("--method", default="claudecode_agent",
              help="Method directory the replicates live under.")
@click.option("--project", required=True)
@click.option("--config", required=True,
              help="Config prefix whose replicates are the candidates, e.g. "
                   "2026-07-31_claude-opus-5-generic-v2.")
@click.option("--allow-unverified", is_flag=True,
              help="Consider replicates whose validation status is unknown. "
                   "Off by default: absence of evidence is not validity.")
@click.option("--execute", is_flag=True,
              help="Record the choice in the winner's provenance. Without "
                   "this, report and write nothing.")
def select_cmd(method, project, config, allow_unverified, execute):
    """Mark one replicate canonical, keeping all of them.

    Selection, not merging. Replicates state different facts on **47-63% of the
    slots they share** (generic-v2, judged equivalence), for a coverage gain
    from merging of 1-5 slots (#229) — and a spliced record can assert a
    participant count from one referent and a DOI from another. A single
    replicate is internally coherent because one generation produced it.

    That figure read 77-98% here until #169 was settled. It was byte equality
    over values that are mostly nested objects of free text, and on these same
    runs it still gives 77-98% — but two records describing one collection
    method in different words are not two facts. Judged on whether the values
    state the same fact, it is 47-63%.

    The decision survives the correction because it never rested on the
    magnitude. Splicing mixes referents whether half the shared slots differ or
    nearly all of them, and the coverage it buys is 1-5 slots either way. What
    the old number did was make the case look stronger than the evidence for
    it, which is worth not repeating.

    The criterion is **validity first, coverage second**. Coverage alone is
    close to arbitrary here: margins across the generic-v2 config are +0, +1,
    +2 and +1 slots, and AI-READI is an outright tie. Validity is decisive —
    it breaks that tie, eliminates a higher-coverage CM4AI replicate, and shows
    that no VOICE replicate is shippable at all.

    Nothing is moved or copied. The winner's provenance gains a `canonical`
    block naming every candidate and the criterion, so the choice is auditable
    and reversible.
    """
    import yaml as _yaml
    from data_sheets_schema.runs import (
        CONCAT_DIR, INVALID, UNVERIFIED, VALID, is_complete, validation_status)
    from data_sheets_schema.provenance import ProvenanceRecord, record_path_for

    base_dir = CONCAT_DIR / method
    labels = sorted(p.name for p in base_dir.glob(f"{config}_rep*") if p.is_dir())
    if len(labels) < 2:
        raise click.ClickException(
            f"selection needs at least two replicates of {config!r}; "
            f"found {len(labels)}")

    candidates = []
    for label in labels:
        record = base_dir / label / f"{project}_d4d.yaml"
        if not record.exists():
            candidates.append((label, None, "no record", 0, "no record", "no record"))
            continue
        if not is_complete(method, label, project, CONCAT_DIR):
            candidates.append((label, record, "incomplete", 0, "incomplete", "incomplete"))
            continue
        loaded = _yaml.safe_load(record.read_text(encoding="utf-8"))
        slots = len(loaded) if isinstance(loaded, dict) else 0
        # Validate now, rather than reading the status recorded at generation
        # time. `compare()` reads the record because it runs over 100+ runs in
        # an analysis hot path; selection touches three and happens once, so it
        # can afford the truth. It matters: the schema has moved since these
        # runs, and CM4AI rep1 is recorded `invalid` but validates against the
        # current schema — the DataCite alignment admits a value that was
        # rejected when the run was made. Selecting on the stale claim would
        # have excluded a perfectly good record.
        ok, detail = _validates(record)
        live = VALID if ok else INVALID
        recorded = validation_status(method, label, project, CONCAT_DIR)
        candidates.append((label, record, live, slots, recorded, detail))

    accept = {VALID} | ({UNVERIFIED} if allow_unverified else set())
    eligible = [c for c in candidates if c[2] in accept]

    click.echo(f"{project} — {len(labels)} replicate(s) of {config}")
    for label, _record, status, slots, recorded, detail in candidates:
        mark = "  " if status in accept else "✗ "
        drift = (f"  (provenance says {recorded}; the schema has moved since "
                 f"this run)" if recorded != status and
                 recorded in (VALID, INVALID) else "")
        click.echo(f" {mark}{label:52s} {slots:3d} slots  {detail}{drift}")

    if not eligible:
        raise click.ClickException(
            f"no replicate of {project} is eligible. Nothing here can be "
            f"canonical, and picking the least-bad would ship a record known "
            f"to be broken. Fix the generator and rerun, or pass "
            f"--allow-unverified if the statuses are merely unrecorded.")

    # Coverage second, and the label as a deterministic tie-break so repeated
    # runs agree. Margins are thin enough that ties are ordinary, not freak.
    eligible.sort(key=lambda c: (-c[3], c[0]))
    winner = eligible[0]
    runner_up = eligible[1] if len(eligible) > 1 else None
    margin = winner[3] - runner_up[3] if runner_up else None

    click.echo(f"\n→ {winner[0]}  ({winner[3]} slots)")
    if margin == 0:
        click.echo("   Tied on coverage with the runner-up; the label broke the "
                   "tie. The choice between them is arbitrary on this "
                   "criterion.")
    elif margin is not None:
        click.echo(f"   {margin} slot(s) ahead of the runner-up — a thin margin "
                   f"on ~{winner[3]} slots, so read this as 'no reason to "
                   f"prefer another', not 'clearly best'.")

    if not execute:
        click.echo("\nDry run. Re-run with --execute to record the choice.")
        return

    prov_path = record_path_for(project, method, winner[0], CONCAT_DIR)
    if not prov_path.exists():
        raise click.ClickException(
            f"{winner[0]} has no provenance record at {prov_path}; a canonical "
            f"record must be attributable.")
    data = _yaml.safe_load(prov_path.read_text(encoding="utf-8")) or {}
    data["canonical"] = {
        "criterion": "full and core both validate against the current schema, then most slots, then lowest label",
        "selected_from": [
            {"label": lab, "slots": n, "validation": detail,
             "validation_recorded_at_run_time": rec}
            for lab, _r, st, n, rec, detail in candidates],
        "margin_over_runner_up": margin,
        "selected_by": "d4d runs select",
    }
    ProvenanceRecord(data=data).write(prov_path)
    click.echo(f"\nRecorded in {prov_path}")
    click.echo("All replicates kept — this marks one, it does not move or "
               "delete anything.")
