"""Apply CLI roster and disclosure rulings for issues 6399/6401, 2026-11-26.

Input: exact cbea441ab CLI source. Output: revised CLI only. Preserves historical
selector line positions and default behavior; no model, corpus or scoring access.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "src/data_sheets_schema/cli/runs.py"
BASE = "cbea441abb233ac6041af9b13f9cbe6c518c0950"


def main():
    source = TARGET.read_text()
    original = subprocess.check_output(["git", "-C", str(ROOT), "show", BASE + ":src/data_sheets_schema/cli/runs.py"]).decode()
    if source != original:
        raise ValueError("CLI is not the frozen round-2 input")

    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError("ambiguous CLI edit: " + old[:80])
        source = source.replace(old, new, 1)

    replace("score_owner_rulings=None, score_owner_authorization=None):",
            "score_owner_rulings=None, score_owner_authorization=None, score_series_project=()):")
    replace("score_receipts, score_owner_rulings, execute=execute, authorization=score_owner_authorization)",
            "score_receipts, score_owner_rulings, execute=execute, authorization=score_owner_authorization, series_projects=score_series_project)")
    replace("candidates, contenders, adverse_of, evidence_why, criterion, authorization=score_owner_authorization)",
            "candidates, contenders, adverse_of, evidence_why, criterion, authorization=score_owner_authorization, series_projects=score_series_project)")
    replace('return False, "unreadable record"',
            'return False, f"{record.parent.name}/{record.name}: unreadable record"')
    replace('return False, "record validation could not be read"',
            'return False, f"{record.parent.name}/{record.name}: record validation could not be read"')
    replace('score_owner_rulings, *, execute=False, authorization=None):',
            'score_owner_rulings, *, execute=False, authorization=None, series_projects=()):')
    replace('if (score_receipts or score_owner_rulings or authorization is not None) and not score_policy:',
            'if (score_receipts or score_owner_rulings or authorization is not None or series_projects) and not score_policy:')
    replace('score evidence, owner rulings and authorization require --score-policy',
            'score evidence, owner rulings, authorization and series projects require --score-policy')
    replace('adverse_of, evidence_why, criterion, *, authorization=None):',
            'adverse_of, evidence_why, criterion, *, authorization=None, series_projects=()):')
    replace('project=project, candidates=candidates,\n            adverse_of=adverse_of, evidence_why=evidence_why)',
            'project=project, candidates=candidates,\n            adverse_of=adverse_of, evidence_why=evidence_why, series_projects=series_projects)')
    replace('''        score_record = decision["score_policy"]
''', '''        score_record = decision["score_policy"]
        score_winner = next(c for c in contenders if c[0] == decision["selected"])
        other_contenders = [c for c in contenders if c[0] != decision["selected"]]
        coverage_runner = other_contenders[0] if other_contenders else None
        score_record["selected_coverage_margin_over_best_other"] = (
            score_winner[3] - coverage_runner[3] if coverage_runner else None)
        score_record["selected_coverage_comparison_label"] = coverage_runner[0] if coverage_runner else None
''')
    start = source.index("def _score_selection_context(")
    end = source.index("\ndef _score_report(", start)
    source = source[:start] + ROSTER_CONTEXT + source[end:]
    replace('''    click.Option(["--score-owner-authorization"], default=None,
                 help="Explicit owner text required before recording a score-policy canonical mark."),
''', '''    click.Option(["--score-owner-authorization"], default=None,
                 help="Owner text required before recording a score-policy mark; a recorded accident-prevention guard, not proof of authorization."),
    click.Option(["--score-series-project"], multiple=True,
                 help="Explicitly replace the selected manifest project roster; repeat once per project in the narrower series."),
''')
    replace('def score_variation_cmd(method, config, score_instrument, score_receipts):',
            'def score_variation_cmd(method, config, score_instrument, score_receipts, score_series_project=()):')
    replace('table, variation = _score_selection_context(method, config, score_instrument, score_receipts)',
            'table, variation = _score_selection_context(method, config, score_instrument, score_receipts,\n                                                     series_projects=score_series_project)')
    replace('''    click.Option(["--score-receipts"], type=click.Path(exists=True, file_okay=False), multiple=True),
])
''', '''    click.Option(["--score-receipts"], type=click.Path(exists=True, file_okay=False), multiple=True),
    click.Option(["--score-series-project"], multiple=True,
                 help="Explicitly replace the selected manifest project roster; repeat once per project in the narrower series."),
])
''')
    # D128 names two historical neutral-boundary comments by exact line.
    for number in (1777, 1939):
        if source.splitlines()[number - 1] != original.splitlines()[number - 1]:
            raise ValueError("historical scanner line moved")
    TARGET.write_text(source)
    if TARGET.read_text() != source:
        raise ValueError("saved CLI differs")


ROSTER_CONTEXT = '''def _score_project_name(name):
    from pathlib import PureWindowsPath
    return (isinstance(name, str) and bool(name.strip()) and name == name.strip()
            and name not in (".", "..") and Path(name).name == name
            and PureWindowsPath(name).name == name and "\\x00" not in name)


def _score_expected_projects(series_projects):
    """The expected project roster is declared independently of score evidence."""
    import hashlib
    from data_sheets_schema.registry import DEFAULT_MANIFEST, load_registry, selected_manifest

    if series_projects:
        names = list(series_projects)
        if any(not _score_project_name(name) for name in names) or len(set(names)) != len(names):
            raise ValueError("--score-series-project needs distinct project path components")
        return sorted(names), {"basis": "explicit_score_series_projects", "manifest_sha256": None}, []
    context = click.get_current_context(silent=True)
    requested = selected_manifest(context) if context is not None else DEFAULT_MANIFEST
    manifest_name = Path(requested).name if requested is not None else "no manifest"
    try:
        registry = load_registry(requested)
        names = registry.projects()
        digest = (hashlib.sha256(registry.path.read_bytes()).hexdigest()
                  if registry.path is not None and registry.path.is_file() else None)
    except (click.ClickException, OSError, ValueError) as error:
        return [], {"basis": "selected_source_manifest", "manifest_sha256": None}, [
            f"source manifest {manifest_name}: {type(error).__name__}; project roster is unreadable"]
    metadata = {"basis": "selected_source_manifest", "manifest_sha256": digest}
    if any(not _score_project_name(name) for name in names):
        return [], metadata, [f"source manifest {manifest_name}: invalid project path component"]
    return sorted(names), metadata, ([] if names else [
        f"source manifest {manifest_name}: no declared projects; expected roster unavailable"])


def _score_roster_pairs(pairs):
    return [{"project": project, "label": label} for project, label in sorted(pairs)]


def _score_selection_context(method, config, instrument_id, receipt_roots, *,
                             project=None, candidates=(), adverse_of=None,
                             evidence_why=None, series_projects=()):
    """Bind a manifest-declared project roster to the discovered label union."""
    from data_sheets_schema.runs import CONCAT_DIR, REPLICATE_RE
    from data_sheets_schema.score_selection import build_evidence_table, load_evidence_index, pooled_variation

    concat = _corpus_path(CONCAT_DIR).resolve()
    corpus_root = concat.parent.parent
    base = concat / method
    directories = [base / label for label in _selection_labels(base, config, True)]
    roots = tuple(Path(p) for p in receipt_roots)
    index = load_evidence_index(roots)
    discovered = {(p.name[:-len("_d4d.yaml")], directory.name) for directory in directories
                  for p in directory.glob("*_d4d.yaml")}
    for entry in index["runs"].values():
        identity = entry["plan"].get("identity", {})
        origin = Path(entry["plan_path"]).parent.name + "/plan.json"
        if not isinstance(identity, dict):
            index["issues"].append(f"{origin}: retained plan identity is not a mapping")
            continue
        label = identity.get("label", "")
        match = REPLICATE_RE.fullmatch(label) if isinstance(label, str) else None
        if (match and match.group("config") == config and identity.get("method") == method
                and identity.get("instrument_id") == instrument_id):
            name = identity.get("project")
            if not _score_project_name(name):
                index["issues"].append(f"{origin}: retained series plan has invalid project identity")
                continue
            discovered.add((name, label))
            directory = base / label
            if directory not in directories:
                directories.append(directory)
    directories.sort()
    expected_projects, roster, roster_problems = _score_expected_projects(series_projects)
    observed_projects = {name for name, _label in discovered}
    excluded = sorted(observed_projects - set(expected_projects)) if series_projects else []
    if series_projects:
        if project is not None and project not in expected_projects:
            raise ValueError(f"selected project {project}: outside the explicitly declared series roster")
        discovered = {pair for pair in discovered if pair[0] in expected_projects}
        projects = set(expected_projects)
    else:
        projects = set(expected_projects) | observed_projects
        if project is not None:
            projects.add(project)
    labels = [directory.name for directory in directories]
    expected = {(name, label) for name in expected_projects for label in labels}
    missing, unexpected = expected - discovered, discovered - expected
    roster.update(projects=expected_projects, replicate_labels=labels,
                  excluded_discovered_projects=excluded)
    roster_problems.extend(f"series roster missing {name}/{label}: no candidate record or retained plan"
                           for name, label in sorted(missing))
    roster_problems.extend(f"series roster unexpected {name}/{label}: project is not in the declared roster"
                           for name, label in sorted(unexpected))
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
    variation.update(series_roster=roster, expected_roster=_score_roster_pairs(expected),
                     discovered_census=_score_roster_pairs(discovered),
                     roster_missing=_score_roster_pairs(missing), roster_unexpected=_score_roster_pairs(unexpected))
    if roster_problems:
        if variation.get("s") is not None:
            import math
            variation["partial_variation"] = {
                "partial_s": variation["s"], "partial_T": 2 * variation["s"] * math.sqrt(2 / 3),
                "partial_degrees_of_freedom": variation.get("degrees_of_freedom"),
                "partial_records": variation.get("records"),
                "partial_per_project": variation.get("per_project"),
                "partial_per_rubric": variation.get("per_rubric")}
        variation["s"] = None
        variation["T"] = None
        variation["per_project"] = {}
        variation["per_rubric"] = {}
        variation["fallback_reasons"] = sorted(set(variation.get("fallback_reasons", []) + roster_problems))
        variation["not_measured_reason"] = "; ".join(variation["fallback_reasons"])
        variation["series_complete"] = False
    return (selected if project is not None else all_rows), variation

'''


if __name__ == "__main__":
    main()
