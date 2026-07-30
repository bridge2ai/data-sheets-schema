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
@click.option('--reason', default=None, help='Recorded in the archive README.')
@click.option('--execute', is_flag=True,
              help='Actually move. Without it, only report what would move.')
def archive(labels, unattested, reason, execute):
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
        # Drop labels whose projects disagree: archiving one would move
        # placeable records out alongside the unplaceable ones.
        mixed = {run.label for run in discover()
                 if not run.is_core and not run.deterministic
                 and run.label in targets
                 for proj in run.projects
                 if attestation(run.method, run.label, proj) != PARTIAL}
        for lab in sorted(mixed):
            click.echo(f"   ⏭  skipping {lab}: it also holds placeable records")
        targets -= mixed
    if not targets:
        click.echo("Nothing selected. Pass --label or --unattested."); return

    default_reason = (
        "These runs have a gap in something that determines their output — most "
        "often an input bundle whose consumed bytes cannot be verified, because "
        "the bundles were first committed after the runs executed. Runs whose "
        "provenance was merely reconstructed, but which pin their inputs, "
        "schema, model and outputs, are NOT archived: they can be placed and "
        "reproduced, and only their hardware is unrecorded.")
    res = archive_runs(sorted(targets), reason=reason or default_reason,
                       dry_run=not execute)
    verb = "Moved" if execute else "Would move"
    click.echo(f"{verb} {res['count']} run director(ies) for "
               f"{len(targets)} label(s) -> {res['archive']}")
    for src, dest in res["moved"]:
        click.echo(f"   {src}")
    if not execute:
        click.echo("\nDry run. Re-run with --execute to move them.")


@runs.command()
@click.option('--label', 'labels', multiple=True,
              help='Run label(s) to restore; default all archived.')
@click.option('--execute', is_flag=True)
def restore(labels, execute):
    """Move archived runs back into data/d4d_concatenated."""
    from data_sheets_schema.runs import restore_runs
    res = restore_runs(list(labels), dry_run=not execute)
    verb = "Restored" if execute else "Would restore"
    click.echo(f"{verb} {res['count']} run director(ies)")
    for src, dest in res["moved"]:
        click.echo(f"   {dest}")
    if not execute and res["count"]:
        click.echo("\nDry run. Re-run with --execute.")


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
