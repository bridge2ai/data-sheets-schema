# Purpose: rerun all 90 named review mutations against frozen round-3 source.
# Inputs: source checkout, interpreter, and a fresh disjoint evidence directory.
# Outputs: source-bound baseline/mutant logs, XML, exact edits and verdict receipt.
# Serves: issues 6385 and 6398 to 6401, 2026-11-26. Catalog A/B/C copied from the
# read-only mutation_harness_r2.py; that script is never imported or executed.
import argparse
from collections import Counter
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

MATH = "src/data_sheets_schema/_score_selection_math.py"
READER = "src/data_sheets_schema/score_selection.py"
CLI = "src/data_sheets_schema/cli/runs.py"
TESTS = ["tests/test_score_selection_math.py", "tests/test_score_selection_evidence.py",
         "tests/test_cli/test_score_selection.py", "tests/test_cli/test_score_selection_integration.py"]
BOUND_FILES = (MATH, READER, CLI, "tests/score_selection_cases.py", *TESTS)

A = [
    ("M01 accept gap equal to T (<= becomes <)", MATH, [('elif gap <= record["T"]:', 'elif gap < record["T"]:')]),
    ("M02 population SD in the pool (df = n)", MATH, [("degrees = sum(len(values) - 1 for values in usable)", "degrees = sum(len(values) for values in usable)")]),
    ("M03 drop the per-rubric no-reversal condition", MATH, [("    elif reversals:", "    elif False:")]),
    ("M04 let invalid replicates rank", MATH, [('eligible = sorted((row for row in summaries if row["validity"] == "valid"), key=_coverage_key)',
                                               "eligible = sorted((row for row in summaries), key=_coverage_key)")]),
    ("M05 two scorings are enough (count guard alone)", MATH, [('if len(row["paired_numbers"]) < 3:', 'if len(row["paired_numbers"]) < 2:')]),
    ("M05b two scorings are enough (count guard, exact-123 guard and absent-cell synthesis)", MATH, [
        ('if len(row["paired_numbers"]) < 3:', 'if len(row["paired_numbers"]) < 2:'),
        ('elif len(row["paired_numbers"]) > 3 or row["paired_numbers"] != [1, 2, 3]:', 'elif len(row["paired_numbers"]) > 3:'),
        ("        for number in (1, 2, 3):\n            if number not in observed:", "        for number in (1, 2):\n            if number not in observed:")]),
    ("M06 threshold one standard error", MATH, [('record["T"] = 2 * s * math.sqrt(2 / 3)', 'record["T"] = 1 * s * math.sqrt(2 / 3)')]),
    ("M07 pair by position, not by scoring number", MATH, [
        ("    paired = [(measured[RUBRICS[0]][number] + measured[RUBRICS[1]][number]) / 2\n              for number in paired_numbers]",
         "    paired = [(a + b) / 2 for a, b in zip(measured[RUBRICS[0]].values(), measured[RUBRICS[1]].values())]")]),
    ("M08 reversal judged on scoring 1 alone", MATH, [('if highest["rubrics"][rubric]["mean"] < current["rubrics"][rubric]["mean"]]',
                                                      'if highest["_values"][rubric][1] < current["_values"][rubric][1]]')]),
    ("M09 equal rubric means count as a reversal", MATH, [('if highest["rubrics"][rubric]["mean"] < current["rubrics"][rubric]["mean"]]',
                                                          'if highest["rubrics"][rubric]["mean"] <= current["rubrics"][rubric]["mean"]]')]),
    ("M10 a not-measured cell is read as zero", MATH, [('                    issue = "not measured: " + str(cell.get("reason") or "no accepted measurement")',
                                                       "                    values[number] = 0.0")]),
    ("M11 candidate spread is population SD", MATH, [('"spread": stdev(values) if len(values) >= 2 else None',
                                                     '"spread": __import__("statistics").pstdev(values) if len(values) >= 2 else None')]),
    ("M12 coverage key ignores coverage (label only)", MATH, [('return (-(slots if _number(slots) else -1), row["label"])', 'return (0, row["label"])')]),
    ("M13 pooled instrument mismatch not checked in decide", MATH, [('if pooled.get("instrument_id") != instrument_id:', "if False:")]),
    ("M14 gap and T rounded to one decimal before comparison", MATH, [
        ('    record.update(highest_mean_pick=highest["label"], gap=gap)',
         '    gap = round(gap, 1); record["T"] = round(record["T"], 1)\n    record.update(highest_mean_pick=highest["label"], gap=gap)')]),
    ("M15 pooled s from rubric10 values only", MATH, [('    result = _pool([row["_paired_values"] for row in summaries])',
                                                      '    result = _pool([list(row["_values"]["rubric10"].values()) for row in summaries])')]),
    ("M16 scoring score weighted 25/75", MATH, [("(measured[RUBRICS[0]][number] + measured[RUBRICS[1]][number]) / 2",
                                                "(0.25 * measured[RUBRICS[0]][number] + 0.75 * measured[RUBRICS[1]][number])")]),
    ("M17 records with 2 scorings left out of the pool", MATH, [("usable = [values for values in groups if len(values) >= 2]",
                                                                "usable = [values for values in groups if len(values) >= 3]")]),
    ("M18 drift between scorings ignored", MATH, [("        if identities and any(identity != identities[0] for identity in identities[1:]):", "        if False:")]),
    ("M19 highest-mean pick is the lowest mean", MATH, [('highest = min(eligible, key=lambda row: (-row["paired"]["mean"], *_coverage_key(row)))',
                                                        'highest = min(eligible, key=lambda row: (row["paired"]["mean"], *_coverage_key(row)))')]),
    ("E01 published bytes not compared with the receipt hash", READER, [('        _require(_sha(raw) == expected, "published bytes do not match accepted receipt")', "        pass")]),
    ("E02 receipt need not bind its saved plan", READER, [('    _require(receipt.get("plan_sha256") == _sha(json.dumps(plan, sort_keys=True).encode()),\n             "receipt does not bind its saved plan")', "    pass")]),
    ("E03 percentage on the adjusted maximum, equality guard removed (reader and math)", READER, [
        ('points, maximum = score.get("total_points"), score.get("max_points")', 'points, maximum = score.get("total_points"), score.get("adjusted_max_points")'),
        ('                 and maximum == {"rubric10": 50, "rubric20": 88}[family] and adjusted == maximum,', "                 ,")],
     MATH, [('                    elif maximum != FIXED_MAXIMA[rubric]:', "                    elif False:")]),
    ("E04 repeat manifest hashes not compared", READER, [('            _require(value.get("destination_sha256") == value.get("source_output_sha256") == expected,\n                     "repeat publication hash differs")', "            pass")]),
    ("E05 published and validated hashes may differ", READER, [('    _require(receipt.get("output_sha256") == receipt.get("validator_input_sha256"),\n             "published and validated hashes differ")', "    pass")]),
    ("E06 refused receipt of a replacement need not be REFUSED or hash-bound", READER, [('                _require(original["receipt_sha256"] == refused.get("sha256")\n                         and original["receipt"].get("status") == "REFUSED",\n                         "replacement refusal binding differs")', "                pass")]),
    ("E07 published scorer_instrument not checked", READER, [('        _require(value.get("scorer_instrument") == {"id": instrument,\n                 "prompt_sha256": measured["prompt_sha256"], "runner_sha256": measured["runner_sha256"]},\n                 "published instrument differs")', "        pass")]),
    ("E08 exit codes and auth cleanup not checked", READER, [('    _require(type(receipt.get("codex_exit")) is int and receipt["codex_exit"] == 0\n             and type(receipt.get("validator_exit")) is int and receipt["validator_exit"] == 0\n             and receipt.get("auth_copy_absent") is True, "acceptance or cleanup is unproven")', "    pass")]),
    ("E09 composed definition pin not checked", READER, [('    _require(provenance.get("composed_sha256") == result["definition_sha256"],\n             "composed definition is not pinned")', "    pass")]),
    ("E10 plan metadata and plan inputs may disagree", READER, [('        _require(digest == _mapping(inputs.get(input_name)).get("sha256"), "plan input and metadata differ")', "        pass")]),
    ("E11 scoring 1 accepts a run that a repeat manifest references", READER, [
        ('        choices = [entry for entry in matches if entry["plan_path"] not in referenced\n                   and entry["receipt"].get("status") == "VALIDATED_AND_PUBLISHED"]',
         '        choices = [entry for entry in matches if entry["receipt"].get("status") == "VALIDATED_AND_PUBLISHED"][:1]')]),
    ("E12 record bytes not compared with the scored record hash", READER, [('    _require(result["record_sha256"] == record_sha, "scoring names changed record bytes")', "    pass")]),
    ("E13 receipt status not required in the acceptance check", READER, [('    _require(receipt.get("status") == "VALIDATED_AND_PUBLISHED", "scoring receipt is not accepted")', "    pass")]),
    ("E14 repeat manifest status and copy validator exit not checked", READER, [('            _require(value.get("status") == "EXPORTED_VALIDATED_REPEAT"\n                     and value.get("copy_validator_exit") == 0, "repeat export is not accepted")', "            pass")]),
    ("E15 published identity fields not compared with the plan", READER, [('            _require(value.get(key) == plan["identity"].get(key), "published scoring identity differs")', "            pass")]),
    ("E16 published deterministic fields not compared with the plan", READER, [('        _published_deterministic_fields(value, plan["deterministic_fields"])', "        pass")]),
    ("E17 output schema binding optional", READER, [('    result["schema_sha256"] = _digest(_mapping(inputs.get("output-schema.json")).get("sha256"))',
                                                    '    result["schema_sha256"] = _mapping(inputs.get("output-schema.json")).get("sha256") or ("0" * 64)')]),
    ("E18 duplicate repeat exports tolerated", READER, [("        if len(exports) != 1:", "        if len(exports) < 1:")]),
    ("E19 repeat manifest need not bind plan and receipt hashes", READER, [('                _require(value.get("actual_" + kind) == entry[kind + "_path"]\n                         and value.get("actual_" + kind + "_sha256") == entry[kind + "_sha256"],\n                         "repeat metadata binding differs")', "                pass")]),
]

B = [
    ("N01 complete-series reasons not carried into decide", MATH, [('    problems.extend(pooled.get("fallback_reasons") or [])', "    pass")]),
    ("N02 pooled_variation does not report record problems as fallback reasons", MATH, [
        ("    reasons = incompatible + [f\"{row['project']}/{row['label']}: {problem}\"\n                              for row in summaries for problem in row[\"problems\"]]", "    reasons = list(incompatible)")]),
    ("N03 fixed-maximum check removed (math only)", MATH, [("                    elif maximum != FIXED_MAXIMA[rubric]:", "                    elif False:")]),
    ("N04 adjusted-equals-fixed check removed (math only)", MATH, [('                    elif cell.get("adjusted_max_points") != maximum:', "                    elif False:")]),
    ("N05 adjusted-equals-fixed check removed (reader only)", READER, [('                 and maximum == {"rubric10": 50, "rubric20": 88}[family] and adjusted == maximum,',
                                                                        '                 and maximum == {"rubric10": 50, "rubric20": 88}[family],')]),
    ("N06 adjusted-equals-fixed check removed (reader and math)", READER, [('                 and maximum == {"rubric10": 50, "rubric20": 88}[family] and adjusted == maximum,',
                                                                            '                 and maximum == {"rubric10": 50, "rubric20": 88}[family],')],
     MATH, [('                    elif cell.get("adjusted_max_points") != maximum:', "                    elif False:")]),
    ("N07 one-context-per-project check removed", MATH, [("        if len(contexts) > 1:", "        if False:")]),
    ("N08 pinned identity keys not required", MATH, [("    if missing:\n        return \"missing or invalid pinned identity: \"", "    if False:\n        return \"missing or invalid pinned identity: \"")]),
    ("N09 zero pooled s accepted (decide only)", MATH, [("    if not (_number(s) and s > 0 and type(degrees) is int and degrees > 0):", "    if not (_number(s) and s >= 0 and type(degrees) is int and degrees > 0):")]),
    ("N10 zero pooled s accepted (decide and pooled_variation)", MATH, [
        ("    if not (_number(s) and s > 0 and type(degrees) is int and degrees > 0):", "    if not (_number(s) and s >= 0 and type(degrees) is int and degrees > 0):"),
        ('    if result["s"] == 0:', "    if False:")]),
    ("N11 pool of one record accepted (decide and pooled_variation)", MATH, [
        ('(type(pooled.get("records")) is not int or pooled["records"] < 2)', '(type(pooled.get("records")) is not int or pooled["records"] < 1)'),
        ('    if result["records"] < 2 and not incompatible:', '    if result["records"] < 1 and not incompatible:')]),
    ("N12 fourth scoring ignored (all three places)", MATH, [
        ("        if any(type(number) is int and number > 3 for number in observed):", "        if False:"),
        ('        elif len(row["paired_numbers"]) > 3 or row["paired_numbers"] != [1, 2, 3]:', "        elif False:")],
     READER, [("                if publication.exists() or publication.is_symlink():", "                if False:")]),
    ("N13 absolute paths not scrubbed from reasons", MATH, [('    return re.sub(r"(?<![\\w:./\\\\])(?:[A-Za-z]:[\\\\/]|\\\\\\\\|/)[^\\s\\"\'<>;,]+", "[external path]", str(value))', "    return str(value)")]),
    ("N14 invalid current policy pick not a fallback reason", MATH, [('    if current["validity"] != "valid":', "    if False:")]),
    ("N15 tie for the highest mean not recorded", MATH, [("    if len(tied) > 1:", "    if False:")]),
    ("N16 instrument drift across records not a problem", MATH, [("            if values and any(value is None or value != values[0] for value in values):", "            if False:")]),
    ("N17 pool not suppressed on incompatible inputs", MATH, [("    if incompatible:\n        result = _pool([])", "    if False:\n        result = _pool([])")]),
    ("N18 missing planned metadata key accepted", READER, [("                _require(name in actual and actual[name] == expected,", "                _require(name not in actual or actual[name] == expected,")]),
    ("N19 changed planned metadata value accepted", READER, [("                _require(name in actual and actual[name] == expected,", "                _require(name in actual,")]),
    ("N20 extra published metadata keys rejected again (exact equality)", READER, [
        ("            for name, expected in expected_value.items():\n                _require(name in actual and actual[name] == expected,\n                         \"published measured-input metadata differs: \" + name)",
         "            _require(actual == expected_value, \"published measured-input metadata differs\")")]),
    ("N21 other planned blocks (scope, context) not compared", READER, [('            _require(value.get(key) == expected_value,\n                     "published measured-input block differs: " + key)', "            pass")]),
    ("N22 undeclared refusal: per-refusal declaration check removed", READER, [("                if len(declarations) != 1:", "                if False:")]),
    ("N23 undeclared refusal: count check removed", READER, [('            if len(refused_matches) > sum(cell["status"] == "measured" and cell["attempt"] == 2 for cell in cells):', "            if False:")]),
    ("N24 undeclared refusal: both checks removed", READER, [("                if len(declarations) != 1:", "                if False:"),
                                                              ('            if len(refused_matches) > sum(cell["status"] == "measured" and cell["attempt"] == 2 for cell in cells):', "            if False:")]),
    ("N25 refusals matched with the accepted-run identity test (needs plan.instrument)", READER, [
        ("                               if _refusal_identity_matches(entry[\"plan\"], project, method, label, family, instrument_id)",
         "                               if _identity_matches(entry[\"plan\"], project, method, label, family, instrument_id)")]),
    ("N26 baseline plan/receipt binding ignored", READER, [("        if bindings:", "        if False:")]),
    ("N27 symlinked receipt root accepted", READER, [("        if any(part.is_symlink() for part in (root, *root.parents)):", "        if False:")]),
    ("N28 evidence index issues not carried to rows", READER, [
        ('               "eligibility_problems": ([record_issue] if record_issue else []) + index["issues"],', '               "eligibility_problems": ([record_issue] if record_issue else []),'),
        ('        row["evidence_issues"] = index["issues"] + ([record_issue] if record_issue else [])', '        row["evidence_issues"] = ([record_issue] if record_issue else [])')]),
    ("N29 incomplete record keeps a slot count", READER, [
        ('                slots = len(loaded) if candidate.get("slots") is not None and candidate["validity"] != "incomplete" else None', "                slots = len(loaded)")]),
    ("N30 publication path left absolute", READER, [('                    cell["publication"] = str(Path(cell["path"]).relative_to(root))', '                    cell["publication"] = str(Path(cell["path"]))')]),
    ("N31 relocated receipt root not reported at index time", READER, [('                if Path(plan.get("run_directory", "")) != directory:', "                if False:")]),
]

C = [
    ("C01 execute under the score policy needs no owner authorization", CLI, [("    if score_policy and execute and authorization is None:", "    if False:")]),
    ("C02 whitespace-only authorization accepted", CLI, [("    if authorization is not None and (not isinstance(authorization, str) or not authorization.strip()):",
                                                         "    if authorization is not None and (not isinstance(authorization, str) or not authorization):")]),
    ("C03 absolute path accepted as authorization text", CLI, [("    if authorization is not None:\n        try:\n            _require_portable_owner_text(authorization)", "    if False:\n        try:\n            _require_portable_owner_text(authorization)")]),
    ("C04 replica-like suffix labels admitted under the score policy", CLI, [("    if not score_policy:\n        return labels\n    from data_sheets_schema.runs import REPLICATE_RE", "    if True:\n        return labels\n    from data_sheets_schema.runs import REPLICATE_RE")]),
    ("C05 policy pick not passed to decide", CLI, [("decision = decide(table, variation, score_instrument, policy_pick=winner[0])", "decision = decide(table, variation, score_instrument)")]),
    ("C06 series projects not discovered through retained plans", CLI, [("            projects.add(name)\n            directory = base / label", "            directory = base / label")]),
    ("C07 other projects: rows only for records that exist on disk", CLI, [
        ('                     "validity": "not measured", "slots": None} for directory in directories]',
         '                     "validity": "not measured", "slots": None} for directory in directories if (directory / f"{name}_d4d.yaml").is_file()]')]),
    ("C08 criterion does not say which rule decided", CLI, [('    criterion += "; score_gap_v1 decision: " + score_record["rule"]', '    criterion += "; score_gap_v1 under the registered score selection policy"')]),
    ("C09 owner ruling slot not checked against the evidence", CLI, [('        if row["slot"] not in available[row["label"]]:', "        if False:")]),
    ("C10 score pick ignored: the coverage pick is always marked", CLI, [('    winner = next(c for c in contenders if c[0] == decision["selected"])', "    pass")]),
    ("C11 margin recomputed for the score winner", CLI, [
        ('    winner = next(c for c in contenders if c[0] == decision["selected"])',
         '    winner = next(c for c in contenders if c[0] == decision["selected"])\n    runner_up = next((c for c in contenders if c[0] != winner[0]), None)\n    margin = winner[3] - runner_up[3] if runner_up else None')]),
    ("C12 owner authorization not recorded in the block", CLI, [('        if authorization is not None:\n            score_record["owner_authorization"] = authorization', "        pass")]),
    ("C13 owner rulings not printed", CLI, [('    for ruling in score_record.get("owner_rulings", []):', "    for ruling in []:")]),
    ("C14 unreadable candidate record raises under the score policy", CLI, [("        if not score_policy:\n            raise\n        return None", "        raise")]),
    ("C15 score_policy block not written to the canonical block", CLI, [("    if score_record is not None:\n        canonical[\"score_policy\"] = score_record\n    return canonical", "    return canonical")]),
    ("C16 default dry-run message changed", CLI, [('        return "\\nDry run. Re-run with --execute to record the choice."', '        return "\\nDry run. Re-run with --execute to record the choice"')]),
    ("C17 default path: coverage runner-up margin off by one", CLI, [("    margin = winner[3] - runner_up[3] if runner_up else None\n    if not score_policy:", "    margin = winner[3] - runner_up[3] + 1 if runner_up else None\n    if not score_policy:")]),
    ("C18 Series variation not printed by select", CLI, [('    _score_report("Series variation", variation)\n    _score_report("Score policy", score_record)', '    _score_report("Score policy", score_record)')]),
    ("C19 score options allowed on the default route", CLI, [("    if (score_receipts or score_owner_rulings or authorization is not None) and not score_policy:", "    if False:")]),
    ("C20 score-variation does not turn reader errors into a clean message", CLI, [
        ("        table, variation = _score_selection_context(method, config, score_instrument, score_receipts)\n    except (ValueError, OSError) as error:",
         "        table, variation = _score_selection_context(method, config, score_instrument, score_receipts)\n    except (OSError,) as error:")]),
]

RUNNER = r'''
import importlib, importlib.util, json, sys
spec_list = json.loads(sys.argv[1])
import data_sheets_schema
order = {"_score_selection_math.py": 0, "score_selection.py": 1, "runs.py": 2}
spec_list.sort(key=lambda item: order[item[0]])
for target, source_path, edits in spec_list:
    text = open(source_path, encoding="utf-8").read()
    for old, new in edits:
        assert text.count(old) == 1, ("mutation site not unique", target, text.count(old), old[:70])
        text = text.replace(old, new)
    name = {"_score_selection_math.py": "data_sheets_schema._score_selection_math",
            "score_selection.py": "data_sheets_schema.score_selection",
            "runs.py": "data_sheets_schema.cli.runs"}[target]
    parent_name, leaf = name.rsplit(".", 1)
    if target == "runs.py":
        importlib.import_module(name)          # let the package finish importing the real one first
    parent = importlib.import_module(parent_name)
    spec = importlib.util.spec_from_loader(name, loader=None, origin=source_path)
    module = importlib.util.module_from_spec(spec)
    module.__file__ = source_path
    sys.modules[name] = module
    exec(compile(text, source_path + " (mutant)", "exec"), module.__dict__)
    setattr(parent, leaf, module)
import pytest
sys.exit(pytest.main(sys.argv[2:]))
'''


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git_head(source):
    return subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True, timeout=30).stdout.strip()


def source_snapshot(source):
    return {relative: sha((source / relative).read_bytes()) for relative in BOUND_FILES}


def adapted_mutation(label, pairs, sources):
    """Keep reviewed IDs and record any semantic resiting explicitly."""
    ident = label.split()[0]
    reader_equality = (
        '                 and maximum > 0 and adjusted == maximum,',
        '                 and maximum > 0,')
    math_equality = [
        ('                    elif (not _number(cell.get("adjusted_max_points"))\n'
         '                          or cell["adjusted_max_points"] != maximum):',
         '                    elif False:'),
        ('                if not _number(adjusted) or adjusted != maximum:', '                if False:'),
    ]
    maximum_uniformity = ('        if len(values) > 1:', '        if False:')
    adaptations = {
        "E03": ([READER, [
            ('points, maximum = score.get("total_points"), score.get("max_points")',
             'points, maximum = score.get("total_points"), score.get("adjusted_max_points")'),
            reader_equality], MATH, [maximum_uniformity]],
            "Use the adjusted denominator and remove reader equality plus the new series-wide maximum-uniformity check. The old 50/88 constant check was replaced by the authorized dynamic per-rubric maximum contract."),
        "N03": ([MATH, [maximum_uniformity]],
            "The fixed 50/88 restriction is now intentionally absent; mutate its replacement requirement that measured cells share one maximum per rubric."),
        "N04": ([MATH, math_equality],
            "Remove adjusted-equals-maximum checks at both the cell summary and the new series-wide diagnostic, preserving the reviewed math-only equality fault."),
        "N05": ([READER, [reader_equality]],
            "Remove adjusted-equals-maximum from the dynamic positive maximum guard, preserving positivity."),
        "N06": ([READER, [reader_equality], MATH, math_equality],
            "Remove reader equality and both math equality sites; dynamic maximum consistency otherwise remains."),
        "N13": ([MATH, [
            ('    text, offset = str(value), 0', '    return str(value)\n    text, offset = str(value), 0')]],
            "Bypass the rewritten general path-prefix guard; the removed regexp is no longer the source implementation. The separate bounded raw-refusal reader remains an independent guard."),
        "C06": ([CLI, [
            ('            discovered.add((name, label))\n            directory = base / label',
             '            directory = base / label')]],
            "Retained plans now add discovered project/label pairs before the roster union. Remove that discovery contribution, leaving label discovery unchanged."),
        "C19": ([CLI, [
            ('    if (score_receipts or score_owner_rulings or authorization is not None or series_projects) and not score_policy:',
             '    if False:')]],
            "The score-option guard now also names series_projects; remove the complete current guard."),
        "C20": ([CLI, [
            ('        table, variation = _score_selection_context(method, config, score_instrument, score_receipts,\n'
             '                                                     series_projects=score_series_project)\n'
             '    except (ValueError, OSError) as error:',
             '        table, variation = _score_selection_context(method, config, score_instrument, score_receipts,\n'
             '                                                     series_projects=score_series_project)\n'
             '    except (OSError,) as error:')]],
            "Resite the same ValueError-catching omission after the new explicit-roster argument."),
    }
    if ident in adaptations:
        replacement, reason = adaptations[ident]
        return replacement, [reason]
    return pairs, []


def prepare(row, sources):
    label, *reviewed_pairs = row
    pairs, adaptations = adapted_mutation(label, reviewed_pairs, sources)
    spec, errors = [], []
    for relative, edits in zip(pairs[0::2], pairs[1::2], strict=True):
        text = sources[relative]
        for old, new in edits:
            matches = text.count(old)
            if matches != 1:
                errors.append({"module": relative, "old": old, "matches": matches})
                break
            text = text.replace(old, new)
        spec.append({"module": relative, "edits": edits, "mutated_sha256": sha(text.encode())})
    return {"id": label.split()[0], "description": label,
            "reviewed_pairs": reviewed_pairs, "adaptations": adaptations,
            "specification": spec, "site_errors": errors}


def run_one(args, item):
    result = dict(item)
    if item["site_errors"]:
        return dict(result, verdict="SITE_DRIFT")
    ident = item["id"]
    spec = [(Path(part["module"]).name, str(args.source / part["module"]), part["edits"])
            for part in item["specification"]]
    env = dict(os.environ, PYTHONPATH=str(args.source / "src") + os.pathsep + str(args.source),
               PYTHONDONTWRITEBYTECODE="1")
    command = [str(args.python), "-B", "-c", RUNNER, json.dumps(spec), *TESTS,
               "-q", "-p", "no:cacheprovider", "--no-header", "-o", "addopts=", "-rfE",
               "--basetemp=" + str(args.output / "fixtures" / ident),
               "--junitxml=" + str(args.output / (ident + ".xml"))]
    result.update(argv=command, cwd=str(args.source),
                  environment_overrides={key: env[key] for key in ("PYTHONPATH", "PYTHONDONTWRITEBYTECODE")})
    try:
        done = subprocess.run(command, cwd=args.source, env=env, capture_output=True,
                              text=True, timeout=args.timeout)
    except subprocess.TimeoutExpired as error:
        return dict(result, verdict="HARNESS_TIMEOUT", timeout=args.timeout,
                    timeout_stdout_sha256=sha(error.stdout or b""),
                    timeout_stderr_sha256=sha(error.stderr or b""))
    text = done.stdout + "\n--- stderr ---\n" + done.stderr
    log = args.output / (ident + ".log")
    with log.open("x", encoding="utf-8") as stream:
        stream.write(text)
    failed = [line for line in done.stdout.splitlines() if line.startswith("FAILED")]
    errors = [line for line in done.stdout.splitlines() if line.startswith("ERROR")]
    verdict = "SURVIVED" if done.returncode == 0 else "KILLED" if done.returncode == 1 and failed and not errors else "HARNESS_ERROR"
    if ident == "BASE":
        verdict = "BASELINE_PASSED" if done.returncode == 0 else "BASELINE_FAILED"
    return dict(result, verdict=verdict, returncode=done.returncode, failing_tests=failed,
                collection_errors=errors, log=log.name, log_sha256=sha(text.encode()),
                xml_sha256=sha((args.output / (ident + ".xml")).read_bytes())
                if (args.output / (ident + ".xml")).is_file() else None)


def fresh_output(output, source):
    output = Path(os.path.abspath(output))
    if any(path.is_symlink() for path in (output, *output.parents)) or output.exists():
        raise ValueError("output must be fresh with physical parents")
    source_info = source.stat()
    identity = (source_info.st_dev, source_info.st_ino)
    for parent in output.parents:
        if parent.exists():
            info = parent.stat()
            if (info.st_dev, info.st_ino) == identity:
                raise ValueError("output must be outside source checkout")
    if output in source.parents:
        raise ValueError("output cannot contain the source checkout")
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline source-bound rerun of all 90 review mutations.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--ids", help="Comma-separated IDs; omitted means all 90 reviewed mutations.")
    parser.add_argument("--plan-only", action="store_true", help="Check and record mutation sites without tests.")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args(argv)
    args.source = args.source.resolve(strict=True)
    args.output = fresh_output(args.output, args.source)
    if git_head(args.source) != args.expected_head:
        parser.error("source does not match expected head")
    if os.getpriority(os.PRIO_PROCESS, 0) < 10:
        parser.error("run this offline lane at nice 10 or lower priority")
    before = source_snapshot(args.source)
    sources = {relative: (args.source / relative).read_text() for relative in (MATH, READER, CLI)}
    catalog = A + B + C
    if len(catalog) != 90 or len({row[0].split()[0] for row in catalog}) != 90:
        parser.error("reviewed catalog identity differs")
    selected = set(args.ids.split(",")) if args.ids else None
    if selected and selected - {row[0].split()[0] for row in catalog}:
        parser.error("requested mutation ID is absent from the catalog")
    planned = [prepare(row, sources) for row in catalog if selected is None or row[0].split()[0] in selected]
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "fixtures").mkdir()
    results = []
    if not args.plan_only:
        results.append(run_one(args, {"id": "BASE", "description": "Unmutated control",
                                    "site_errors": [], "specification": []}))
        print("BASE", results[0]["verdict"], flush=True)
        if results[0]["verdict"] == "BASELINE_PASSED":
            for item in planned:
                result = run_one(args, item)
                results.append(result)
                print(result["id"], result["verdict"], flush=True)
    after = source_snapshot(args.source)
    end_head = git_head(args.source)
    receipt = {"source_head": args.expected_head, "finish_head": end_head,
               "mode": "PLAN_ONLY" if args.plan_only else "MUTATION_TESTS",
               "reviewed_catalog_count": len(catalog), "planned": planned, "results": results,
               "before_sha256": before, "after_sha256": after,
               "source_unchanged": before == after and end_head == args.expected_head,
               "actual_nice": os.getpriority(os.PRIO_PROCESS, 0), "tests": TESTS,
               "counts": dict(Counter(item["verdict"] for item in results)),
               "helper_sha256": sha(Path(__file__).read_bytes()),
               "original_review_script_imported_or_executed": False,
               "multi_module_loading": "math before reader before CLI so imported aliases use mutated dependencies"}
    with (args.output / "result.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    if not receipt["source_unchanged"]:
        return 2
    if args.plan_only:
        return 0 if all(not row["site_errors"] for row in planned) else 1
    return 0 if results and results[0]["verdict"] == "BASELINE_PASSED" and all(
        item["verdict"] == "KILLED" for item in results[1:]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
