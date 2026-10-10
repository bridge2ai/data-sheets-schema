"""Evaluate command group for D4D CLI.

Commands for evaluating D4D datasheet quality.
"""

import click

from data_sheets_schema.registry import project_choice
import sys
from pathlib import Path
from data_sheets_schema.constants import METHODS, RUBRIC_TYPES
from data_sheets_schema.runs import RUNTIME_CHOICES

@click.group()
def evaluate():
    """D4D evaluation commands."""
    pass

@evaluate.command("verifiable")
@click.option("--project", default=None, help="limit to one project")
@click.option("--method", default=None, help="run directory family; defaults to the one the label lives in (claudecode_agent or claudecode_api, #934)")
@click.option("--label", "labels", multiple=True, help="run label(s); default all")
@click.option("--show", default=0, type=int,
              help="list up to N ungrounded values per record")
@click.option("--json", "as_json", is_flag=True, help="include captured schema/source identities and unchecked records as JSON")
def verifiable_cmd(project, method, labels, show, as_json=False):
    """Check the values a record states against the documents it declared.

    Answers the half of #165 that survives having no gold standard: a DOI, a
    date, a count and an accession must appear literally in a source document,
    because that is where they came from. No reference record is needed, and no
    LLM.

    `stated` is printed beside `grounded` on purpose. A record that states
    nothing is trivially correct on everything it states, so the ratio alone
    would rank an empty record top. Each run uses its recorded schema when
    recoverable and its exact pinned source bytes. Missing schema identities
    and unpinned legacy sources are disclosed; unusable pinned inputs are
    unchecked and make the command fail. No historical files are rewritten.
    """
    from data_sheets_schema.cli.method import resolve_method
    # Each named label is read from its own directory (#973): v7 and v8
    # labels together evaluate both, not one. An explicit --method that a
    # named label is not under is an error, not a silent omission. With no
    # label, the pre-v8 default holds.
    by_label = {lab: resolve_method(lab, project) for lab in labels}
    if method is not None:
        outside = sorted(lab for lab, m in by_label.items() if m != method)
        if outside:
            raise click.ClickException(f"not under {method}: {', '.join(outside)}")
        methods = {method}
    else:
        methods = set(by_label.values()) or {"claudecode_agent"}
    from data_sheets_schema.runs import discover, record_path
    from data_sheets_schema.provenance import record_path_for
    from data_sheets_schema.corpus import anchored
    from data_sheets_schema.verifiable import check_run

    wanted = set(labels)
    rows = []
    for run in discover():
        # Skip core/deterministic runs only when the caller did not name one.
        # Filtering them unconditionally made `--method claudecode_agent_core`
        # report "No records matched" for records that plainly exist.
        if run.method not in methods:
            continue
        if (run.is_core or run.deterministic) and run.method == "claudecode_agent":
            continue
        if wanted and run.label not in wanted:
            continue
        for proj in run.projects:
            if project and proj != project:
                continue
            rec = record_path(run.method, run.label, proj)
            if rec is None:
                # Retain a selected record that disappeared after discovery as
                # unmeasured; absence cannot turn a partial cohort into success.
                filename = f"{proj}_d4d_core.yaml" if run.is_core else f"{proj}_d4d.yaml"
                rec = anchored(Path("data/d4d_concatenated") / run.method / run.label / filename)
            r = check_run(rec, record_path_for(proj, run.method, run.label),
                          kind="core" if run.is_core else "full",
                          fallback_bundle=anchored(Path("data/preprocessed/concatenated") / f"{proj}_preprocessed.txt"),
                          project=proj, label=run.label)
            rows.append(r)

    rows.sort(key=lambda row: (row["project"], row["label"]))
    failed = any(not row["checked"] for row in rows)
    if as_json:
        import json
        click.echo(json.dumps({"instrument": "verifiable-recorded-basis-v1", "records": rows}, indent=2))
        if failed:
            raise SystemExit(1)
        return
    if not rows:
        click.echo("No records matched."); return

    click.echo(f"{'project':10}{'label':38}{'stated':>7}{'grounded':>9}{'rate':>7}")
    for r in rows:
        if not r["checked"]:
            click.echo(f"{r['project']:10}{r['label']:38} UNCHECKED: {r['reason']}")
            continue
        rate = f"{r['rate']:.1%}" if r["rate"] is not None else "  n/a"
        click.echo(f"{r['project']:10}{r['label']:38}{r['stated']:>7}{r['grounded']:>9}{rate:>7}")
        for name in ("schema", "source"):
            basis = r[f"{name}_basis"]
            why = f"; {basis['reason']}" if basis.get("reason") else ""
            kind = f"/{basis['kind']}" if name == "schema" else ""
            click.echo(f"    {name}{kind}: {basis['status']}; sha256={basis['actual_sha256']}; "
                       f"{basis['source']}{why}")
        for c in [c for c in r["claims"] if c["grounded"] is False][:show]:
            click.echo(f"    [{c['kind']}] {c['slot']}: {c['value'][:70]}")

    measured = [row for row in rows if row["checked"]]
    total_stated = sum(r["stated"] for r in measured)
    total_ok = sum(r["grounded"] for r in measured)
    click.echo(f"\n{total_ok}/{total_stated} values grounded across "
               f"{len(measured)} measured record(s); {len(rows) - len(measured)} unchecked.")
    click.echo("These are token-location counts, not semantic accuracy. Schema and source "
               "bases are shown per record; totals can combine different bases. "
               "Unpinned legacy sources do not establish what a historical run read.")
    if failed:
        raise SystemExit(1)


@evaluate.command()
@click.option('--file', type=click.Path(exists=True, dir_okay=False),
              help='Evaluate an explicit D4D file with declared identities')
@click.option('--context', type=click.Path(exists=True, dir_okay=False),
              help='YAML/JSON applicability predicates and their evidence')
@click.option('--project',
              help='Evaluate specific project only (default: all)')
@click.option('--method', default=None,
              help='Method to evaluate')
@click.option('--output-dir', type=click.Path(), default='data/evaluation',
              help='Output directory for evaluation reports')
def presence(file, context, project, method, output_dir):
    """Run presence-based evaluation (field existence check)."""
    if file:
        if not project or not method:
            raise click.ClickException("--file requires --project and --method")

    if project:
        click.echo(f"📊 Evaluating {project} ({method}) - presence-based...")
    else:
        click.echo(f"📊 Evaluating all projects ({method}) - presence-based...")

    from data_sheets_schema.evaluation.evaluate_d4d import main as eval_main

    # Set up args for the evaluation script
    old_argv = sys.argv
    sys.argv = ['evaluate_d4d.py']
    if method:
        sys.argv.extend(['--methods', method])
    sys.argv.extend(['--output-dir', output_dir])
    if project:
        sys.argv.extend(['--project', project])
    if file:
        sys.argv.extend(['--file', file])
    if context:
        sys.argv.extend(['--context', context])

    try:
        eval_main()
        click.echo(f"✓ Evaluation complete. Reports saved to {output_dir}")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        sys.argv = old_argv

@evaluate.command()
@click.option('--file', type=click.Path(exists=True), required=True,
              help='D4D YAML file to evaluate')
@click.option('--project', required=True,
              help='Project name')
@click.option('--method', required=True,
              help='Generation method')
@click.option('--rubric', type=click.Choice(RUBRIC_TYPES + ['both']),
              default='both',
              help='Which rubric to use')
@click.option('--output-dir', type=click.Path(), default='data/evaluation_llm',
              help='Output directory for LLM evaluation reports')
@click.option('--context', type=click.Path(exists=True, dir_okay=False),
              help='YAML/JSON applicability predicates and their evidence')
def llm(file, project, method, rubric, output_dir, context):
    """Run LLM-based quality evaluation (requires ANTHROPIC_API_KEY)."""

    click.echo(f"🤖 LLM evaluating {file} with {rubric}...")
    click.echo("⚠️  Note: Requires ANTHROPIC_API_KEY environment variable")

    try:
        from data_sheets_schema.evaluation.evaluate_d4d_llm import main as llm_eval_main
    except ImportError:
        click.echo("❌ Error: LLM evaluation script not found", err=True)
        click.echo("   Expected: data_sheets_schema.evaluation.evaluate_d4d_llm", err=True)
        sys.exit(1)

    # Set up args for the LLM evaluation script
    old_argv = sys.argv
    sys.argv = ['evaluate_d4d_llm.py',
                '--file', file,
                '--project', project,
                '--method', method,
                '--rubric', rubric,
                '--output-dir', output_dir]
    if context:
        sys.argv.extend(['--context', context])

    try:
        llm_eval_main()
        click.echo(f"✓ LLM evaluation complete. Reports saved to {output_dir}")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        sys.argv = old_argv


@evaluate.command("plan")
@click.option("--config", default=None,
              help="Restrict to one run config (label prefix).")
@click.option("--paths-only", is_flag=True,
              help="One record path per line, for piping into a sweep.")
@click.option("--runtime", type=click.Choice(list(RUNTIME_CHOICES)), default=None,
              help="which runtime's canonical set (#690); required where a project is marked under more than one")
@click.option("--all-replicates", is_flag=True,
              help="Every replicate of the canonical config, not one record "
                   "per project (#287). Buys a within-config variance estimate "
                   "at ~3x the cost; does not rescue between-config power.")
def plan_cmd(config, paths_only, all_replicates, runtime):
    """What a semantic evaluation sweep would cover, derived from the canonical set.

    The count has been stated four times and been wrong three of them (#315),
    because it depends on how many projects end up with a canonical record —
    which is not known until `d4d runs select --execute` has run. This derives
    it rather than restating it, and prints the derivation alongside the number
    so a bare count is harder to quote onward.
    """
    from data_sheets_schema.evaluation_plan import (NothingSelected, plan,
                                                    summarise)
    from data_sheets_schema.runs import AmbiguousCanonical
    try:
        evaluations = plan(config=config, runtime=runtime,
                           all_replicates=all_replicates)
    except NothingSelected as exc:
        raise click.ClickException(str(exc))
    except AmbiguousCanonical as exc:
        # The state the rerun creates: marks under both the old and the new
        # config until re-selection settles — or, since #690, under both
        # runtimes. `plan` is right to propagate rather than choose one
        # (#308); rendering it is this boundary's job (#342).
        head = str(exc).split(". Pass config=", 1)[0]
        raise click.ClickException(
            f"{head}. Pass --config to say which configuration you mean, "
            "--runtime api|agentic to say which arm's canonical set, or "
            "re-run `d4d runs select --execute` to settle the mark.")

    if paths_only:
        for path in dict.fromkeys(str(e.path) for e in evaluations):
            click.echo(path)
        # Preserve a clean path stream while making reduced cohort coverage
        # visible to a caller piping it into a sweep (#1364).
        from data_sheets_schema.evaluation_plan import LAST_EXCLUDED
        if LAST_EXCLUDED:
            click.echo(summarise(evaluations), err=True)
        return

    for evaluation in evaluations:
        click.echo(f"{evaluation.name}\t{evaluation.path}")
    click.echo("")
    click.echo(summarise(evaluations))


@evaluate.command("related-datasets")
@click.option("--runtime", type=click.Choice(list(RUNTIME_CHOICES)), default=None,
              help="which runtime's canonical set (#690), where no records are given")
@click.argument("records", nargs=-1, type=click.Path(exists=True))
@click.option("--project", default=None,
              help="Limit to one project when reading the canonical set.")
@click.option("--schema-policy", type=click.Choice(["legacy_current", "recorded"]),
              default="legacy_current", show_default=True,
              help="Recorded mode binds each artifact to its full/core historical schema.")
@click.option("--provenance", type=click.Path(), default=None,
              help="Recorded mode: explicit provenance for one explicit artifact.")
@click.option("--kind", type=click.Choice(["full", "core"]), default=None,
              help="Recorded mode: explicit artifact kind, paired with --provenance.")
@click.option("--json", "as_json", is_flag=True,
              help="Recorded mode: emit versioned per-artifact results and coverage.")
def related_datasets_cmd(records, project, runtime, schema_policy="legacy_current",
                         provenance=None, kind=None, as_json=False):
    """Classify `related_datasets` defects by mode (#292).

    All three VOICE replicates fail this slot, each differently, and
    `linkml-validate` reports them as three unrelated errors. The rerun's answer
    differs per mode: an aliased type recurring means the write-path normaliser
    did not run, an unknown type means the model reached for a word the DataCite
    vocabulary lacks, and an inline target under generic-v4 means that rule did
    not work.

    With no arguments, reads the canonical set.
    """
    if schema_policy == "recorded":
        return _related_recorded_cli(records, project, runtime, provenance, kind, as_json)
    if provenance is not None or kind is not None or as_json:
        raise click.UsageError("--provenance, --kind and --json require --schema-policy recorded")
    import yaml

    from data_sheets_schema.related_datasets import inspect, summarise

    paths = [Path(r) for r in records]
    if not paths:
        from data_sheets_schema.evaluation_plan import NothingSelected, VARIANTS
        from data_sheets_schema.runs import AmbiguousCanonical, canonical_runs
        try:
            # Diagnostics must inspect stale and invalid marks too (#1365).
            # Workload planning filters those before a paid evaluation.
            canonical = canonical_runs(runtime=runtime)
            if not canonical:
                raise NothingSelected(None)
            paths = list(dict.fromkeys(Path(record[variant])
                for name, record in canonical.items() if project in (None, name)
                for variant in VARIANTS if record.get(variant)))
        except (NothingSelected, AmbiguousCanonical) as exc:
            raise click.ClickException(str(exc))
        if not paths:
            raise click.ClickException(f"no canonical records matched project {project!r}")

    total = 0
    for path in paths:
        record = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        defects = inspect(record)
        total += len(defects)
        if defects:
            click.echo(f"{path}")
            for defect in defects:
                click.echo(f"  [{defect.index}] {defect.mode}: {defect.detail}")
    click.echo("")
    click.echo(f"{total} defect(s) across {len(paths)} record(s)")
    if total:
        raise SystemExit(1)


def _related_recorded_cli(records, project, runtime, provenance, kind, as_json):
    import json
    from data_sheets_schema.related_dataset_diagnostics import INSTRUMENT, check_record
    from data_sheets_schema.evaluation_plan import NothingSelected, VARIANTS
    from data_sheets_schema.runs import AmbiguousCanonical, canonical_runs

    if records:
        if len(records) != 1 or provenance is None or kind is None:
            raise click.UsageError("recorded explicit input requires one artifact and both --provenance and --kind")
        selected = [(Path(records[0]), Path(provenance), kind)]
    else:
        if provenance is not None or kind is not None:
            raise click.UsageError("--provenance and --kind require an explicit artifact")
        try:
            canonical = canonical_runs(runtime=runtime)
            if not canonical:
                raise NothingSelected(None)
        except (NothingSelected, AmbiguousCanonical) as exc:
            raise click.ClickException(str(exc))
        selected, seen = [], {}
        for name, record in canonical.items():
            if project not in (None, name):
                continue
            for variant in VARIANTS:
                if not record.get(variant):
                    continue
                if not record.get('provenance'):
                    raise click.ClickException(f"canonical artifact lacks provenance association: {record[variant]}")
                path, prov = Path(record[variant]), Path(record['provenance'])
                identity, association = path.resolve(), (prov.resolve(), variant)
                if identity in seen:
                    if seen[identity] != association:
                        raise click.ClickException(f"ambiguous canonical artifact association: {path}")
                    continue
                seen[identity] = association
                selected.append((path, prov, variant))
        if not selected:
            raise click.ClickException(f"no canonical records matched project {project!r}")

    results = [check_record(path, prov, kind=variant) for path, prov, variant in selected]
    unavailable = sum(not r['checked'] for r in results)
    total = sum(len(r['defects']) for r in results if r['checked'])
    output = {'instrument': INSTRUMENT, 'requested_policy': 'recorded', 'records': results,
              'coverage': {'selected': len(results), 'checked': len(results) - unavailable,
                           'unavailable': unavailable, 'defects': total}}
    if as_json:
        click.echo(json.dumps(output, sort_keys=True))
    else:
        for result in results:
            click.echo(f"{result['path']} [{result['kind']}] policy=recorded instrument={INSTRUMENT}")
            if not result['checked']:
                click.echo(f"  unavailable: {result['reason']}")
                continue
            schema = result['selected_schema']
            click.echo(f"  schema={schema['sha256']} root={schema['root']} owner={schema['owner']} "
                       f"enum={schema['enum']} basis={result['schema_basis']['source']}")
            click.echo(f"  output={result['output_association']['historical_output']}: "
                       f"{result['output_association']['meaning']}")
            for defect in result['defects']:
                click.echo(f"  [{defect['index']}] {defect['mode']}: {defect['detail']}")
        click.echo(f"{total} defect(s) across {len(results) - unavailable} checked record(s); "
                   f"{unavailable} unavailable of {len(results)} selected")
    if unavailable:
        raise SystemExit(2)
    if total:
        raise SystemExit(1)


@evaluate.command("slot-meaning")
# No existence, readability or directory check at the argument (#3144): click
# would reject the whole call with a usage error, and the records named beside
# the bad path would go unreported. The loop reports such a path as not checked.
@click.argument("records", nargs=-1, required=True, type=click.Path(readable=False))
@click.option("--json", "as_json", is_flag=True, help="print one JSON document instead of text")
def slot_meaning_cmd(records, as_json):
    """Embargo, release-timing and availability text under
    `confidential_elements` or `sensitive_elements` (#2931).

    A temporary pre-publication embargo is a statement about when data are
    released, not that they are confidential; recorded under
    `confidential_elements` it asserts confidential elements on the strength
    of a release date. Only these two slots are read: the same text is
    correct in `known_limitations`, `distribution_dates` and the access
    slots. Access-control language ("withheld from the public release",
    "controlled access") is not matched.

    Read-only and non-gating: exits 0 whatever it finds, and 1 only when a
    named record was not checked (2 is a usage error, such as naming no
    record). A record is not checked when it cannot be read (the path does
    not exist, is a directory or is not readable; the file is not UTF-8; or
    the YAML loader raises on it: a syntax error, or anything else, such as
    an impossible unquoted date), is not a mapping, or repeats a key one of whose
    dropped earlier values held something the scan reads (#1029): a scoped
    slot, a key inside one that the scan reads (any but `id`, `source_caveats`
    and what they hold), or an ancestor such as a second `resources` block
    holding one. A mapping is judged wherever the scan reaches it, through an
    alias or a merge key as well as where it is written, and a merged value
    that an explicit key or an earlier merge overrides is never read, so a
    key repeated inside it is no reason (#3203), nor is it looked into for a
    scoped slot a dropped ancestor holds (#3247). A duplicated
    ancestor whose dropped copies hold no scoped slot hides nothing from this
    scan and does not stop the record being checked. A record is not checked
    either when its walk runs past a fixed step budget: aliases can load a
    small text as a graph with exponentially many paths (#3247); a merge
    chain costs about a few steps a link, since each mapping's merges are
    laid out once (#3496), but where each link also adds a key the pairs
    grow quadratically and one of 628 links or more is not checked (#3504);
    when the paths its scan builds pass a fixed character
    budget, as a deep record under long keys does (#3582);
    when its merge keys would copy more pairs in the loader than the same
    bound (#3259); or when a merge key reaches the mapping it is written in
    (#3263). A record that is not checked has none of its findings reported, not even those its kept
    values carry. A record the diagnostic never looked at is not a clean one,
    and the other records named in the same call are still reported. Nothing
    is written.
    """
    import json

    from data_sheets_schema import routing_diagnostics as rd

    results = []
    for record_path in records:
        try:
            text = Path(record_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            results.append((record_path, None, (str(exc).splitlines() or [type(exc).__name__])[0]))
            continue
        found, reason = rd.check_text(text)
        results.append((record_path, found, reason))

    checked = [found for _, found, _ in results if found is not None]
    unchecked = len(results) - len(checked)
    if as_json:
        click.echo(json.dumps({
            "instrument": rd.INSTRUMENT, "lexicon_sha256": rd.LEXICON_SHA256,
            "gating": False, "slots": list(rd.SCOPED_SLOTS),
            "records": [{"path": path, "checked": False, "reason": reason} if found is None else
                        {"path": path, "checked": True, "count": len(found),
                         "mismatches": [rd.as_dict(m) for m in found]}
                        for path, found, reason in results],
        }, indent=2))
    else:
        for path, found, reason in results:
            if found is None:
                click.echo(f"{path}\n  not checked: {reason}")
            elif found:
                click.echo(path)
                for mismatch in found:
                    click.echo(f"  {rd.describe(mismatch)}")
        total = [m for found in checked for m in found]
        click.echo("")
        click.echo(f"{len(total)} slot-meaning mismatch(es) in {sum(1 for f in checked if f)} of "
                   f"{len(checked)} record(s) checked, {sum(1 for m in total if m.present is True)} "
                   f"in an entry asserting its elements present; not gating ({rd.INSTRUMENT})")
    if unchecked:
        raise click.ClickException(f"{unchecked} record(s) could not be checked")



@evaluate.command("spelling")
@click.option('--method', default=None, help="run directory family; defaults to the one the label lives in (claudecode_agent or claudecode_api, #934)")
@click.option('--label', default=None, help='restrict to one run label')
@click.option('--project', default=None)
@click.option('--show-quoted', is_flag=True,
              help='also list occurrences that appear verbatim in the bundle')
def spelling_cmd(method, label, project, show_quoted):
    """British spellings in generated prose, excluding quoted source text (#502).

    A find-and-replace would be wrong: the bundles themselves contain `licence`
    13 times and `programme` 6, so rewriting every occurrence would silently
    alter what a source said. An occurrence is treated as quoted when a window
    of surrounding text appears verbatim in the run's declared bundle.

    Conservative in the direction of silence. A false "quoted" merely fails to
    report; a false "generated" would invite someone to edit evidence.
    """
    from data_sheets_schema.cli.method import resolve_method
    method = method or (resolve_method(label, project) if label else 'claudecode_agent')
    if label and not (Path(f"data/d4d_concatenated/{method}_core") / label).is_dir():
        # The resolver accepts a prefix; the filter below compares labels
        # exactly, and a prefix printed a clean zero (#973).
        raise click.ClickException(f"{label!r} is not an exact label under {method}_core; name the replicate")
    from pathlib import Path as _Path

    import yaml as _yaml

    from data_sheets_schema.runs import discover, record_path
    from data_sheets_schema.spelling import in_identifiers, occurrences
    from data_sheets_schema.verifiable import declared_bundle

    generated = quoted = 0
    ident: list = []
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
            path = record_path(run.method, run.label, proj)
            if not path.exists():
                continue
            try:
                data = _yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception:                                # noqa: BLE001
                continue
            bundle = declared_bundle(run.method, run.label, proj)
            text = (_Path(bundle).read_text(errors="ignore")
                    if bundle and _Path(bundle).exists() else None)
            occ = occurrences(data, text)
            here = [o for o in occ if not o.quoted]
            quoted += len(occ) - len(here)
            if here:
                click.echo(f"\n{proj}  {run.label}"
                           + ("" if text else "   ⚠️  bundle not identified, so "
                              "nothing could be shown to be quoted"))
                for o in here:
                    click.echo(f"   {o.slot:26} {o.word:14} -> {o.suggestion}")
                    click.echo(f"      …{o.context[:100]}…")
                generated += len(here)
            ident.extend((proj, run.label, o) for o in in_identifiers(data))

    click.echo(f"\n{generated} occurrence(s) in generated prose, "
               f"{quoted} in text quoted from a bundle (left alone).")
    if ident:
        click.echo(f"\n⚠️  {len(ident)} inside an `id`, which is structural "
                   "rather than stylistic — an identifier other records may "
                   "key on cannot be fixed by a later copy-edit:")
        for proj, lab, o in ident:
            click.echo(f"   {proj:16} {o.context}")


@evaluate.command("q19-lint")
@click.argument("paths", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option("--inspection", "inspections", multiple=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="A recorded Q19 inspection (semantic_errata.md or semantic_review.md, read "
                   "with the JSON companion beside it where there is one): lint the evaluations "
                   "it names and report agreement with it. Refused where an evaluation is "
                   "missing, has no recorded hash, or is not the bytes or the Q19 score the "
                   "inspection recorded.")
@click.option("--show", is_flag=True,
              help="Print the text each reason was read from (a sentence, a label's reason "
                   "clauses, or the part of a sentence that names a gap).")
@click.option("--strict", is_flag=True, help="Exit 1 if any rating is flagged.")
def q19_lint_cmd(paths, inspections, show, strict):
    """Flag rubric20 Q19 scores held below 5 for how provenance is represented (#2911).

    PATHS are rubric20 semantic evaluation files, or directories searched for
    *_evaluation.json. A rating is flagged when what says why Q19 is below
    5 gives a representation or empty-slot reason (an empty
    was_derived_from, no PROV graph, not machine-traversable, scattered
    across fields). Where nothing says why, the score label's reason
    clauses and the parts of the rationale's sentences that name a gap are
    read instead; a part naming no gap is not read. A clause that accepts
    a form, concedes, or disclaims a deduction names no reason.
    Substantive reasons given beside a representation reason are listed. A
    rating with only substantive reasons, or with no reason the lint can
    determine, is reported and never shown as a pass. Evaluation files are
    read, never written.
    """
    from data_sheets_schema.q19_rationale_lint import lint_report
    try:
        lines, flagged = lint_report(paths, inspections, show=show)
    except ValueError as exc:
        raise click.ClickException(str(exc))
    for line in lines:
        click.echo(line)
    if strict and flagged:
        raise SystemExit(1)


@evaluate.command("validate")
@click.argument("files", nargs=-1, required=True,
                type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--rubric", type=click.Choice(["rubric10-semantic", "rubric20-semantic"]),
              help="Require this semantic rubric for every named output.")
@click.option("--input", "input_path", required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Original D4D used in the assessment.")
@click.option("--agent-definition", required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Exact evaluator definition used for the assessment.")
@click.option("--context", "context_path",
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Trusted applicability declarations; omitted predicates remain unknown.")
def validate_cmd(files, rubric, input_path, agent_definition, context_path):
    """Validate named semantic outputs against their input and instrument."""
    from data_sheets_schema.evaluation.validate import validate_outputs
    if validate_outputs(list(files), rubric, input_path=input_path,
                        definition_path=agent_definition, context_path=context_path):
        raise click.ClickException("Semantic output validation failed.")


@evaluate.command("audit-recall")
@click.option("--audit", "audits", multiple=True, required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="audit.json to score; repeat once per replicate")
@click.option("--original", "originals", multiple=True, required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="the frozen original_full each --audit reviewed, in the same order")
@click.option("--ground-truth", "ground_truth", required=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="held-out ground-truth file to score against")
@click.option("--arm", default=None, help="arm label to record; never inferred")
@click.option("--replicate", "replicates", multiple=True,
              help="replicate label for each --audit, in the same order")
@click.option("--output", default=None, type=click.Path(dir_okay=False, path_type=Path),
              help="also write the JSON report here")
@click.option("--json", "as_json", is_flag=True, help="print the JSON report instead of the summary")
def audit_recall_cmd(audits, originals, ground_truth, arm, replicates, output, as_json):
    """Recall of Phase 3 audits against held-out review observations (#2921).

    Offline and read-only: no model call, no source check. Each audit must
    pass audit_grammar and name its original's sha256 in source_review; only
    ground-truth entries pinned to that sha256 are scored, so another
    original gives 0 applicable entries and recall n/a, not 0. The hit rule
    is provisional until the owner signs it off. Unmatched audit flags are
    review candidates, never false positives.
    """
    import json as _json

    from data_sheets_schema import audit_recall
    if len(audits) != len(originals):
        raise click.UsageError("give one --original for each --audit, in the same order")
    if replicates and len(replicates) != len(audits):
        raise click.UsageError("give one --replicate for each --audit, or none")
    if output is not None and output.resolve() in {p.resolve() for p in (*audits, *originals, ground_truth)}:
        raise click.UsageError("--output names an input; a report never overwrites what it scored")
    raw = ground_truth.read_bytes()
    runs = [{"audit": a.read_bytes(), "original": o.read_bytes(), "audit_path": str(a),
             "original_path": str(o), "replicate": replicates[i] if replicates else None}
            for i, (a, o) in enumerate(zip(audits, originals))]
    try:
        truth = audit_recall.load_ground_truth(raw)
        value = audit_recall.report(runs, truth, ground_truth_raw=raw,
                                    ground_truth_label=str(ground_truth), arm=arm)
    except audit_recall.GroundTruthError as exc:
        raise click.ClickException("ground truth refused:\n" + "\n".join(
            f"  {p['at'] or '/'}: {p['problem']}" for p in exc.problems))
    except audit_recall.AuditRecallError as exc:
        raise click.ClickException(f"not scored: {exc}")
    text = _json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if output is not None:
        output.write_text(text, encoding="utf-8")
    click.echo(text if as_json else audit_recall.render_text(value), nl=False)


@evaluate.command("support-plan")
@click.option("--roster", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              default="notes/reference_rescore_2026-09-11/manifest.json", show_default=True)
@click.option("--output", type=click.Path(path_type=Path), required=True,
              help="Fresh directory; its parent must exist. Existing plans are never overwritten.")
@click.option("--profile", type=click.Choice(["bridge2ai", "neutral"]), required=True)
@click.option("--model", default=None, help="Evaluator override; otherwise records the generation-default basis.")
@click.option("--class-name", default="Dataset", show_default=True)
@click.option("--schema", "schema_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--max-tokens", type=click.IntRange(min=1), default=8000, show_default=True)
@click.option("--prices", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Optional local USD-per-million-token price JSON. Omitted prices stay unknown.")
@click.option("--plan-version", type=click.Choice(["1", "2"]), default="1", show_default=True,
              help="1: historical top-level support; 2: draft nested support with separate top-level fitness.")
@click.option("--artifact-kind", type=click.Choice(["full", "core", "collection"]),
              help="Required for plan version 2; must agree with the selected root class and roster.")
@click.option("--vocabulary", "vocabulary_path", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Version 2 only: explicit vocabulary snapshot overriding the selected profile's pin.")
@click.option("--relationship-policy", type=click.Choice(["strict", "inline-class-strings"]),
              default="strict", show_default=True,
              help="Version 2 opt-in: retain invalid inline strings as relationship claims, without schema repair.")
@click.option("--context-policy", type=click.Choice(["nearest-owner", "ancestor-qualifiers"]),
              default="nearest-owner", show_default=True,
              help="Version 2 opt-in: retain origin-scoped ancestor scalar fields and qualifiers as untrusted context.")
def support_plan_cmd(roster, output, profile, model, class_name, schema_path, max_tokens, prices,
                     plan_version, artifact_kind, vocabulary_path, relationship_policy, context_policy):
    """Freeze an OFFLINE typed-support/fitness plan; makes no model calls.

    Version 1 preserves the current top-level instrument; version 2 opts into
    draft nested support. Independent empirical calibration, context review,
    transport registration and paid authorization remain separate blockers.
    """
    from data_sheets_schema.support_plan import build_plan
    from data_sheets_schema import support_targets
    try:
        manifest = build_plan(roster, output, profile=profile, model=model,
                              class_name=class_name, schema_path=schema_path,
                              max_tokens=max_tokens, prices=prices, plan_version=int(plan_version),
                              artifact_kind=artifact_kind, vocabulary_path=vocabulary_path,
                              relationship_policy=(support_targets.POLICY if relationship_policy == "strict"
                                                   else support_targets.SCALAR_POLICY),
                              context_policy=(support_targets.CONTEXT_POLICY if context_policy == "nearest-owner"
                                              else support_targets.ANCESTOR_CONTEXT_POLICY))
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Saved {manifest['counts']['records']} records / "
               f"{manifest['counts']['axis_targets']} axis-targets to {output / 'manifest.json'}")
    click.echo("BLOCKED for paid use: " + ", ".join(manifest["readiness"]["blockers"]))
    if prices is None:
        click.echo("Estimated dollars: unknown (no local prices supplied).")


@evaluate.command("support-request")
@click.option("--plan", type=click.Path(exists=True, file_okay=False, path_type=Path), required=True)
@click.option("--target", required=True, help="Exact target id from manifest.json.")
def support_request_cmd(plan, target):
    """Verify a planned request and print its arguments; makes no model calls."""
    import json
    from data_sheets_schema.support_plan import materialize_request
    try:
        request = materialize_request(plan, target)
    except (OSError, ValueError, KeyError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(request, ensure_ascii=False, indent=2))


# A separate opt-in saved-response protocol; the existing planners stay unchanged.
from data_sheets_schema.cli.support_results import support_results
evaluate.add_command(support_results)

from data_sheets_schema.cli.support_execution import support_execution
evaluate.add_command(support_execution)

from data_sheets_schema.cli.support_calibration import support_calibration
evaluate.add_command(support_calibration)

from data_sheets_schema.cli.fitness_results import fitness_results
evaluate.add_command(fitness_results)

from data_sheets_schema.cli.cross_family_panel import cross_family_panel
evaluate.add_command(cross_family_panel)
