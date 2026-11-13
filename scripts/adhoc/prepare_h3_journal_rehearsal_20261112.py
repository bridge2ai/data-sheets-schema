"""Adapt existing isolated helpers for #5992/#5993 and their carry, 2026-11-12.

Inputs: owned hardening runner and failure-branch composition/restore recipes.
Outputs: owned runner accepting only the three assigned trees, scratch recipes.
No model/native/network call and no production state creation.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = root.parent / 'codex-native-failure-record-20261112/scripts/adhoc'
runner = (root / 'scripts/adhoc/run_h3_hardening_tests_20261112.py').read_text()
runner = runner.replace('if SCRIPT_ROOT.name != "codex-native-launch-sequence-hardening-20261112":',
    'if SCRIPT_ROOT.name not in ("codex-native-launch-sequence-hardening-20261112",\n'
    '        "codex-native-failure-record-20261112", "codex-native-incomplete-capture-retention-20261112"):')
runner = runner.replace('"-p", "xdist.plugin", "-n", str(args.workers)',
                        '"-p", "xdist.plugin", "-n", str(args.workers), "--dist=worksteal"')
(root / 'scripts/adhoc/run_h3_journal_tests_20261112.py').write_text(runner)
for old, new in (('compose_h3_failure_20261112.py', 'compose_h3_journal_20261112.py'),
                 ('restore_h3_failure_configs_20261112.py', 'restore_h3_journal_configs_20261112.py')):
    raw = (source / old).read_text().replace('scratch-h3-failure-record-20261112',
                                            'scratch-h3-launch-hardening-20261112')
    (root / 'scripts/adhoc' / new).write_text(raw)
