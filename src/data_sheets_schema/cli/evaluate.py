"""Evaluate command group for D4D CLI.

Commands for evaluating D4D datasheet quality.
"""

import click
import sys
from pathlib import Path
from data_sheets_schema.constants import PROJECTS, METHODS, RUBRIC_TYPES
from data_sheets_schema.cli._repo_utils import setup_repo_imports, require_repo_context

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
def verifiable_cmd(project, method, labels, show):
    """Check the values a record states against the documents it declared.

    Answers the half of #165 that survives having no gold standard: a DOI, a
    date, a count and an accession must appear literally in a source document,
    because that is where they came from. No reference record is needed, and no
    LLM.

    `stated` is printed beside `grounded` on purpose. A record that states
    nothing is trivially correct on everything it states, so the ratio alone
    would rank an empty record top.
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
    import yaml as _yaml
    from data_sheets_schema.runs import discover, record_path
    from data_sheets_schema.verifiable import (
        check_record, declared_bundle, identifier_slots,
    )

    skip = identifier_slots()
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
            # The bundle the run declared, not the baseline one. See
            # verifiable.declared_bundle: arms read different inputs, and
            # assuming the baseline reported the whole crate arm as inventing
            # every value it stated.
            bundle = declared_bundle(run.method, run.label, proj)
            if bundle is None:
                bundle = (Path("data/preprocessed/concatenated")
                          / f"{proj}_preprocessed.txt")
            rec = record_path(run.method, run.label, proj)
            if not (bundle.exists() and rec and rec.exists()):
                continue
            r = check_record(_yaml.safe_load(rec.read_text(encoding="utf-8")),
                             bundle.read_text(encoding="utf-8"),
                             project=proj, label=run.label, skip_slots=skip)
            rows.append(r)

    if not rows:
        click.echo("No records matched."); return

    click.echo(f"{'project':10}{'label':38}{'stated':>7}{'grounded':>9}{'rate':>7}")
    for r in sorted(rows, key=lambda x: (x.project, x.label)):
        rate = f"{r.rate:.1%}" if r.rate is not None else "  n/a"
        click.echo(f"{r.project:10}{r.label:38}{r.stated:>7}{r.grounded:>9}{rate:>7}")
        for c in r.ungrounded[:show]:
            click.echo(f"    [{c.kind}] {c.slot}: {c.value[:70]}")

    total_stated = sum(r.stated for r in rows)
    total_ok = sum(r.grounded for r in rows)
    click.echo(f"\n{total_ok}/{total_stated} values grounded across "
               f"{len(rows)} record(s)")
    click.echo("A value is 'ungrounded' when it appears in no declared source "
               "document. Identifiers the generator mints are excluded — they "
               "are not claims about the world.")


@evaluate.command()
@click.option('--project', type=click.Choice(PROJECTS),
              help='Evaluate specific project only (default: all)')
@click.option('--method', type=click.Choice(METHODS), default='gpt5',
              help='Method to evaluate')
@click.option('--output-dir', type=click.Path(), default='data/evaluation',
              help='Output directory for evaluation reports')
def presence(project, method, output_dir):
    """Run presence-based evaluation (field existence check)."""
    require_repo_context("d4d evaluate presence")

    if project:
        click.echo(f"📊 Evaluating {project} ({method}) - presence-based...")
    else:
        click.echo(f"📊 Evaluating all projects ({method}) - presence-based...")

    # Import and call the evaluation script
    setup_repo_imports()
    from src.evaluation.evaluate_d4d import main as eval_main

    # Set up args for the evaluation script
    old_argv = sys.argv
    sys.argv = ['evaluate_d4d.py',
                '--methods', method,
                '--output-dir', output_dir]
    if project:
        sys.argv.extend(['--project', project])

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
@click.option('--project', type=click.Choice(PROJECTS), required=True,
              help='Project name')
@click.option('--method', type=click.Choice(METHODS), required=True,
              help='Generation method')
@click.option('--rubric', type=click.Choice(RUBRIC_TYPES + ['both']),
              default='both',
              help='Which rubric to use')
@click.option('--output-dir', type=click.Path(), default='data/evaluation_llm',
              help='Output directory for LLM evaluation reports')
def llm(file, project, method, rubric, output_dir):
    """Run LLM-based quality evaluation (requires ANTHROPIC_API_KEY)."""
    require_repo_context("d4d evaluate llm")

    click.echo(f"🤖 LLM evaluating {file} with {rubric}...")
    click.echo("⚠️  Note: Requires ANTHROPIC_API_KEY environment variable")

    # Import and call the LLM evaluation script
    setup_repo_imports()

    try:
        from src.evaluation.evaluate_d4d_llm import main as llm_eval_main
    except ImportError:
        click.echo("❌ Error: LLM evaluation script not found", err=True)
        click.echo("   Expected: src/evaluation/evaluate_d4d_llm.py", err=True)
        sys.exit(1)

    # Set up args for the LLM evaluation script
    old_argv = sys.argv
    sys.argv = ['evaluate_d4d_llm.py',
                '--file', file,
                '--project', project,
                '--method', method,
                '--rubric', rubric,
                '--output-dir', output_dir]

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
@click.option("--runtime", type=click.Choice(["api", "agentic"]), default=None,
              help="which runtime's canonical set (#690); required where a project is marked under both")
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
        return

    for evaluation in evaluations:
        click.echo(f"{evaluation.name}\t{evaluation.path}")
    click.echo("")
    click.echo(summarise(evaluations))


@evaluate.command("related-datasets")
@click.option("--runtime", type=click.Choice(["api", "agentic"]), default=None,
              help="which runtime's canonical set (#690), where no records are given")
@click.argument("records", nargs=-1, type=click.Path(exists=True))
@click.option("--project", default=None,
              help="Limit to one project when reading the canonical set.")
def related_datasets_cmd(records, project, runtime):
    """Classify `related_datasets` defects by mode (#292).

    All three VOICE replicates fail this slot, each differently, and
    `linkml-validate` reports them as three unrelated errors. The rerun's answer
    differs per mode: an aliased type recurring means the write-path normaliser
    did not run, an unknown type means the model reached for a word the DataCite
    vocabulary lacks, and an inline target under generic-v4 means that rule did
    not work.

    With no arguments, reads the canonical set.
    """
    import yaml

    from data_sheets_schema.related_datasets import inspect, summarise

    paths = [Path(r) for r in records]
    if not paths:
        from data_sheets_schema.evaluation_plan import NothingSelected, plan
        from data_sheets_schema.runs import AmbiguousCanonical
        try:
            paths = list(dict.fromkeys(
                e.path for e in plan(runtime=runtime) if project in (None, e.project)))
        except (NothingSelected, AmbiguousCanonical) as exc:
            raise click.ClickException(str(exc))

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
