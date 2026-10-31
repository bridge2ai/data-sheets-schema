#!/usr/bin/env python3
"""Causal/mutation checks for PR #5094 F1–F6/F9, 2026-10-28.

Inputs: the two current production modules, pinned local git baseline, and
tests/test_pr5094_round2.py. Outputs: compact JSON results. Runs one pytest
process at a time with provider keys unset; restores source bytes in finally.
Only this worktree's modules and .codex-pt are temporarily modified. No network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
RAT = "src/data_sheets_schema/report_audit_totals.py"
API = "src/data_sheets_schema/api_runner.py"
TEST = "tests/test_pr5094_round2.py"
BASE = "8f181a68699066d5fab847a46d5c2368aedf1e95"

# Each row removes or reverses one decision, then runs the causal guard.
MUTATIONS = {
    "F1_M17_full_record_total": (RAT,
        r'(?:the\s+)?core\s+record\b",', r'(?:the\s+)?(?:core|full)\s+record\b",',
        "test_full_record_corpus_total"),
    "F1_full_record_no_total": (RAT,
        'or re.search(r"\\bcore\\s+record\\b", clause, re.I)',
        'or re.search(r"\\b(?:core|full)\\s+record\\b", clause, re.I)',
        "test_full_record_is_global_in_each_reader"),
    "F1_full_record_label": (RAT,
        'or re.search(r"\\bcore\\s+record\\b", text, re.I)',
        'or re.search(r"\\b(?:core|full)\\s+record\\b", text, re.I)',
        "test_full_record_is_global_in_each_reader"),
    "F1_fallback_produced": (RAT, r'|no\s+changes?', '', "test_disposition_fallback_is_not_a_total"),
    "F1_fallback_resulted": (RAT, r'|resulted\s+in', '', "test_disposition_fallback_is_not_a_total"),
    "F2_first_severity_count": (RAT, 'first.setdefault(sev, count)', 'first[sev] = count',
        "test_later_subset_counts_do_not_add_mismatches"),
    "F2_disposition_scope": (RAT, r'|still\s+open|after\s+reconciliation', '',
        "test_later_subset_counts_do_not_add_mismatches"),
    "F3_continuation": (RAT, '    leading = line.lstrip', '    return False\n    leading = line.lstrip',
        "test_global_breakdown_after_wrap_or_intro or test_corpus_wrapped_low_mismatch_is_kept"),
    "F3_including": (RAT, 'subset[0].lower() == "including"', 'False',
        "test_global_breakdown_after_wrap_or_intro"),
    "F3_parenthetical": (RAT, 'if SUBSET_CLAUSE_RE.search(m[0]) else m[0]', 'if False else m[0]',
        "test_global_breakdown_after_wrap_or_intro or test_later_subset_counts_do_not_add_mismatches"),
    "F3_abbreviation": (RAT, r'(?<!e\.g)(?<!i\.e)', '', "test_global_breakdown_after_wrap_or_intro"),
    "F4_heading_scope": (RAT, 'contexts = [text for _, text in headings] + [before[line_start:]]',
        'contexts = [before[line_start:]]', "test_heading_or_paragraph_scoped_summary"),
    "F4_paragraph_scope": (RAT, '        contexts.append(previous)', '        pass',
        "test_heading_or_paragraph_scoped_summary"),
    "F5_attested_latest": (API, 'audit_source = snapshot[1].decode("utf-8")',
        'audit_source = _intermediate_dir(spec) / f"{spec.project}_audit.json"',
        "test_resume_reads_attested_second_snapshot"),
    "F5_legacy_ambiguity": (API, 'if len(candidates) == 1:', 'if candidates:',
        "test_legacy_ambiguous_snapshots_preserve_checked_prior"),
    "F6_M9_two_no_total_clauses": (RAT, '                add_summary(clause)\n',
        '                add_summary(clause)\n                break\n', "test_no_total_compares_two_global_clauses"),
    "F6_M14_noninteger_version": (API, 'isinstance(prior, dict) and type(prior.get("instrument_version")) is int',
        'isinstance(prior, dict)', "test_resume_recomputes_noninteger_instrument"),
    "F6_M18_newer_version": (API,
        '    if (isinstance(prior, dict) and type(prior.get("instrument_version")) is int\n'
        '            and prior["instrument_version"] > INSTRUMENT_VERSION):\n        return prior\n', '',
        "test_resume_keeps_newer_instrument_with_sources_present"),
    "F9_digit_bound": (RAT, '        if len(s) > 9:\n            return None\n', '',
        "test_unparseable_or_oversized_counts_are_bounded"),
    "F9_nondecimal_digit": (RAT, '        except ValueError:', '        except TypeError:',
        "test_unparseable_or_oversized_counts_are_bounded"),
}


def pytest_run(selector=None):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    for key in ("ANTHROPIC_API_KEY", "CBORG_API_KEY", "OPENAI_API_KEY"):
        env.pop(key, None)
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=",
               f"--basetemp={ROOT / '.codex-pt'}", TEST]
    if selector:
        command.extend(["-k", selector])
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.stdout
    summary = next((line for line in reversed(output.splitlines()) if re.search(r"\d+ (?:failed|passed)", line)), output[-500:])
    return {"exit_code": result.returncode, "summary": summary,
            "failed_tests": [line for line in output.splitlines() if line.startswith("FAILED ")],
            "command": command}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    originals = {name: (ROOT / name).read_bytes() for name in (RAT, API)}
    results = {"baseline": BASE, "source_sha256": {name: hashlib.sha256(raw).hexdigest() for name, raw in originals.items()}}
    try:
        for name in originals:
            (ROOT / name).write_bytes(subprocess.check_output(
                ["git", "--no-replace-objects", "show", f"{BASE}:{name}"], cwd=ROOT,
                env={**os.environ, "GIT_NO_LAZY_FETCH": "1"}))
        results["before"] = pytest_run()
    finally:
        for name, raw in originals.items():
            (ROOT / name).write_bytes(raw)
    results["after"] = pytest_run()
    assert results["before"]["exit_code"] == 1 and results["after"]["exit_code"] == 0, results
    results["mutations"] = {}
    for name, (relative, old, new, selector) in MUTATIONS.items():
        text = originals[relative].decode()
        assert text.count(old) == 1, (name, text.count(old))
        try:
            (ROOT / relative).write_text(text.replace(old, new))
            result = pytest_run(selector)
            results["mutations"][name] = result
            print(name + ": " + result["summary"], flush=True)
        finally:
            (ROOT / relative).write_bytes(originals[relative])
    # All five unchecked exits must supply both diagnostic fields.
    source = originals[RAT].decode()
    pattern = re.compile(r'^ +"stated_severity_summaries": \[\],\n +"stated_severity_counts": \{\},\n', re.M)
    matches = list(pattern.finditer(source))
    assert len(matches) == 5
    for index, match in enumerate(matches):
        try:
            (ROOT / RAT).write_text(source[:match.start()] + source[match.end():])
            result = pytest_run("test_unchecked_blocks_have_uniform_shape")
            name = f"F9_shape_exit_{index + 1}"
            results["mutations"][name] = result
            print(name + ": " + result["summary"], flush=True)
        finally:
            (ROOT / RAT).write_bytes(originals[RAT])
    assert all((ROOT / name).read_bytes() == raw for name, raw in originals.items())
    args.output.write_text(json.dumps(results, indent=2) + "\n")
    assert all(result["exit_code"] == 1 and result["failed_tests"] for result in results["mutations"].values()), results


if __name__ == "__main__":
    main()
