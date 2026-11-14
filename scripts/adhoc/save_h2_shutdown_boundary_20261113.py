#!/usr/bin/env python3
"""Retain static shutdown-lifetime finding for H2 issue 6200, 2026-11-13.
Inputs: source/AST, Git blame and saved preload JUnit. Outputs: scratch finding
and bounded handoff-producer addition. No project execution or active-run reads.
"""
import ast
import json
from pathlib import Path
import subprocess
import report_h2_resume_20261113 as report

TARGETS = {
    'notes/matched_cborg_2026-09-13/native_controls/native_control.py': ['close'],
    'notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py': ['_close_responsive_control'],
    'src/data_sheets_schema/native_shared_controller_orchestration.py': ['observe', 'report', '_report_and_close'],
    'src/data_sheets_schema/native_shared_callback_orchestration.py': ['classify'],
}


def main():
    sources = []
    for relative, names in TARGETS.items():
        path = report.ROOT / relative
        raw = path.read_text()
        functions = []
        for node in ast.walk(ast.parse(raw)):
            if isinstance(node, ast.FunctionDef) and node.name in names:
                command = ['git', 'blame', '-L', str(node.lineno) + ',' + str(node.end_lineno), '--', relative]
                functions.append({'name': node.name, 'line': node.lineno,
                    'source': ast.get_source_segment(raw, node), 'blame_command': command,
                    'blame': subprocess.check_output(command, cwd=report.ROOT, text=True)})
        assert {row['name'] for row in functions} == set(names)
        sources.append({'evidence': report.pin(path), 'functions': functions})
    engine = report.ROOT / 'src/data_sheets_schema/native_execution_orchestration.py'
    lines = engine.read_text().splitlines()
    calls = [{'line': i, 'text': line.strip()} for i, line in enumerate(lines, 1)
             if 'adapter.report(complete=True)' in line]
    assert calls
    cohort = report.load_cohort(report.SCRATCH, preload=True)
    proof = report.test_proof([cohort], 'test_main_thread_teardown_waits_for_active_historical_worker', 1)
    assert proof['passed']
    result = {'finding_id': 'H2-RESUME-SHUTDOWN-F1', 'status': 'design-decision-required',
        'answer': 'Bounded transport cleanup does not bound subsequent callback finalization.',
        'established': 'NativeControl.close joins the non-daemon worker only for its registered join interval and freezes incomplete shutdown. The transport preserves that state. Orchestration later calls adapter.report(complete=True), which acquires without a timeout the same lock held by observe and classifier work. The lock predates H2, as the saved Git blame shows.',
        'causal_limit': 'This is a possible route to prolonged waiting after transport cleanup. It does not identify the slow operation or prove the G3b hang used that route.',
        'recommendation': 'Preserve callback ownership, fresh verification and the lock. A bounded full shutdown needs cooperative cancellation or process isolation with an explicit lifetime and evidence contract; pinned transport changes require a review-only proposal.',
        'sources': sources, 'finalization_call': {'evidence': report.pin(engine), 'excerpts': calls},
        'lifetime_regression': proof,
        'lead_filing_needed': True, 'github_issue_number': None,
        'filing_reason': 'Helper GitHub writes are prohibited; the lead must file this review finding.'}
    destination = report.SCRATCH / 'callback-shutdown-boundary.json'
    with destination.open('x') as stream:
        stream.write((json.dumps(result, indent=2) + '\n').replace(chr(64), '\\u0040'))
    path = Path(report.__file__)
    raw = path.read_text()
    needle = "    g3b = read_json(g3b_path)"
    assert needle in raw and 'shutdown_boundary_path =' not in raw
    raw = raw.replace(needle, needle + "\n    shutdown_boundary_path = SCRATCH / 'callback-shutdown-boundary.json'\n    shutdown_boundary = read_json(shutdown_boundary_path)", 1)
    needle = "        'g3b_comparison': g3b, 'g3b_comparison_evidence': pin(g3b_path),"
    assert needle in raw
    raw = raw.replace(needle, needle + "\n        'callback_shutdown_boundary': shutdown_boundary,\n        'callback_shutdown_boundary_evidence': pin(shutdown_boundary_path),", 1)
    needle = "    lines += ['', 'Saved verification cohorts:', '']"
    assert needle in raw
    raw = raw.replace(needle, '''    lines += ['', 'H2-RESUME-SHUTDOWN-F1: ' + shutdown_boundary['answer'],
        shutdown_boundary['established'], shutdown_boundary['causal_limit'], shutdown_boundary['recommendation'],
        'Evidence: `' + str(shutdown_boundary_path) + '`. The existing lifetime regression passed in the preload suite. Lead filing remains needed; no production repair is claimed.']
''' + needle, 1)
    path.write_text(raw)
    print(json.dumps(report.pin(destination)))


if __name__ == '__main__':
    main()
