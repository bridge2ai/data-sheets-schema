#!/usr/bin/env python3
"""PR #5212/F4/F11, 2026-10-28: run the corrected crash/repeated-gate fixtures.

Input: db88ca68c's gate function or current code. Output: pytest exit/log/XML.
The old function is compiled in memory with current dependencies; no checkout
or protected source is edited, and no API/network calls are made.
"""
import argparse
import ast
import subprocess
import pytest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', action='store_true')
    parser.add_argument('--before-latch', action='store_true')
    args, pytest_args = parser.parse_known_args()
    if args.before:
        from data_sheets_schema import api_runner
        raw = subprocess.check_output(['git', 'show', 'db88ca68c:src/data_sheets_schema/api_runner.py'], text=True)
        node = next(n for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef) and n.name == '_gate_report')
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<db88ca68c _gate_report>', 'exec'), api_runner.__dict__)
    if args.before_latch:
        from data_sheets_schema import latch_journal
        raw = subprocess.check_output(['git', 'show', 'db88ca68c:src/data_sheets_schema/latch_journal.py'], text=True)
        exec(compile(raw, '<db88ca68c latch_journal>', 'exec'), latch_journal.__dict__)
        node = 'tests/test_pr5212_d55_fixes.py::test_interrupted_intent_requires_exact_acknowledgement_and_can_continue'
    else:
        node = 'tests/test_report_gate.py::TestTheRunnerGate::test_regeneration_exhaustion_survives_multiple_rechecks_and_unusable_answers'
    return pytest.main([*pytest_args, node])


if __name__ == '__main__':
    raise SystemExit(main())
