"""`d4d receipts` — check a run's coverage receipt and record the result (#708)."""
from __future__ import annotations

import sys
from pathlib import Path

import click

from data_sheets_schema.corpus import anchored as _corpus_path

@click.group()
def receipts():
    """Coverage and claim receipts: what the agent says it read, checked."""


def _run_paths(method: str, label: str, project: str) -> dict[str, Path]:
    from data_sheets_schema.provenance import CONCAT_DIR
    base = method[:-5] if method.endswith("_core") else method
    core_dir = _corpus_path(CONCAT_DIR) / f"{base}_core" / label
    return {"core_dir": core_dir,
            "full": _corpus_path(CONCAT_DIR) / base / label / f"{project}_d4d.yaml",
            "provenance": core_dir / f"{project}_provenance.yaml"}


@receipts.command("check")
@click.option("--method", default=None, help="run directory family; defaults to the one the label lives in (claudecode_agent or claudecode_api, #934)")
@click.option("--label", required=True)
@click.option("--project", required=True, help="dataset identifier carried by the run's files")
@click.option("--write", is_flag=True,
              help="write the `receipts` block into the provenance record and the "
                   "claim-receipt sidecar beside it")
@click.option("--strict", is_flag=True,
              help="exit 1 when a registered receipt floor fails; reported diagnostics are not all gated")
@click.option("--bundle", "bundle_opt", default=None, type=click.Path(exists=True, dir_okay=False),
              help="the bundle the run read; needed only before the provenance record "
                   "exists and the full record's header does not name it")
@click.option("--chunk-manifest", type=click.Path(dir_okay=False, path_type=Path),
              help="selected chunk manifest, including before provenance exists; recorded hashes still apply")
def check(method, label, project, write, strict, bundle_opt, chunk_manifest):
    """Validate `{PROJECT}_coverage_receipt.yaml` against the chunk manifest,
    the bundle and the full record, with affirmative counts.

    Prints `chunks N/N reviewed · snippets M/M verified · slots S/T with a
    receipt` and every finding. A receipt that is absent is reported as
    unchecked, never as clean; whether that is a defect depends on whether
    the run's procedure was to write one, which the provenance record says
    (`inputs.receipt_expected`).
    """
    from data_sheets_schema.cli.provenance import _require_repo_root_cwd
    _require_repo_root_cwd("d4d receipts check")          # a corpus write lands under the cwd (#1685)
    from data_sheets_schema.cli.method import resolve_method
    if not project.strip() or "/" in project or "\\" in project or project in {".", ".."}:
        raise click.BadParameter("must be a nonempty dataset basename", param_hint="--project")
    method = method or resolve_method(label, project)
    import yaml

    from data_sheets_schema import backfill_checks as bc
    from data_sheets_schema import receipts as rc

    p = _run_paths(method, label, project)
    if p["provenance"].exists():
        record = yaml.safe_load(bc._split_header(p["provenance"].read_text(encoding="utf-8"))[1]) or {}
        inputs = record.get("inputs") or {}
        bundle = bc.declared_bundle(record, p["provenance"])
        md5, expected = inputs.get("bundle_md5"), bool(inputs.get("receipt_expected"))
        recovery = {"snapshot_record": record, "bundle_rel_path": inputs.get("bundle_path"), "record_bundle_sha256": inputs.get("bundle_sha256"),
                    "record_chunks": inputs.get("chunks") if isinstance(inputs.get("chunks"), dict) else None}
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
        recovery = {}
        click.echo(f"   · no provenance record yet; checking against {bundle} as on disk")
    # The same recovery the backfill makes (#1140, #1187 review M2): the gate
    # on attestation must not say "unchecked" of a record the backfill checked.
    chunks = recovery.get("record_chunks") if isinstance(recovery.get("record_chunks"), dict) else None
    if chunks and chunks.get("path") and "manifest" not in recovery:
        from data_sheets_schema.provenance import resolve_record_input
        recovery["manifest"] = resolve_record_input(Path(chunks["path"]), p["provenance"])
        recovery["allow_manifest_discovery"] = False
    if chunk_manifest is not None:
        recovery["manifest"] = chunk_manifest
    block = rc.block_for(p["full"], rc.receipt_path(p["core_dir"], project), bundle, md5, expected, **recovery)
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


@receipts.command("sources")
@click.option("--method", default=None, help="run directory family; defaults to the one the label lives in (claudecode_agent or claudecode_api, #934)")
@click.option("--label", required=True)
@click.option("--project", required=True, help="dataset identifier carried by the run's files")
@click.option("--examples", type=click.IntRange(min=0), default=10, show_default=True,
              help="paths to list from each of the higher-tier and supersession token screens")
@click.option("--at-run-commit", is_flag=True,
              help="read tiers from the source manifest bytes the run recorded (inputs.source_manifest), "
                   "recovered from git by hash when the file has changed since, instead of the selected manifest (#3050)")
@click.option("--json", "as_json", is_flag=True, help="emit the whole report, one row per path included, as JSON")
def sources(method, label, project, examples, at_run_commit, as_json):
    """Which source documents a run's coverage receipt cites, by tier (#2937).

    Read-only: writes nothing, and no receipt, record or `receipts` block
    changes. Tiers are the `source_priority` tiers of the selected source
    manifest (`d4d --manifest`, default data/preprocessed/source_manifest.yaml),
    read through `source_metadata.projection`; the chunks are the ones the
    run's record hashed. Prints the receipted-path count in its stated unit,
    the share cited by exactly one document overall and by tier, each
    document's sole-citation share, and the paths cited only to a lower tier
    while a higher-tier chunk holds every token of the value — a lexical
    screen to spot-check, not a finding — and, as a separate count, the
    paths cited only to superseded sources while a replacement's chunk
    holds them (#3049). `--at-run-commit` takes the tiers from the manifest
    bytes the run recorded instead (#3050).
    """
    from data_sheets_schema.cli.method import resolve_method
    if not project.strip() or "/" in project or "\\" in project or project in {".", ".."}:
        raise click.BadParameter("must be a nonempty dataset basename", param_hint="--project")
    method = method or resolve_method(label, project)
    import json

    import yaml

    from data_sheets_schema import corpus
    from data_sheets_schema import receipt_sources as rs
    from data_sheets_schema import receipts as rc
    from data_sheets_schema.provenance import GitUnavailable

    p = _run_paths(method, label, project)
    receipt_file = rc.receipt_path(p["core_dir"], project)
    for need in (p["provenance"], receipt_file, p["full"]):
        if not need.exists():
            raise click.ClickException(f"no {need}")
    selected = None if at_run_commit else corpus.selected_manifest(allow_checkout_fallback=True)
    if selected is None and not at_run_commit:     # --at-run-commit reads the run's own manifest instead
        raise click.ClickException("tiers come from a source manifest's source_priority, and none is selected")
    try:
        run = rs.run_chunks(p["provenance"])
        if at_run_commit:
            raw, manifest_basis = rs.run_source_manifest(run["record"], p["provenance"])
            tiers_from = str(manifest_basis["path"])   # a path in both modes; the text line adds the basis (#3492)
        else:
            raw, manifest_basis, tiers_from = Path(selected).read_bytes(), None, str(selected)
        full = yaml.safe_load(p["full"].read_text(encoding="utf-8")) or {}
        if not isinstance(full, dict):
            raise ValueError(f"{p['full']} is not a mapping")
        report = rs.source_dependence(rc.load_receipt(receipt_file), run["manifest"], raw, project,
                                      full, run["texts"], examples=examples)
    except (OSError, ValueError, yaml.YAMLError, GitUnavailable) as exc:
        raise click.ClickException(str(exc)) from None
    report["run"] = {"method": method, "label": label, "bundle_basis": run["basis"],
                     "source_manifest": tiers_from,
                     "source_manifest_basis": rs.source_manifest_basis(run["record"], raw)}
    if at_run_commit:
        report["run"]["source_manifest_bytes"] = manifest_basis
        report["non_checks"] = rs.non_checks(at_run_commit=True)
    if as_json:
        click.echo(json.dumps(report, indent=1, ensure_ascii=False, default=str))
        return
    for line in rs.render(report):
        click.echo(line)


@receipts.command("status-context")
@click.option("--method", default=None,
              help="with --label/--project: the run directory family; defaults to the one the label lives in (#934)")
@click.option("--label", default=None, help="a run label; with --project, read the run's receipt, record and bundle")
@click.option("--project", default=None, help="dataset identifier carried by the run's files")
@click.option("--receipt", "receipt_file", default=None, type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="instead of a run: the coverage receipt (with --bundle and --record)")
@click.option("--bundle", "bundle_file", default=None, type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="with --receipt: the bundle the receipt names by md5")
@click.option("--record", "record_file", default=None, type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="with --receipt: the record the receipt addresses (the phase-1 snapshot where the run wrote one)")
@click.option("--final", "final_file", default=None, type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="with --receipt: the final record, to say whether each flagged value there expresses the status")
@click.option("--chunk-manifest", default=None, type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="with --receipt: the bundle's chunk manifest; default the one beside it or the study's")
@click.option("--corpus", is_flag=True,
              help="instead of a run or files: every committed coverage receipt, tallied per project by the "
                   "haystack form that located each snippet, with the unlocated and form-located ones listed "
                   "(at most 20 of each per receipt; the counts are complete and a cut list says how "
                   "many it left out, #3709, #3809)")
@click.option("--json", "as_json", is_flag=True, help="print the whole result as JSON")
def status_context(method, label, project, receipt_file, bundle_file, record_file, final_file,
                   chunk_manifest, corpus, as_json):
    """Where a receipted snippet lost a status marker its context carries
    (#2917): `governor_outside_snippet` and `modal_dropped`, label slots apart.

    Read-only and non-gating: it writes nothing, exits 0 whatever it finds,
    and leaves `receipts check` and every provenance block as they are. A
    flag is lexical — see the assurance line it prints.
    """
    import json

    import yaml

    from data_sheets_schema import receipts as rc
    from data_sheets_schema import status_context as sc
    if corpus:
        given = [flag for flag, v in (("--method", method), ("--label", label), ("--project", project),
                                      ("--receipt", receipt_file), ("--bundle", bundle_file),
                                      ("--record", record_file), ("--final", final_file),
                                      ("--chunk-manifest", chunk_manifest)) if v is not None]
        if given:
            raise click.UsageError(f"--corpus reads every committed receipt; {', '.join(given)} would be ignored")
        from data_sheets_schema.provenance import CONCAT_DIR
        out = sc.corpus_status_context(_corpus_path(CONCAT_DIR))
        if as_json:
            click.echo(json.dumps(out, indent=2, ensure_ascii=False, default=str))
        else:
            for line in sc.corpus_report_lines(out):
                click.echo(line)
        return
    if receipt_file is not None:
        if bundle_file is None or record_file is None or label or project or method:
            # --method names a run's directory family; the files named here
            # are read as given, so it would be silently ignored (#3253).
            raise click.UsageError("--receipt takes --bundle and --record, and no --label/--project/--method")
    elif not label or not project:
        raise click.UsageError("name a run (--label and --project) or files (--receipt, --bundle, --record)")
    elif not project.strip() or "/" in project or "\\" in project or project in {".", ".."}:
        raise click.BadParameter("must be a nonempty dataset basename", param_hint="--project")
    else:
        given = [flag for flag, v in (("--bundle", bundle_file), ("--record", record_file),
                                      ("--final", final_file), ("--chunk-manifest", chunk_manifest)) if v is not None]
        if given:
            # A run is read from its own files; a file option here would be
            # ignored and the result would be over other bytes (#3212).
            raise click.UsageError(f"{', '.join(given)} apply to --receipt, not to a run (--label/--project)")
    try:
        if receipt_file is not None:
            out = sc.file_status_context(receipt_file, bundle_file, record_file,
                                         chunk_manifest=chunk_manifest, final=final_file)
        else:
            from data_sheets_schema.cli.method import resolve_method
            p = _run_paths(method or resolve_method(label, project), label, project)
            out = sc.run_status_context(p["provenance"], rc.receipt_path(p["core_dir"], project), p["full"])
    except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        click.echo(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    else:
        for line in sc.report_lines(out):
            click.echo(line)


@receipts.command("origin")
@click.option("--transcript", "transcripts", multiple=True, required=True, type=click.Path(dir_okay=False),
              help="the run's stream-json transcript; repeat, first invocation first, for a killed-and-resumed run")
@click.option("--receipt", "receipt_file", required=True, type=click.Path(dir_okay=False),
              help="the coverage receipt as it is on disk now, whose sha256 is compared; without "
                   "--receipt-at-run it must also be spelled or resolve as the transcript's calls name it")
@click.option("--full", "full_file", required=True, type=click.Path(dir_okay=False),
              help="the full record's current path, reported and not read; without --full-at-run it must also be spelled "
                   "or resolve as the transcript's calls name it")
@click.option("--receipt-at-run", "receipt_at_run", type=click.Path(dir_okay=False),
              help="the receipt's path as the transcript spelled it, where the file has moved since the run; "
                   "--receipt is then the file read for the final sha256")
@click.option("--full-at-run", "full_at_run", type=click.Path(dir_okay=False),
              help="the full record's path as the transcript spelled it, where the file has moved since the run")
@click.option("--json", "as_json", is_flag=True, help="print the whole block as JSON")
def origin(transcripts, receipt_file, full_file, receipt_at_run, full_at_run, as_json):
    """Report which receipt snippets were written before the full record
    existed, and which after it (#2933). Report-only: it writes nothing.

    Rebuilds the receipt from the transcript's successful Writes, and
    replays each successful Edit or MultiEdit of it exactly (#3047): an
    `old_string` that does not occur, or occurs more than once without
    `replace_all`, or any edit that cannot be replayed exactly, makes the
    status `unknown`, and the rebuilt final receipt must still match the
    file on disk by sha256. It then classifies each final (chunk, snippet,
    slot) element as `contemporaneous`, `phase1_correction` (after the first full-record
    Write, before the first successful `derive core`, or to the end when
    none succeeded) or `phase3_backport`. A derive counts only where its
    call's result carries its own status: it is the command's last part, or
    every join after it is `&&` and the call succeeded. A piped,
    backgrounded, grouped or multi-line derive, one after `||` or followed
    by `;`, or a failed `&&` chain cannot be placed, unless the native
    control denied the call, or the runtime did in `dontAsk` mode and its
    terminal `result` lists the call, which then never ran. `timeout`,
    `env` and `nice` wrappers are read through. A derive whose program is a
    variable or a relative path (`$PY -m data_sheets_schema.cli`, `./d4d`)
    cannot be placed, as that program may be a wrapper. Three kinds of part carrying
    the words `derive core` cannot be placed: one that is neither a d4d call
    it reads nor a program known only to read, such as a `bash -c` or an
    `xargs` part; a reader part in a command where a later pipe feeds a
    program not known only to read (`echo '... derive core ...' | bash`);
    and, in a command with a substitution anywhere, every such part. The words are matched after quote and escape
    characters are removed (`bash -c 'd4d derive "core"'`), and `derive` followed by a word
    supplied at run time (`$SUB`, `$(echo core)`, `xargs`'s `{}` or any other replacement
    string it sets, such as `-I%` or `-J %`, or the word xargs appends after a `derive` that
    ends its command, redirections such as `2>&1` aside, or after a `derive` with a
    redirection directly after it) cannot be placed either. A command the tokenizer
    cannot split (an unclosed quote, or an apostrophe in a heredoc body read as
    commands) is tested whole for the same words, and a match cannot be placed, and so does a derive call with a
    redirection among its words (`--full 2>/dev/null F`). Last, a command-wide
    backstop: a call carrying more `derive` words than these rules gave
    rows, whose raw text with quotes
    and escapes removed carries the whole word `derive` anywhere (a
    substitution, an assignment, a `cd` part, an `xargs` argument) beside a
    `d4d`, `data_sheets_schema` or `$`-variable invocation, cannot be placed;
    its cost is a false `unknown` (`grep 'd4d derive core' notes.md`). A
    derive whose words are not on the command line (a script, an alias, a variable supplying
    `derive` itself, `python -c` building the arguments) is placed by position: a
    shell call that runs a program this does not read (anything but a reader, a
    builtin `cd`, `pushd` or `popd` -- not `./cd` or `poetry run cd` -- a d4d call of a literal subcommand, or `linkml-validate` or
    `linkml-term-validator` with the options it reads, each run as its words name it: a bare
    name or absolute path, no assignment before it, `printf -v` included, and no directory
    change before a `python -c` or `-m` part or a `poetry run` part, a `derive core` call
    aimed at another record included; the inner command of a command or
    process substitution is never read), that had not returned when the first full-record Write was
    issued (one in flight with it, backgrounded by its `run_in_background` input or its result,
    or started with `&`, `coproc`, `setsid` and the like, or by a process substitution
    `<(...)` or `>(...)`, which bash does not wait for, counts, a `&` inside a nested shell's
    word read as that shell splits a word with a space in it, and the word a shell nested in
    it gives its `-c`, or `eval` or `ssh` runs, read so in turn) and was issued before the derive, with a receipt change returning after both
    it and the first full-record Write were issued,
    makes the status `unknown`; its cost is a false `unknown` for such a program that
    derived nothing. A command the tokenizer cannot split is such a call, open-ended where its
    text carries a `&`, `coproc`, `setsid` and the like, `<(` or `>(`. A script that detaches a child itself
    is not seen as open-ended, nor is an
    environment set outside the command read, nor a package in the directory the session's
    shell started in that a `python -c` or `-m` part imports first, nor the project there whose
    virtualenv a `poetry run` part takes; after an earlier call whose `cd`, `pushd` or `popd`
    may have left that directory (plain, or behind a brace, a compound keyword, `!`, `time`,
    `builtin` or `command`, or one `eval` runs or may run), or which may run code not on its
    command line in that shell (`source`, `.`, or a program named by a bare word this does
    not read, which may be a function or an alias; not a path, a reader or a d4d call),
    such a part counts as after a directory change, and a relative `--full` cannot be
    placed, even where the transcript records a directory for the call. A change in a
    subshell, an unquoted `$(...)`, `<(...)` or `>(...)`, a pipe's left side or a `&` job
    counts too, though it runs in a child: which parts a child runs is not read (#3810);
    one in a backquoted or double-quoted substitution is not read; and a command the
    tokenizer cannot split counts. Where the transcript records another directory and no
    earlier change was seen, such a part counts as after a change too, and a relative
    `--full` resolves against the recorded directory. A redirection before a program is read
    past (`2>/dev/null cd /tmp`); a program word built at run time (`$C /tmp`, `c${X}d`,
    a glob) counts as a change and, at a part's head, as open-ended (`$X ./derive.sh`);
    the command `eval` runs is its words joined and tokenised again (`eval
    '"cd" /tmp'`), and one carrying a word supplied at run time or that cannot be split
    counts as a change and as open-ended; every argument of a shell given `-c` (`bash
    -ceo pipefail 'cmd'`), the command `eval` runs and each run of `ssh`'s arguments to
    the end are read for a `&` and the like, and one carrying a word supplied at run
    time is open-ended (`bash -c "$X"`); and a command the tokenizer cannot split is
    open-ended where any word in it starts with `$` or a backquote. One gate on a
    command's text, before any lexing, chooses its reading (#4028): v6 reads a command
    of printable ASCII, tabs and newlines only, with no backslash-newline, no `$$`, no
    `$(`, `${`, `$[`, `$((`, `((`, `<(`, `>(` or backquote anywhere, and not both a `<<`
    and a `$'`, where its here-documents are data and it can split it; every other
    command is read exactly as origin/main read it, and a nested command string (a
    substitution's command, a `-c` string, `eval`'s command) is always split as
    origin/main split it (#4029). v6 lexes as bash lexes (#3830): a quoted or escaped
    operator (`';'`, `'&&'`, `\\;`) is a word, never a join; a `$'...'` string closes
    where bash closes it, past a `\\'`; and a brace expansion with a quoted blank in it
    (`{cd,'/tmp a b'}`) is a program built at run time (#3924). A double-quoted word
    still ends at its first `"`, and a substitution is read to its `)` by counting
    brackets, so a case pattern's `)` ends it (#3925: these wait for a shell grammar).
    A here-document body is one data word, never commands of this shell (#3897), only
    where one part of the command carries the here-documents; every part before it is
    `cd WORD` or `mkdir [-p] WORD...`, every word unquoted and plain (#4028); that part
    and every part after it is plainly run -- its program its first word, with no
    assignment, `env`, `poetry run`, other wrapper or redirection before it (#3996) --
    and is a reader other than `sed` or `rg`, a builtin `cd`, `pushd` or `popd`, or a
    plain-named `python*` interpreter reading its program from the here-document it
    carries (`python3 - <<'EOF'`, standard input); nothing substitutes; and every
    delimiter is a plain word (letters, digits, `_`, `-`, `.`), bare or wholly inside
    one pair of single or double quotes (#3947). Anywhere else the body's lines are
    read as commands, as origin/main read them. A tool
    call whose name is not a non-empty string is a malformed call (#3918). A relative `--full`
    after a `cd`, `pushd` or `popd` resolves against the new directory only
    where every join from the change to the derive is `&&`, and after one `eval` runs
    or may run it cannot be placed. Where the
    history cannot be rebuilt the status is `unknown`, with the reasons,
    and nothing is classified; that includes a receipt Write (or replayed
    Edit/MultiEdit) in flight together with another receipt change, the
    draft or the derive. Prints counts, chunk ids, slot paths and hashes, never
    snippet text.
    """
    import json

    from data_sheets_schema import receipt_origin as ro
    block = ro.origin([Path(t) for t in transcripts], Path(receipt_file), Path(full_file),
                      receipt_at_run=Path(receipt_at_run) if receipt_at_run else None,
                      full_at_run=Path(full_at_run) if full_at_run else None)
    if as_json:
        click.echo(json.dumps(block, indent=2))
    else:
        for line in ro.summary(block):
            click.echo(f"   {line}")
