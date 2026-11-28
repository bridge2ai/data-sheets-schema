"""Apply the reviewed CLI integration delta for issues 6388-6394, 2026-11-26.

Input: the selection feature checkout at its pre-round-2 CLI shape.
Output: that checkout's CLI and focused mock controls, preserving scanner lines.
This edit helper never runs selection or touches a scoring corpus.
"""
from pathlib import Path


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("edit anchor is not unique: " + old[:90])
    return text.replace(old, new, 1)


def main():
    path = Path("src/data_sheets_schema/cli/runs.py")
    text = path.read_text()
    historical_lines = {number: text.splitlines()[number - 1] for number in (1777, 1939)}
    text = once(text, "score_policy=None, score_instrument=None, score_receipts=(), score_owner_rulings=None):",
                "score_policy=None, score_instrument=None, score_receipts=(), score_owner_rulings=None, score_owner_authorization=None):")
    text = once(text, "                                     score_receipts, score_owner_rulings)",
                "                                     score_receipts, score_owner_rulings, execute=execute, authorization=score_owner_authorization)")
    text = once(text, '    labels = sorted(p.name for p in base_dir.glob(f"{config}_rep*") if p.is_dir())',
                '    labels = _selection_labels(base_dir, config, score_policy)')
    text = once(text, '        loaded = _yaml.safe_load(record.read_text(encoding="utf-8"))\n        slots = len(loaded) if isinstance(loaded, dict) else 0',
                '        loaded = _selection_record_mapping(record, score_policy)\n        slots = len(loaded) if isinstance(loaded, dict) else 0')
    text = once(text, '        ok, detail = _validates(record)\n        live = VALID if ok else INVALID',
                '        ok, detail = _selection_live_validation(record, loaded, score_policy)\n        live = VALID if ok else INVALID')
    text = once(text, '        candidates, contenders, adverse_of, evidence_why, criterion)',
                '        candidates, contenders, adverse_of, evidence_why, criterion, authorization=score_owner_authorization)')
    start = text.index('def _require_score_selection_options(')
    stop = text.index('\ndef _print_selection_reason(', start)
    text = text[:start] + '''def _selection_labels(base, config, score_policy):
    labels = sorted(p.name for p in base.glob(f"{config}_rep*") if p.is_dir())
    if not score_policy:
        return labels
    from data_sheets_schema.runs import REPLICATE_RE
    return [label for label in labels if (match := REPLICATE_RE.fullmatch(label))
            and match.group("config") == config]


def _selection_record_mapping(record, score_policy):
    import yaml
    try:
        return yaml.safe_load(record.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError, UnicodeDecodeError):
        if not score_policy:
            raise
        return None


def _selection_live_validation(record, loaded, score_policy):
    if score_policy and not isinstance(loaded, dict):
        return False, "unreadable record"
    if not score_policy:
        return _validates(record)
    try:
        return _validates(record)
    except (ValueError, OSError):
        return False, "record validation could not be read"


def _require_score_selection_options(score_policy, score_instrument, score_receipts,
                                     score_owner_rulings, *, execute=False, authorization=None):
    """Keep preflight and score options outside the historical selector layout."""
    from data_sheets_schema.cli.provenance import _require_repo_root_cwd
    _require_repo_root_cwd("d4d runs select")
    if bool(score_policy) != bool(score_instrument):
        raise click.ClickException("--score-policy and --score-instrument must be supplied together")
    if (score_receipts or score_owner_rulings or authorization is not None) and not score_policy:
        raise click.ClickException("score evidence, owner rulings and authorization require --score-policy")
    if authorization is not None and (not isinstance(authorization, str) or not authorization.strip()):
        raise click.ClickException("--score-owner-authorization needs nonempty owner text")
    if score_policy and execute and authorization is None:
        raise click.ClickException("--score-owner-authorization TEXT is required to execute score-policy selection")


def _select_with_score_policy(method, project, config, score_policy, score_instrument,
                              score_receipts, score_owner_rulings, candidates, contenders,
                              adverse_of, evidence_why, criterion, *, authorization=None):
    """Return the original coverage pick unless the caller opted into scoring."""
    winner = contenders[0]
    runner_up = contenders[1] if len(contenders) > 1 else None
    margin = winner[3] - runner_up[3] if runner_up else None
    if not score_policy:
        return winner, runner_up, margin, criterion, None
    from data_sheets_schema.score_selection import decide
    try:
        table, variation = _score_selection_context(
            method, config, score_instrument, score_receipts,
            project=project, candidates=candidates,
            adverse_of=adverse_of, evidence_why=evidence_why)
        decision = decide(table, variation, score_instrument, policy_pick=winner[0])
        score_record = decision["score_policy"]
        if score_owner_rulings:
            score_record["owner_rulings"] = _score_owner_rulings(score_owner_rulings, table)
        if authorization is not None:
            score_record["owner_authorization"] = authorization
    except (ValueError, OSError) as error:
        raise click.ClickException(str(error)) from error
    _score_report("Evidence table", table)
    _score_report("Series variation", variation)
    _score_report("Score policy", score_record)
    click.echo(f"Current policy pick: {score_record['current_policy_pick']}")
    click.echo(f"score_gap_v1 pick: {decision['selected']}")
    click.echo(f"Deciding rule: {score_record['rule']}; "
               f"reason: {score_record.get('fallback_reason') or 'score gap and no rubric reversal'}")
    for ruling in score_record.get("owner_rulings", []):
        click.echo(f"Owner ruling recorded (does not change arithmetic): {ruling['label']} / "
                   f"{ruling['slot']}: {ruling['ruling']} [{ruling['authorization_reference']}]")
    winner = next(c for c in contenders if c[0] == decision["selected"])
    # This existing field remains the original coverage pick's margin over its
    # original coverage runner, even when a score gap promotes another record.
    criterion += "; score_gap_v1 decision: " + score_record["rule"]
    return winner, runner_up, margin, criterion, score_record

''' + text[stop:]
    start = text.index('def _score_selection_context(')
    stop = text.index('\ndef _score_report(', start)
    text = text[:start] + '''def _score_selection_context(method, config, instrument_id, receipt_roots, *,
                             project=None, candidates=(), adverse_of=None,
                             evidence_why=None):
    """Read each series record and retained evidence index once for pooled noise."""
    from data_sheets_schema.runs import CONCAT_DIR, REPLICATE_RE
    from data_sheets_schema.score_selection import build_evidence_table, load_evidence_index, pooled_variation

    concat = _corpus_path(CONCAT_DIR).resolve()
    corpus_root = concat.parent.parent
    base = concat / method
    directories = [base / label for label in _selection_labels(base, config, True)]
    roots = tuple(Path(p) for p in receipt_roots)
    index = load_evidence_index(roots)
    projects = {p.name[:-len("_d4d.yaml")] for directory in directories
                for p in directory.glob("*_d4d.yaml")}
    for entry in index["runs"].values():
        identity = entry["plan"].get("identity", {})
        label = identity.get("label", "")
        match = REPLICATE_RE.fullmatch(label) if isinstance(label, str) else None
        if (match and match.group("config") == config and identity.get("method") == method
                and identity.get("instrument_id") == instrument_id and isinstance(identity.get("project"), str)):
            projects.add(identity["project"])
            directory = base / label
            if directory not in directories:
                directories.append(directory)
    directories.sort()
    if project is not None:
        projects.add(project)
    all_rows, selected = [], []
    for name in sorted(projects):
        if name == project:
            rows = [{"label": label, "record": record, "validity": status,
                     "slots": slots if status not in ("incomplete", "no record") else None,
                     "review_adverse": (adverse_of or {}).get(label),
                     "review_not_evidence": (evidence_why or {}).get(label)}
                    for label, record, status, slots, _recorded, _detail in candidates]
            known = {row["label"] for row in rows}
            rows.extend({"label": directory.name, "record": directory / f"{name}_d4d.yaml",
                         "validity": "no record", "slots": None}
                        for directory in directories if directory.name not in known)
        else:
            rows = [{"label": directory.name, "record": directory / f"{name}_d4d.yaml",
                     "validity": "not measured", "slots": None} for directory in directories]
        table = build_evidence_table(name, config, instrument_id, candidates=rows,
                                     corpus_root=corpus_root, evidence_roots=roots, evidence_index=index)
        all_rows.extend(table)
        if name == project:
            selected = table
    if not all_rows:
        raise ValueError(f"no records for configuration {config!r}")
    variation = pooled_variation(all_rows)
    return (selected if project is not None else all_rows), variation

''' + text[stop:]
    start = text.index('def _score_owner_rulings(')
    stop = text.index('\n\nselect_cmd.params.extend(', start)
    text = text[:start] + '''def _score_owner_rulings(path, table):
    """Validate and record owner adjudications; never alter the score arithmetic."""
    import json
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, list) or not value:
        raise ValueError("owner rulings must be a nonempty JSON list")
    available = {row["label"]: set(row.get("slot_names", [])) for row in table}
    for row in value:
        if (not isinstance(row, dict) or row.get("label") not in available
                or any(not isinstance(row.get(key), str) or not row[key].strip()
                       for key in ("slot", "ruling", "authorization_reference"))):
            raise ValueError("each owner ruling needs a candidate label, slot, ruling and authorization_reference")
        if row["slot"] not in available[row["label"]]:
            raise ValueError("owner ruling slot is absent from the named candidate evidence")
    return value
''' + text[stop:]
    text = once(text, '    click.Option(["--score-owner-rulings"], type=click.Path(exists=True, dir_okay=False), default=None,\n                 help="Owner-adjudicated content findings JSON, recorded without automatic ranking effects."),',
                '    click.Option(["--score-owner-rulings"], type=click.Path(exists=True, dir_okay=False), default=None,\n                 help="Owner-adjudicated content findings JSON, recorded without automatic ranking effects."),\n    click.Option(["--score-owner-authorization"], default=None,\n                 help="Explicit owner text required before recording a score-policy canonical mark."),')
    lines = text.splitlines()
    if any(lines[number - 1] != value for number, value in historical_lines.items()):
        raise ValueError("historical scanner-hit lines moved")
    path.write_text(text)
    print("Updated CLI; historical scanner-hit lines preserved at 1777 and 1939")


def refine():
    path = Path("src/data_sheets_schema/cli/runs.py")
    text = path.read_text()
    historical = {number: text.splitlines()[number - 1] for number in (1777, 1939)}
    text = once(text, '        click.echo("\\nDry run. Re-run with --execute to record the choice.")',
                '        click.echo(_score_selection_dry_run_message(score_record))')
    text = once(text, '        identity = entry["plan"].get("identity", {})\n        label = identity.get("label", "")',
                '        identity = entry["plan"].get("identity", {})\n'
                '        if not isinstance(identity, dict):\n'
                '            index["issues"].append("retained plan identity is not a mapping")\n'
                '            continue\n'
                '        label = identity.get("label", "")')
    text = once(text, '            projects.add(identity["project"])\n            directory = base / label',
                '            name = identity["project"]\n'
                '            if not name or Path(name).name != name or name in (".", ".."):\n'
                '                index["issues"].append("retained series plan has invalid project identity")\n'
                '                continue\n'
                '            projects.add(name)\n'
                '            directory = base / label')
    text = once(text, '    if score_policy and execute and authorization is None:\n',
                '    if authorization is not None:\n'
                '        try:\n'
                '            _require_portable_owner_text(authorization)\n'
                '        except ValueError as error:\n'
                '            raise click.ClickException(str(error)) from error\n'
                '    if score_policy and execute and authorization is None:\n')
    text = once(text, '    for row in value:\n        if (not isinstance(row, dict) or row.get("label") not in available',
                '    for row in value:\n'
                '        if isinstance(row, dict) and set(row) - {"label", "slot", "ruling", "authorization_reference"}:\n'
                '            raise ValueError("owner ruling has unknown fields")\n'
                '        if (not isinstance(row, dict) or row.get("label") not in available')
    text = once(text, '        if row["slot"] not in available[row["label"]]:',
                '        for field in ("label", "slot", "ruling", "authorization_reference"):\n'
                '            _require_portable_owner_text(row[field])\n'
                '        if row["slot"] not in available[row["label"]]:')
    helper = '''def _score_selection_dry_run_message(score_record):
    if score_record is None:
        return "\\nDry run. Re-run with --execute to record the choice."
    return ("\\nDry run. A score-policy canonical mark requires --execute and "
            "--score-owner-authorization TEXT from the owner.")


def _require_portable_owner_text(value):
    from pathlib import PurePosixPath, PureWindowsPath
    from data_sheets_schema._score_selection_math import _portable_text
    if (_portable_text(value) != value or PurePosixPath(value).is_absolute()
            or PureWindowsPath(value).is_absolute()):
        raise ValueError("owner records must use repository-relative references, not absolute paths")


'''
    text = once(text, 'def _selection_labels(base, config, score_policy):',
                helper + 'def _selection_labels(base, config, score_policy):')
    if any(text.splitlines()[number - 1] != value for number, value in historical.items()):
        raise ValueError("historical scanner-hit lines moved")
    path.write_text(text)
    print("Refined CLI metadata discovery and portable owner input guards")


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--refine"]:
        refine()
    elif not sys.argv[1:]:
        main()
    else:
        raise SystemExit("use no arguments or --refine")
