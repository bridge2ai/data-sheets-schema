"""Run-tracking commands for the D4D CLI."""

from datetime import datetime, timezone
from pathlib import Path

import click


@click.group()
def runs():
    """Track and compare parallel D4D generation runs."""
    pass


@runs.command("telemetry")
@click.option("--label-prefix", required=True,
              help="run label or prefix, e.g. 2026-08-05_claude-opus-5-1m-generic-v3")
@click.option("--method", default="claudecode_agent", show_default=True)
@click.option("-o", "--output", type=click.Path(), default=None,
              help="output path; defaults to data/run_telemetry/{label_prefix}.yaml")
@click.option("--findings", "findings_path", type=click.Path(exists=True),
              default=None,
              help="authored findings YAML (list of Finding objects) to merge")
@click.option("--validate", "do_validate", is_flag=True,
              help="linkml-validate the report against the telemetry schema")
def telemetry_cmd(label_prefix, method, output, findings_path, do_validate):
    """Collect per-phase process telemetry into a schema-backed report.

    Harvests provenance api_usage, the reasoning log, repair rounds,
    validation outcomes and what timing evidence exists (see the schema's
    timing_basis for how honest each figure is).
    """
    import subprocess
    import yaml as _yaml

    from data_sheets_schema.run_telemetry import (
        SCHEMA_PATH, collect_report, load_findings)

    findings = load_findings(Path(findings_path)) if findings_path else None
    report = collect_report(label_prefix, method=method, findings=findings)
    if not report["runs"]:
        raise click.ClickException(
            f"no runs with provenance found for prefix {label_prefix!r} "
            f"under method {method!r}")
    out = Path(output) if output else (
        Path("data/run_telemetry") / f"{label_prefix}.yaml")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_yaml.safe_dump(report, sort_keys=False,
                                   allow_unicode=True), encoding="utf-8")
    click.echo(f"✓ {len(report['runs'])} run(s) -> {out}")
    for r in report["runs"]:
        click.echo(f"   {r['project']:9} rep{r.get('replicate', '?')} "
                   f"{r['validation_state']:9} in={r['total_input_tokens']:,} "
                   f"out={r['total_output_tokens']:,} "
                   f"~${r['approx_cost_usd']:.2f} timing={r['timing_basis']}")
    if do_validate:
        res = subprocess.run(
            ["poetry", "run", "linkml-validate", "-s", str(SCHEMA_PATH),
             "-C", "RunTelemetryReport", str(out)],
            capture_output=True, text=True, timeout=180)
        if res.returncode != 0:
            raise click.ClickException(
                f"telemetry report failed schema validation:\n"
                f"{(res.stdout + res.stderr).strip()[:800]}")
        click.echo("✓ report validates against d4d_run_telemetry.yaml")


@runs.command("identifiers")
@click.option("--label", default=None, help="limit to one run label")
@click.option("--method", default=None, help="limit to one method directory")
@click.option("-o", "--output", type=click.Path(), default=None,
              help="write the full per-record report here as YAML")
@click.option("--show", default=8, type=int, show_default=True,
              help="list up to N offending values per affected record")
@click.option("--strict", is_flag=True,
              help="exit non-zero if any identifier cannot be resolved")
def identifiers_cmd(label, method, output, show, strict):
    """Audit identifier syntax across records — the trap the validator misses (#402).

    `trap-inventory` mines validation failures. This is its complement, and the
    defect it finds is the more dangerous kind because it passes: `uriorcurie`
    declares no pattern, so LinkML renders it `{"type": ["string","null"]}` and
    a bare token like `funder_nih` validates exactly as cleanly as a ROR IRI.

    Nothing is repaired here. Adding the pattern would invalidate values in
    records already committed — the right end state, and a migration rather
    than a flag flip. Naming what is out there comes first.
    """
    import sys
    import yaml as _yaml

    from data_sheets_schema import identifiers as ident
    from data_sheets_schema.runs import CONCAT_DIR

    root = CONCAT_DIR
    if method:
        root = root / method
    report = ident.audit(root=root)
    if label:
        # Recompute rather than filter in place: the headline must describe
        # exactly the records it is printed above. `slots_audited` describes
        # the schema, not the selection, so it is carried across rather than
        # recomputed — dropping it made the header claim only `id` was checked
        # while the by-slot line below it named others.
        audited = report.get("slots_audited")
        report = ident.summarize(
            [r for r in report["records"] if f"/{label}/" in r["path"]],
            report["prefixes_declared"], report.get("unreadable"))
        report["slots_audited"] = audited

    rows = [r for r in report["records"] if r["offenders"]]
    slots = report.get("slots_audited") or ["id"]
    click.echo(f"🔍 {len(report['records'])} record(s), "
               f"{report['identifiers']} identifier(s), "
               f"{report['prefixes_declared']} declared prefix(es)")
    click.echo(f"   slots with range uriorcurie: {', '.join(slots)}")
    c = report["counts"]
    click.echo(f"   {c[ident.URI]:>6}  absolute IRI")
    # Named separately, never folded into either neighbour (#530). Folded into
    # `uri` it would claim resolvability these do not have; left among the
    # undeclared CURIEs it inflated the unresolvable headline by 1,067 values
    # that need no remedy at all.
    click.echo(f"   {c[ident.URI_UNVERIFIED]:>6}  URI on a no-authority scheme "
               "(urn:, ark:, doi:) — well-formed, resolution not established")
    click.echo(f"   {c[ident.CURIE_DECLARED]:>6}  CURIE on a declared prefix")
    click.echo(f"   {c[ident.CURIE_UNDECLARED]:>6}  CURIE on an undeclared prefix")
    click.echo(f"   {c[ident.BARE]:>6}  bare token — neither IRI nor CURIE")

    if report["unresolvable"]:
        click.echo(f"\n⚠️  {report['unresolvable']} identifier(s) "
                   f"({report['unresolvable_share']:.0%}) across {len(rows)} "
                   "record(s) resolve to nothing:")
        by_slot = report.get("unresolvable_by_slot") or {}
        if by_slot:
            click.echo("   by slot: " + ", ".join(f"{s} {n}"
                                                  for s, n in by_slot.items()))
        for r in rows:
            name = Path(r["path"]).name
            click.echo(f"   {name}  ({len(r['offenders'])} of {r['total']}, "
                       f"mostly {r['dominant']})")
            for o in r["offenders"][:show]:
                click.echo(f"       {o['slot_path']:44} {o['value'][:48]}")
            if len(r["offenders"]) > show:
                # Never a silent cap: a truncated list that does not say it was
                # truncated reads as the whole finding.
                click.echo(f"       … {len(r['offenders']) - show} more "
                           "(raise --show, or use -o for the full report)")
    else:
        click.echo("\n✓ every identifier is an IRI or a CURIE on a declared prefix")

    if report.get("unreadable"):
        click.echo(f"\n·  {len(report['unreadable'])} record(s) could not be parsed")

    if output:
        out = Path(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_yaml.safe_dump(report, sort_keys=False,
                                       allow_unicode=True), encoding="utf-8")
        click.echo(f"\n✓ full report -> {out}")

    if strict and report["unresolvable"]:
        sys.exit(1)


@runs.command("trap-inventory")
@click.option("-o", "--output", type=click.Path(),
              default="data/run_telemetry/trap_slot_inventory.yaml",
              show_default=True)
@click.option("--validate", "do_validate", is_flag=True,
              help="linkml-validate the inventory against the telemetry schema")
def trap_inventory_cmd(output, do_validate):
    """Mine every generated record for validation-failure sites (#360).

    Runs the validator over the whole corpus (slow: one subprocess per
    record) and aggregates findings by normalized slot path and error class.
    """
    import subprocess
    import yaml as _yaml

    from data_sheets_schema.run_telemetry import SCHEMA_PATH, trap_inventory

    report = trap_inventory()
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_yaml.safe_dump(report, sort_keys=False,
                                   allow_unicode=True), encoding="utf-8")
    click.echo(f"✓ {report['records_scanned']} records scanned, "
               f"{report['records_with_errors']} with errors, "
               f"{len(report['traps'])} trap rows -> {out}")
    for t in report["traps"][:12]:
        click.echo(f"   {t['occurrence_count']:>4}x {t['error_class']:18} "
                   f"{t['slot_path']}")
    if do_validate:
        res = subprocess.run(
            ["poetry", "run", "linkml-validate", "-s", str(SCHEMA_PATH),
             "-C", "TrapSlotInventoryReport", str(out)],
            capture_output=True, text=True, timeout=180)
        if res.returncode != 0:
            raise click.ClickException(
                "inventory failed schema validation:\n"
                + (res.stdout + res.stderr).strip()[:800])
        click.echo("✓ inventory validates against d4d_run_telemetry.yaml")


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
    from data_sheets_schema.runs import AmbiguousCanonical, canonical_runs

    try:
        found = canonical_runs(config=config)
    except AmbiguousCanonical as exc:
        # Naming the configurations, because --config is the answer and the
        # user cannot pass it without knowing what to pass (#308).
        click.echo(f"{exc}", err=True)
        raise SystemExit(2)
    if project:
        found = {k: v for k, v in found.items() if k == project}

    if missing:
        gap = [p for p in PROJECTS if p not in found]
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
    from data_sheets_schema.runs import (canonical_prompt_status,
                                         check_provenance, discover,
                                         is_complete,
                                         prompt_condition_mismatch,
                                         requires_request,
                                         verify_request)

    rows = []
    mismatches = []
    requests = []
    uncanonical = []
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
            m = prompt_condition_mismatch(run.method, run.label, proj)
            if m:
                mismatches.append({"project": proj, "label": run.label,
                                   "reason": m})
            st, why = verify_request(run.method, run.label, proj)
            if st == "absent" and requires_request(run.label, run.method):
                # Silent before the cutoff, required after it. The gate is
                # otherwise opt-in by omission: an agentic launcher that simply
                # does not pass --prompt-text records nothing, and nothing says
                # so (#419).
                requests.append({"project": proj, "label": run.label,
                                 "status": "missing",
                                 "reason": ("no instruction recorded; render it "
                                            "with `d4d api render-prompt --out` "
                                            "and pass `--prompt-text`")})
            elif st in ("mismatch", "unverifiable"):
                requests.append({"project": proj, "label": run.label,
                                 "status": st, "reason": why})

            # The third comparison (#432). A prompt file edited before the
            # instruction was rendered re-renders to itself, so `verify_request`
            # says `match` and means it. Only the pin can tell that the file was
            # not a published version of its condition.
            cst, cwhy = canonical_prompt_status(run.method, run.label, proj)
            # `pre_registry` is reported like `superseded` and `unpinned`,
            # never failed: the bytes are attested by git at the run's own
            # commit (#399), which the registry could not have pinned because
            # it postdates the run. Failing it would make recovering honest
            # historical evidence worse than leaving the record blank.
            if cst in ("uncanonical", "missing", "unpinned",
                       "superseded", "pre_registry"):
                uncanonical.append({"project": proj, "label": run.label,
                                    "status": cst, "reason": cwhy})

    # Values recorded but not observed (#447). Every record has carried this
    # list since temperature got a basis, and no command read it — so the
    # honest gap-naming landed in a field nobody sees. Counted, never fatal:
    # the point of the list is that these values are usable *with* a caveat,
    # and a gate would collapse that back into a binary.
    import collections
    import yaml as _yaml
    from data_sheets_schema.provenance import record_path_for
    unobserved: collections.Counter = collections.Counter()
    for r in rows:
        p = record_path_for(r["project"], r["method"], r["label"])
        if not p.exists():
            continue
        data = _yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for entry in data.get("unverified") or []:
            unobserved[entry.get("field") or "unnamed"] += 1

    failed = [r for r in rows if not r["ok"]]
    required = [r for r in rows if r["required"]]
    for r in failed:
        click.echo(f"   ❌ {r['project']:9} {r['label']:44} {r['reason']}")
    click.echo(f"\n{len(rows)} run(s) checked, {len(required)} subject to the "
               f"requirement, {len(failed)} failing")
    if not failed:
        click.echo("All runs subject to the live-provenance requirement satisfy it.")

    if unobserved:
        click.echo(f"\nⓘ  {sum(unobserved.values())} value(s) across these runs "
                   "were recorded but not observed:")
        for field, n in unobserved.most_common():
            click.echo(f"     {field:28} {n}")

    # Bundle drift (#452). The mirror of `audit-bundles` one layer up: that asks
    # whether a derived bundle still matches what its inputs produce, this asks
    # whether a record's *declared input* still matches what the record
    # consumed. Reported, never fatal, for the same reason as the counter above
    # — a drifted record is still usable, it just cannot be re-derived from the
    # path it names, and a gate would collapse that distinction.
    from data_sheets_schema.runs import (
        BUNDLE_ABSENT, BUNDLE_CURRENT, BUNDLE_DRIFTED, BUNDLE_UNRECORDED,
        bundle_drift_detail,
    )
    drift: collections.Counter = collections.Counter()
    drifted_bundles: collections.Counter = collections.Counter()
    for r in rows:
        st, _why, declared = bundle_drift_detail(
            r["method"], r["label"], r["project"])
        drift[st] += 1
        if st in (BUNDLE_DRIFTED, BUNDLE_ABSENT):
            drifted_bundles[Path(declared).name if declared else "unknown"] += 1

    # Verdict schema pins (#433). `validation_status` leaves an unpinned
    # verdict alone, correctly — but that means VALID means two things
    # depending on when it was written, and `d4d runs validate` will not close
    # the gap because it skips a run already VALID. Counted so the gap is a
    # number someone can watch shrink rather than a property nobody can see.
    from data_sheets_schema.runs import (
        VERDICT_ABSENT, VERDICT_PINNED, VERDICT_UNPINNED, verdict_schema_pin,
    )
    pins: collections.Counter = collections.Counter()
    for r in rows:
        pins[verdict_schema_pin(r["method"], r["label"], r["project"])] += 1

    if pins[VERDICT_UNPINNED]:
        click.echo(f"\nⓘ  {pins[VERDICT_UNPINNED]} verdict(s) name no schema "
                   f"({pins[VERDICT_PINNED]} pinned, {pins[VERDICT_ABSENT]} "
                   "have no verdict at all).")
        click.echo("   An unpinned verdict is not wrong; it is unfalsifiable "
                   "by a schema change, so it cannot go STALE.")

    # Replicates generated against different schemas (#517). Every other check
    # here reads one record; this one only exists between records, which is
    # why the 2026-08-11 arm passed --strict with a schema change in the
    # middle of it. Reported for the whole corpus rather than the filtered
    # selection would be misleading, so it uses the same rows as everything
    # else: narrow the filter and you narrow what can be compared.
    from data_sheets_schema.runs import schema_straddle
    straddled = schema_straddle(rows)
    if straddled:
        click.echo(f"\n⚠️  {len(straddled)} replicate series generated against "
                   "more than one schema:")
        for series, by_digest in sorted(straddled.items()):
            click.echo(f"   {series}")
            for digest, labels in sorted(by_digest.items()):
                reps = ", ".join(l.rsplit("_", 1)[-1] for l in labels)
                click.echo(f"     {digest[:8]}  {reps}")
        click.echo("   Each record correctly names the schema it saw. Slot "
                   "counts across the split are not like-for-like.")

    # Playbook drift (#525). The same question as bundle drift, asked of the
    # declared *instructions* rather than the declared input — the playbook is
    # where the uniform decision rules live, so editing one changes the method
    # for every run that follows and left every earlier record attesting to
    # bytes that no longer exist. Reported, never fatal: playbooks are meant to
    # evolve, and a gate would make every improvement a corpus-wide failure.
    from data_sheets_schema.runs import (
        PLAYBOOK_ABSENT, PLAYBOOK_CURRENT, PLAYBOOK_DRIFTED,
        PLAYBOOK_UNRECORDED, playbook_drift,
    )
    books: collections.Counter = collections.Counter()
    book_detail: collections.Counter = collections.Counter()
    for r in rows:
        st, why = playbook_drift(r["method"], r["label"], r["project"])
        books[st] += 1
        if st in (PLAYBOOK_DRIFTED, PLAYBOOK_ABSENT) and why:
            book_detail[why] += 1

    moved = books[PLAYBOOK_DRIFTED] + books[PLAYBOOK_ABSENT]
    if moved:
        click.echo(f"\nⓘ  {moved} record(s) read a playbook whose bytes have "
                   f"since changed ({books[PLAYBOOK_CURRENT]} still match, "
                   f"{books[PLAYBOOK_UNRECORDED]} record no playbook hash):")
        for why, n in book_detail.most_common(6):
            click.echo(f"     {why[:66]:66} {n}")
        click.echo("   The decision rules live in these files, so a record "
                   "that names them cannot be re-derived from them.")

    # Full/core pair consistency (#544). Every other check here reads one
    # file; this reads two together, which is why `linkml-validate` and every
    # gate above passed a v4 arm in which 11 of 12 pairs disagreed. The API
    # path writes "Phase 4 reconciliation: completed" into every core header
    # and never ran the checker that would substantiate it; the agentic
    # playbook runs it, and scored 0 divergent pairs in 15.
    #
    # Reported, never fatal: each record is individually valid and usable, and
    # the whole corpus predates the check, so a gate would fail history.
    from data_sheets_schema.runs import (
        PAIR_CONSISTENT, PAIR_DIVERGENT, PAIR_NOT_RUN, PAIR_STALE,
        PAIR_UNRECORDED, pair_status,
    )
    pairs: collections.Counter = collections.Counter()
    divergent: list[tuple[str, str, int]] = []
    for r in rows:
        st, errs = pair_status(r["method"], r["label"], r["project"])
        pairs[st] += 1
        if st == PAIR_DIVERGENT:
            divergent.append((r["project"], r["label"], errs))

    # What each run said about its own phases (#562). The API path has always
    # written `api_usage`; the agentic path wrote nothing, so its phase
    # structure lived only in prose and no arm comparison could reach it.
    from data_sheets_schema.runs import (
        PHASES_ABSENT, PHASES_API, PHASES_RECORDED, phase_log_status,
    )
    logs: collections.Counter = collections.Counter()
    for r in rows:
        logs[phase_log_status(r["method"], r["label"], r["project"])[0]] += 1
    if logs[PHASES_ABSENT]:
        click.echo(f"\nⓘ  {logs[PHASES_ABSENT]} record(s) say nothing about "
                   f"which phases they ran ({logs[PHASES_API]} carry "
                   f"`api_usage`, {logs[PHASES_RECORDED]} a `phase_log`).")
        click.echo("   An arm comparison over a phase cannot include these.")

    # External identifiers checked against the bundle they were read from
    # (#547). The hardest fabrication class: right answer, no evidence. VOICE
    # rep1's RORs are all correct and none of them is in its bundle.
    from data_sheets_schema.runs import (
        GROUNDED_ALL, GROUNDED_GAPS, GROUNDED_NOT_RUN, GROUNDED_UNRECORDED,
        grounding_status,
    )
    grounds: collections.Counter = collections.Counter()
    ungrounded: list[tuple[str, str, int]] = []
    for r in rows:
        st, n = grounding_status(r["method"], r["label"], r["project"])
        grounds[st] += 1
        if st == GROUNDED_GAPS:
            ungrounded.append((r["project"], r["label"], n))

    if grounds[GROUNDED_GAPS]:
        click.echo(f"\nⓘ  {grounds[GROUNDED_GAPS]} record(s) carry an external "
                   f"identifier that is not in the bundle they read "
                   f"({grounds[GROUNDED_ALL]} fully grounded, "
                   f"{grounds[GROUNDED_NOT_RUN]} not checked, "
                   f"{grounds[GROUNDED_UNRECORDED]} predate the check):")
        for project, label, n in sorted(ungrounded)[:8]:
            click.echo(f"     {project:9} {label:44} {n} identifier(s)")
        if len(ungrounded) > 8:
            click.echo(f"     … and {len(ungrounded) - 8} more")
        click.echo("   These are generally correct values. Correct is not the "
                   "same as attested, and only the bundle can tell them apart.")
    elif grounds[GROUNDED_UNRECORDED]:
        click.echo(f"\nⓘ  {grounds[GROUNDED_UNRECORDED]} record(s) predate the "
                   "identifier-grounding check (#547).")

    # Reconciliation reports checked against the record and the schema (#546).
    # The report is what a reviewer reads instead of diffing YAML; nothing
    # checked it against either. In the v4 arm every record that emitted a
    # `distributions` block reported removing it, from the false premise that
    # the slot is not declared — and the blocks are still there.
    from data_sheets_schema.runs import (
        CLAIMS_CLEAN, CLAIMS_CONTRADICTED, CLAIMS_NOT_RUN, CLAIMS_STALE,
        CLAIMS_UNRECORDED, report_claim_status,
    )
    claims: collections.Counter = collections.Counter()
    contradicted: list[tuple[str, str, int]] = []
    for r in rows:
        st, n = report_claim_status(r["method"], r["label"], r["project"])
        claims[st] += 1
        if st == CLAIMS_CONTRADICTED:
            contradicted.append((r["project"], r["label"], n))

    if claims[CLAIMS_CONTRADICTED]:
        click.echo(f"\nⓘ  {claims[CLAIMS_CONTRADICTED]} reconciliation "
                   f"report(s) assert something the record or the schema "
                   f"contradicts ({claims[CLAIMS_CLEAN]} clean, "
                   f"{claims[CLAIMS_NOT_RUN]} not checked, "
                   f"{claims[CLAIMS_STALE]} stale, "
                   f"{claims[CLAIMS_UNRECORDED]} predate the check):")
        for project, label, n in sorted(contradicted)[:8]:
            click.echo(f"     {project:9} {label:44} {n} claim(s)")
        if len(contradicted) > 8:
            click.echo(f"     … and {len(contradicted) - 8} more")
        click.echo("   A report is the audit trail read instead of the diff. "
                   "These claims are decidable and were never decided.")
    elif claims[CLAIMS_UNRECORDED]:
        click.echo(f"\nⓘ  {claims[CLAIMS_UNRECORDED]} record(s) predate the "
                   "reconciliation-report check (#546).")

    if pairs[PAIR_STALE]:
        click.echo(f"\nⓘ  {pairs[PAIR_STALE]} pair verdict(s) describe bytes "
                   "that have since changed; the pair is unknown again.")

    if pairs[PAIR_DIVERGENT] or pairs[PAIR_NOT_RUN]:
        click.echo(f"\nⓘ  {pairs[PAIR_DIVERGENT]} record(s) wrote a full/core "
                   f"pair that disagrees ({pairs[PAIR_CONSISTENT]} agree, "
                   f"{pairs[PAIR_NOT_RUN]} could not be checked, "
                   f"{pairs[PAIR_UNRECORDED]} predate the check):")
        for project, label, errs in sorted(divergent)[:8]:
            click.echo(f"     {project:9} {label:44} {errs} error(s)")
        if len(divergent) > 8:
            click.echo(f"     … and {len(divergent) - 8} more")
        click.echo("   Both files validate alone. This is a property of the "
                   "two together, so no single-file gate can see it.")
    elif pairs[PAIR_UNRECORDED]:
        click.echo(f"\nⓘ  {pairs[PAIR_UNRECORDED]} record(s) predate the "
                   "full/core pair check (#544); their pairs are unknown, "
                   "not consistent.")

    stale = drift[BUNDLE_DRIFTED] + drift[BUNDLE_ABSENT]
    if stale:
        click.echo(f"\nⓘ  {stale} record(s) name an input bundle whose bytes "
                   f"have since changed ({drift[BUNDLE_CURRENT]} still match, "
                   f"{drift[BUNDLE_UNRECORDED]} record no hash):")
        for name, n in drifted_bundles.most_common():
            click.echo(f"     {name:44} {n}")
        click.echo("   Each record correctly states the bytes it consumed; the "
                   "path no longer resolves to them.")

    # Reported separately from the provenance verdict, and never fatal. A
    # label naming a condition its prompt does not match is a real defect
    # (#420) — but it is a defect in records that already exist, and failing
    # them retroactively would block every gate on history nobody can change.
    # Visible is the point: the 2026-08-07 sweep says `generic-v3` and hashes
    # v1, and nothing said so for three days.
    if mismatches:
        click.echo(f"\n⚠️  {len(mismatches)} run(s) whose label and hashed "
                   "prompt name different conditions (#420):")
        for m in mismatches:
            click.echo(f"   {m['project']:9} {m['label']:44} {m['reason']}")

    # The render gate. A mismatch means the instruction sent was not the one
    # the recorded spec produces — the intervention #419/#422 documented, now
    # detectable rather than merely discouraged. Fatal under --strict, because
    # unlike the label mismatch this is a claim about a run being made now:
    # every record carrying a request hash was written after the field existed.
    bad_requests = [r for r in requests
                    if r["status"] in ("mismatch", "missing")]
    if requests:
        click.echo(f"\n{len(requests)} run(s) whose recorded instruction could "
                   "not be confirmed against its spec:")
        for r in requests:
            mark = "❌" if r["status"] == "mismatch" else "⚠️ "
            click.echo(f"   {mark} {r['project']:9} {r['label']:44} "
                       f"{r['status']}: {r['reason']}")

    # Fatal for `uncanonical` — a run whose prompt was never a published
    # version of its condition — and for `missing`, a run that named a pinned
    # prompt file and hashed nothing for it. `superseded` is a condition that
    # has moved on since, `unpinned` is a file the registry does not cover;
    # both are worth seeing and neither is a defect in the run.
    never_pinned = [r for r in uncanonical
                    if r["status"] in ("uncanonical", "missing")]
    if uncanonical:
        click.echo(f"\n{len(uncanonical)} run(s) whose prompt files are not the "
                   "current canonical text of their condition (#432):")
        for r in uncanonical:
            mark = ("❌" if r["status"] in ("uncanonical", "missing")
                    else "⚠️ ")
            click.echo(f"   {mark} {r['project']:9} {r['label']:44} "
                       f"{r['status']}: {r['reason']}")

    if strict and (failed or bad_requests or never_pinned):
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
    # One canonical record per project, enforced by clearing rather than by
    # hoping. `select` used to leave a previous mark in place, so re-selecting
    # under a new config left the project with two and the resolver had to
    # refuse (#308). Superseding is what re-selection means.
    superseded = []
    for other in sorted(CONCAT_DIR.rglob(f"{project}_provenance.yaml")):
        if other == prov_path:
            continue
        try:
            prior = _yaml.safe_load(other.read_text(encoding="utf-8")) or {}
        except (_yaml.YAMLError, OSError, UnicodeDecodeError) as exc:
            # Fail the selection rather than skip. This command's contract is
            # one canonical record per project, and a file it cannot read is a
            # file whose mark it cannot clear. Skipping leaves the ambiguity to
            # surface later in `canonical_runs`, in a different command, with
            # nothing to connect it back to here (#310).
            raise click.ClickException(
                f"{other} could not be read "
                f"({type(exc).__name__}: {str(exc).splitlines()[0][:80]}), so a "
                "prior canonical mark there could not be cleared. Fix or remove "
                "that record before selecting, or the project would end up with "
                "two.")
        if not isinstance(prior, dict):
            raise click.ClickException(
                f"{other} is not a mapping, so a prior canonical mark there "
                "could not be cleared.")
        if "canonical" not in prior:
            continue
        superseded.append(((prior.get("run") or {}).get("label") or str(other),
                           other, prior))

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
    # Named, not merely removed. A mark that vanishes leaves no trace of what
    # the project used to ship, and "this replaced that" is the fact a reader
    # of either record wants.
    if superseded:
        data["canonical"]["supersedes"] = [lab for lab, _p, _d in superseded]
    ProvenanceRecord(data=data).write(prov_path)

    for label, other, prior in superseded:
        prior.pop("canonical", None)
        prior["canonical_superseded_by"] = {
            "label": winner[0],
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "by": "d4d runs select",
        }
        ProvenanceRecord(data=prior).write(other)
        click.echo(f"   cleared the prior mark on {label}")

    click.echo(f"\nRecorded in {prov_path}")
    if superseded:
        click.echo(f"Superseded {len(superseded)} earlier mark(s); each records "
                   "what replaced it.")
    click.echo("All replicates kept — this marks one, it does not move or "
               "delete anything.")


@runs.command("redundancy")
@click.option("--method", default="claudecode_agent", show_default=True)
@click.option("--label", default=None,
              help="one run label; default is each project's canonical record")
@click.option("--project", default=None)
@click.option("--threshold", default=None, type=float,
              help="content-word overlap above which two sentences are the "
                   "same statement (default 0.6)")
@click.option("--show", default=3, type=int, show_default=True,
              help="example restatements to print per project")
def redundancy_cmd(method, label, project, threshold, show):
    """How often one fact is stated in more than one slot (#501).

    Reported, never fatal. The repetition is **intended**: the decision on #501
    was that a reader who opens one slot must get an answer there rather than a
    pointer elsewhere, so per-slot completeness wins and the document reads
    repetitively as the price.

    This exists so the rate can be watched. It sat at 7.4% of sentences across
    the canonical set when that was decided; a later arm at 30% would mean
    something changed that nobody chose.
    """
    from pathlib import Path as _Path

    from data_sheets_schema import redundancy as red
    from data_sheets_schema.constants import PROJECTS
    from data_sheets_schema.runs import CONCAT_DIR, canonical_runs

    kwargs = {} if threshold is None else {"threshold": threshold}
    if label:
        targets = {p: label for p in ([project] if project else PROJECTS)}
    else:
        targets = {p: info["label"] for p, info in canonical_runs().items()
                   if not project or p == project}
        if not targets:
            raise click.ClickException(
                "no canonical records; pass --label, or run "
                "`d4d runs select --execute`")

    total_sentences = total_prose = total_structural = 0
    rows = []
    for proj, lab in sorted(targets.items()):
        path = _Path(CONCAT_DIR) / method / lab / f"{proj}_d4d.yaml"
        if not path.exists():
            continue
        summary = red.summarize(red.load(path), **kwargs)
        rows.append((proj, lab, summary))
        total_sentences += summary["sentences"]
        total_prose += summary["prose_restatements"]
        total_structural += summary["structural_restatements"]

    if not rows:
        raise click.ClickException("no records found for that selection")

    click.echo(f"{'project':17}{'sentences':>10}{'restated':>10}{'rate':>8}"
               f"{'structural':>12}")
    for proj, _lab, s in rows:
        click.echo(f"{proj:17}{s['sentences']:>10}{s['prose_restatements']:>10}"
                   f"{s['rate']:>7.1%}{s['structural_restatements']:>12}")
    rate = (total_prose / total_sentences) if total_sentences else 0.0
    used = red.THRESHOLD if threshold is None else threshold
    # The threshold is printed with the rate because the rate is meaningless
    # without it: on the canonical set the same corpus reads 2.1% at exact
    # match and 12.0% at 0.5. A figure quoted bare invites comparison against
    # a future figure computed differently.
    click.echo(f"\n{total_prose} prose restatement(s) across {total_sentences} "
               f"sentences — {rate:.1%} at threshold {used}")
    # Named separately rather than folded in: a URL beside its format, or a
    # nested sub-resource repeating its parent's title, is correct. Including
    # it would overstate the figure by about a third.
    click.echo(f"{total_structural} further pair(s) are structural (a URL or a "
               "nested resource) and are not redundancy.")

    for proj, _lab, s in rows:
        if not s["restatements"]:
            continue
        click.echo(f"\n{proj} — {len(s['slots_involved'])} slots involved:")
        for r in sorted(s["restatements"],
                        key=lambda x: -x.similarity)[:show]:
            click.echo(f"   {r.similarity:.2f}  {r.slot_a} | {r.slot_b}")
            click.echo(f"          {r.text_a[:96]}")
            click.echo(f"          {r.text_b[:96]}")
        if len(s["restatements"]) > show:
            click.echo(f"   … {len(s['restatements']) - show} more "
                       "(raise --show)")

    click.echo("\nThis is reported, not failed: per-slot completeness is the "
               "decision on #501, and the repetition is its accepted cost.")
