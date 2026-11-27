# Purpose: rerun the review's named mutations without altering source or evidence.
# Inputs: source checkout, Python interpreter and fresh evidence directory.
# Outputs: bounded subprocess logs and a structured mutation receipt in that directory.
# Serves: issue 6385 round-2 controls, 2026-11-26. Adapted from the review's
# mutation_harness.py by copying its literal mutation definitions, never importing it.
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

MATH = "src/data_sheets_schema/_score_selection_math.py"
READER = "src/data_sheets_schema/score_selection.py"
TESTS = ["tests/test_score_selection_math.py", "tests/test_score_selection_evidence.py",
         "tests/test_cli/test_score_selection_integration.py"]
BOUND_FILES = (MATH, READER, "src/data_sheets_schema/cli/runs.py", "tests/score_selection_cases.py", *TESTS)

MUTANTS = [
    ("M01 accept gap equal to T (<= becomes <)", MATH,
     'elif gap <= record["T"]:', 'elif gap < record["T"]:'),
    ("M02 population SD in the pool (df = n, not n-1)", MATH,
     "degrees = sum(len(values) - 1 for values in usable)", "degrees = sum(len(values) for values in usable)"),
    ("M03 drop the per-rubric no-reversal condition", MATH, "    elif reversals:", "    elif False:"),
    ("M04 let invalid replicates rank", MATH,
     'eligible = sorted((row for row in summaries if row["validity"] == "valid"), key=_coverage_key)',
     "eligible = sorted((row for row in summaries), key=_coverage_key)"),
    ("M05 two scorings are enough", MATH, 'if len(row["paired_numbers"]) < 3:', 'if len(row["paired_numbers"]) < 2:'),
    ("M06 threshold one standard error (2*s becomes 1*s)", MATH,
     'record["T"] = 2 * s * math.sqrt(2 / 3)', 'record["T"] = 1 * s * math.sqrt(2 / 3)'),
    ("M07 pair by position in the cell list, not by scoring number", MATH,
     "    paired = [(measured[RUBRICS[0]][number] + measured[RUBRICS[1]][number]) / 2\n              for number in paired_numbers]",
     "    paired = [(a + b) / 2 for a, b in zip(measured[RUBRICS[0]].values(), measured[RUBRICS[1]].values())]"),
    ("M08 reversal judged on scoring 1 alone, not the mean", MATH,
     'if highest["rubrics"][rubric]["mean"] < current["rubrics"][rubric]["mean"]]',
     'if highest["_values"][rubric][1] < current["_values"][rubric][1]]'),
    ("M09 equal rubric means count as a reversal (< becomes <=)", MATH,
     'if highest["rubrics"][rubric]["mean"] < current["rubrics"][rubric]["mean"]]',
     'if highest["rubrics"][rubric]["mean"] <= current["rubrics"][rubric]["mean"]]'),
    ("M10 a not-measured cell is read as zero", MATH,
     '                problems.append(f"{rubric} scoring {number}: not measured")\n                continue',
     "                values[number] = 0.0\n                continue"),
    ("M11 candidate spread is population SD", MATH,
     '"spread": stdev(values) if len(values) >= 2 else None', '"spread": __import__("statistics").pstdev(values) if len(values) >= 2 else None'),
    ("M12 current policy pick ignores coverage (label only)", MATH,
     'return (-(slots if _number(slots) else -1), row["label"])', 'return (0, row["label"])'),
    ("M13 pooled instrument mismatch is not checked in decide", MATH,
     'if pooled.get("instrument_id") != instrument_id:', "if False:"),
    ("M14 gap and T rounded to one decimal before comparison", MATH,
     '    record.update(highest_mean_pick=highest["label"], gap=gap)',
     '    gap = round(gap, 1); record["T"] = round(record["T"], 1)\n    record.update(highest_mean_pick=highest["label"], gap=gap)'),
    ("M15 pooled s taken from rubric10 values only, not the paired scoring score", MATH,
     '    result = _pool([row["_paired_values"] for row in summaries])',
     '    result = _pool([list(row["_values"]["rubric10"].values()) for row in summaries])'),
    ("M16 scoring score weighted 25/75 instead of equal", MATH,
     "(measured[RUBRICS[0]][number] + measured[RUBRICS[1]][number]) / 2",
     "(0.25 * measured[RUBRICS[0]][number] + 0.75 * measured[RUBRICS[1]][number])"),
    ("M17 pool only the records of valid candidates' project-wide noise: drop records with <3 scorings", MATH,
     "usable = [values for values in groups if len(values) >= 2]", "usable = [values for values in groups if len(values) >= 3]"),
    ("M18 measured-input drift between scorings is ignored", MATH,
     "        if identities and any(identity != identities[0] for identity in identities[1:]):", "        if False:"),
    ("M19 highest-mean pick is the LOWEST mean", MATH,
     'highest = min(eligible, key=lambda row: (-row["paired"]["mean"], *_coverage_key(row)))',
     'highest = min(eligible, key=lambda row: (row["paired"]["mean"], *_coverage_key(row)))'),
    ("E01 published bytes are not compared with the receipt hash", READER,
     '        _require(_sha(raw) == expected, "published bytes do not match accepted receipt")', "        pass"),
    ("E02 receipt need not bind its saved plan", READER,
     '    _require(receipt.get("plan_sha256") == _sha(json.dumps(plan, sort_keys=True).encode()),\n             "receipt does not bind its saved plan")', "    pass"),
    ("E03 percentage uses the first of max_points/adjusted (denominator source changed)", READER,
     'points, maximum = score.get("total_points"), score.get("adjusted_max_points")',
     'points, maximum = score.get("total_points"), score.get("max_points", score.get("adjusted_max_points"))'),
    ("E04 repeat manifest hashes are not compared", READER,
     '            _require(value.get("destination_sha256") == value.get("source_output_sha256") == expected,\n                     "repeat publication hash differs")', "            pass"),
    ("E05 published and validated hashes may differ", READER,
     '    _require(receipt.get("output_sha256") == receipt.get("validator_input_sha256"),\n             "published and validated hashes differ")', "    pass"),
    ("E06 refused receipt of a replacement need not be REFUSED or hash-bound", READER,
     '                _require(original["receipt_sha256"] == refused.get("sha256")\n                         and original["receipt"].get("status") == "REFUSED",\n                         "replacement refusal binding differs")', "                pass"),
    ("E07 published scorer_instrument is not checked", READER,
     '        _require(value.get("scorer_instrument") == {"id": instrument,\n                 "prompt_sha256": measured["prompt_sha256"], "runner_sha256": measured["runner_sha256"]},\n                 "published instrument differs")', "        pass"),
    ("E08 codex/validator exit codes and auth cleanup are not checked", READER,
     '    _require(type(receipt.get("codex_exit")) is int and receipt["codex_exit"] == 0\n             and type(receipt.get("validator_exit")) is int and receipt["validator_exit"] == 0\n             and receipt.get("auth_copy_absent") is True, "acceptance or cleanup is unproven")', "    pass"),
    ("E09 composed definition pin is not checked", READER,
     '    _require(provenance.get("composed_sha256") == result["definition_sha256"],\n             "composed definition is not pinned")', "    pass"),
    ("E10 plan metadata and plan inputs may disagree", READER,
     '        _require(digest == _mapping(inputs.get(input_name)).get("sha256"), "plan input and metadata differ")', "        pass"),
    ("E11 scoring 1 accepts a run that a repeat manifest references", READER,
     '        choices = [entry for entry in matches if entry["plan_path"] not in referenced\n                   and entry["receipt"].get("status") == "VALIDATED_AND_PUBLISHED"]',
     '        choices = [entry for entry in matches if entry["receipt"].get("status") == "VALIDATED_AND_PUBLISHED"][:1]'),
]

MUTANTS2 = [
    ("E12 control: record bytes are not compared with the scored record hash", READER,
     '    _require(result["record_sha256"] == record_sha, "scoring names changed record bytes")', "    pass"),
    ("E13 receipt status is not required to be VALIDATED_AND_PUBLISHED in the acceptance check", READER,
     '    _require(receipt.get("status") == "VALIDATED_AND_PUBLISHED", "scoring receipt is not accepted")', "    pass"),
    ("E14 repeat manifest status and copy validator exit are not checked", READER,
     '            _require(value.get("status") == "EXPORTED_VALIDATED_REPEAT"\n                     and value.get("copy_validator_exit") == 0, "repeat export is not accepted")', "            pass"),
    ("E15 published identity fields are not compared with the plan", READER,
     '            _require(value.get(key) == plan["identity"].get(key), "published scoring identity differs")', "            pass"),
    ("E16 published deterministic fields are not compared with the plan", READER,
     '            _require(value.get(key) == expected_value, "published measured-input metadata differs")', "            pass"),
    ("E17 output schema binding is optional", READER,
     '    result["schema_sha256"] = _digest(_mapping(inputs.get("output-schema.json")).get("sha256"))',
     '    result["schema_sha256"] = _mapping(inputs.get("output-schema.json")).get("sha256") or "absent"'),
    ("E18 duplicate repeat exports are tolerated (first wins)", READER,
     "        if len(exports) != 1:", "        if len(exports) < 1:"),
    ("E19 repeat manifest need not bind plan and receipt hashes", READER,
     '                _require(value.get("actual_" + kind) == entry[kind + "_path"]\n                         and value.get("actual_" + kind + "_sha256") == entry[kind + "_sha256"],\n                         "repeat metadata binding differs")', "                pass"),
]

RUNNER = r'''
import importlib.util, sys
target, source_path, old, new = sys.argv[1:5]
text = open(source_path, encoding="utf-8").read()
if old:
    assert text.count(old) == 1, ("mutation site not unique", text.count(old))
    text = text.replace(old, new)
name = {"_score_selection_math.py": "data_sheets_schema._score_selection_math",
        "score_selection.py": "data_sheets_schema.score_selection"}[target]
import data_sheets_schema
spec = importlib.util.spec_from_loader(name, loader=None, origin=source_path)
module = importlib.util.module_from_spec(spec)
module.__file__ = source_path
sys.modules[name] = module
exec(compile(text, source_path + " (mutant)", "exec"), module.__dict__)
setattr(data_sheets_schema, name.rsplit(".", 1)[1], module)
import pytest
sys.exit(pytest.main(sys.argv[5:]))
'''


SURVIVORS = {"M01", "M08", "M09", "M11", "M15", "E01", "E02", "E03", "E04", "E05",
             "E06", "E07", "E08", "E09", "E10", "E11", "E14", "E15", "E16", "E19"}


def adapted_mutation(label, old, new, source):
    """Preserve the reviewed defect when its source site moved; disclose edits."""
    key = label.split()[0]
    if key == "M05" and 'cells.append({"scoring_number": number, "status": "not measured"' in source:
        changes = [
            ('        for number in (1, 2, 3):', '        for number in (1, 2):'),
            ('if len(row["paired_numbers"]) < 3:', 'if len(row["paired_numbers"]) < 2:'),
            ('row["paired_numbers"] != [1, 2, 3]', 'row["paired_numbers"] not in ([1, 2], [1, 2, 3])'),
        ]
        changed = source
        for before, after in changes:
            if changed.count(before) != 1:
                return old, new, "M05 semantic adaptation site is absent or nonunique"
            changed = changed.replace(before, after)
        return source, changed, "Permit two cells at both the census and exact scoring-number guards; three remains accepted."
    if source.count(old) == 1:
        return old, new, None
    adaptations = {
        "E03": ('        points, maximum = score.get("total_points"), score.get("max_points")\n'
                '        adjusted = score.get("adjusted_max_points")\n'
                '        _require(all(type(item) in (int, float) and math.isfinite(item) for item in (maximum, adjusted))\n'
                '                 and maximum == {"rubric10": 50, "rubric20": 88}[family] and adjusted == maximum,\n'
                '                 "fixed percentage base requires max_points 50/88 and adjusted_max_points equal to it")',
                '        points, maximum = score.get("total_points"), score.get("adjusted_max_points")\n'
                '        adjusted = maximum',
                "Restore the reviewed adjusted-denominator behavior, including removal of the newly added equality guard."),
        "E16": ('        _published_deterministic_fields(value, plan["deterministic_fields"])',
                '        pass', "The equality checks moved into _published_deterministic_fields; bypass its call."),
        "M10": ('                    issue = "not measured: " + str(cell.get("reason") or "no accepted measurement")',
                '                    values[number] = 0.0', "Missing cells now carry a reason; inject zero at the same branch."),
    }
    return adaptations.get(key, (old, new, "original mutation site is absent or nonunique"))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run_one(args, label, relative, old, new, adaptation=None):
    path = args.source / relative
    raw = path.read_bytes()
    result = {"id": label.split()[0], "description": label, "module": relative,
              "source_sha256": sha(raw), "old": old, "new": new, "adaptation": adaptation}
    if old and raw.decode().count(old) != 1:
        return dict(result, verdict="SITE_DRIFT", matches=raw.decode().count(old))
    env = dict(os.environ, PYTHONPATH=str(args.source / "src"), PYTHONDONTWRITEBYTECODE="1")
    command = [str(args.python), "-c", RUNNER, path.name, str(path), old, new,
               *TESTS, "-q", "-p", "no:cacheprovider", "-x", "--no-header", "-o", "addopts="]
    try:
        done = subprocess.run(command, cwd=args.source, env=env, capture_output=True, text=True,
                              timeout=args.timeout)
    except subprocess.TimeoutExpired as exc:
        return dict(result, verdict="HARNESS_TIMEOUT", timeout=args.timeout)
    log = args.output / (result["id"] + ".log")
    text = done.stdout + "\n--- stderr ---\n" + done.stderr
    log.write_text(text, encoding="utf-8")
    failures = [line for line in done.stdout.splitlines() if line.startswith("FAILED")]
    errors = [line for line in done.stdout.splitlines() if line.startswith("ERROR")]
    verdict = "SURVIVED" if done.returncode == 0 else "KILLED" if done.returncode == 1 and failures and not errors else "HARNESS_ERROR"
    if not old:
        verdict = "BASELINE_PASSED" if done.returncode == 0 else "BASELINE_FAILED"
    return dict(result, verdict=verdict, returncode=done.returncode,
                failing_tests=failures, collection_errors=errors, log=log.name, log_sha256=sha(text.encode()))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--all", action="store_true", help="also rerun the 18 already-killed review mutations")
    args = parser.parse_args(argv)
    args.source = args.source.resolve(strict=True)
    args.output = args.output.absolute()
    if args.output.exists() or args.output.is_symlink():
        parser.error("output must be a fresh evidence directory")
    if args.source in args.output.parents or args.output in args.source.parents:
        parser.error("output and tested source must be disjoint")
    if not all((args.source / item).is_file() for item in BOUND_FILES):
        parser.error("source must contain the selected synthetic tests and both source modules")
    os.nice(10)
    args.output.mkdir(parents=True)
    before = {relative: sha((args.source / relative).read_bytes()) for relative in BOUND_FILES}
    results = [run_one(args, "BASE unmutated", MATH, "", "")]
    if results[0]["verdict"] == "BASELINE_PASSED":
        for label, relative, old, new in MUTANTS + MUTANTS2:
            if not args.all and label.split()[0] not in SURVIVORS:
                continue
            reviewed_old, reviewed_new = old, new
            old, new, adaptation = adapted_mutation(label, old, new, (args.source / relative).read_text())
            result = run_one(args, label, relative, old, new, adaptation)
            result.update(reviewed_old=reviewed_old, reviewed_new=reviewed_new)
            results.append(result)
            print(result["id"], result["verdict"], flush=True)
    after = {relative: sha((args.source / relative).read_bytes()) for relative in before}
    receipt = {"source": str(args.source), "before_sha256": before, "after_sha256": after,
               "source_unchanged": before == after, "tests": TESTS, "results": results,
               "helper_sha256": sha(Path(__file__).read_bytes()),
               "original_review_scripts_imported": False}
    (args.output / "result.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if before == after and results[0]["verdict"] == "BASELINE_PASSED" and all(
        item["verdict"] == "KILLED" for item in results[1:]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
