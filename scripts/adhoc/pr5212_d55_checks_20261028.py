#!/usr/bin/env python3
"""PR #5212/D55, 2026-10-28: serial offline test selection and retained evidence.

Inputs: local checkout and committed exact 29 F2 nodes (originally S-H.log).
Outputs: pytest logs/XML and the selected node IDs in an external evidence dir.
No providers, network, nested worktree, or cache writes are used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil

ROOT = Path(__file__).resolve().parents[2]
REVIEW = Path('/private/tmp/claude-501/d42-review-Uaym')
ROUTING = [f'tests/test_source_heading_runtime_api.py::{name}' for name in (
    'test_actual_sent_routing_counts_usage_and_completed_zero_calls',
    'test_actual_completed_capture_is_portable_and_refuses_changed_bytes',
    'test_actual_regated_report_captured_lineage',
    'test_actual_default_layout_completed_capture',
)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('batch', choices=('baseline', 'required', 'runtime', 'f2', 'routing'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--pin-sources-only', action='store_true')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'production_sources.json').write_text(json.dumps({
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / 'src/data_sheets_schema').rglob('*.py'))}, indent=2, sort_keys=True) + '\n')
    if args.pin_sources_only:
        return 0
    roster = ROOT / 'notes/reviews/pr5212_d55_f2_nodes.txt'
    if roster.exists():
        f2 = roster.read_text().splitlines()
    else:
        f2 = [line.split(' ', 2)[1] for line in (REVIEW / 'S-H.log').read_text().splitlines()
              if line.startswith('FAILED ')]
        assert len(f2) == 29
        roster.write_text('\n'.join(f2) + '\n')
    canary = ['notes/matched_cborg_2026-09-13/test_budgeted_cborg.py::test_real_repair_catch_cannot_allow_a_cheaper_report']
    selections = {
        'baseline': f2 + ROUTING + canary,
        'f2': f2 + canary,
        'routing': ROUTING,
        'runtime': ['tests/test_pr5212_d55_fixes.py', 'tests/test_latch_journal.py',
                    'tests/test_api_latch_guard.py', 'tests/test_download/test_api_runner.py',
                    'tests/test_usage_ledger.py', 'tests/test_receipt_completion_runtime.py',
                    'tests/test_generation_snapshot_ownership.py', 'tests/test_snapshot_attempt_recovery.py',
                    'tests/test_provenance_header.py', *f2, *canary],
        'required': ['tests/test_pr5212_d55_fixes.py', 'tests/test_latch_journal.py', 'tests/test_api_latch_guard.py',
                     'tests/test_d41_request_parity.py', 'tests/test_report_gate.py',
                     *[str(p.relative_to(ROOT)) for p in sorted((ROOT / 'tests').glob('test_unusable_snapshot*.py'))],
                     *[str(p.relative_to(ROOT)) for p in sorted((ROOT / 'tests').rglob('test*provenance*.py'))],
                     *f2, *ROUTING, *canary],
    }
    selected = selections[args.batch]
    (args.out / 'selection.txt').write_text('\n'.join(selected) + '\n')
    env = {k: v for k, v in os.environ.items() if k not in {
        'ANTHROPIC_API_KEY', 'CBORG_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_BASE_URL'}}
    env.update(PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1')
    command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-o', 'addopts=',
               '--basetemp=' + str(Path(env.get('TMPDIR', '/private/tmp')) / 'codex-5212-pt'),
               '--junitxml=' + str(args.out / 'results.xml'), *selected]
    (args.out / 'command.txt').write_text(repr(command) + '\n')
    with (args.out / 'pytest.log').open('w') as log:
        completed = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    basetemp = Path(env.get('TMPDIR', '/private/tmp')) / 'codex-5212-pt'
    for summary in basetemp.glob('test_chorus_shared_v1_exact_ba*/parity/summary.json'):
        if summary.parent.parent.is_symlink():
            continue
        shutil.copytree(summary.parent, args.out / 'parity', dirs_exist_ok=True)
    print('\n'.join((args.out / 'pytest.log').read_text().splitlines()[-45:]))
    return completed.returncode


if __name__ == '__main__':
    raise SystemExit(main())
