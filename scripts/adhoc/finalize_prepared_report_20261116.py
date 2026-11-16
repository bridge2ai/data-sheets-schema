"""Add timeout and rerun evidence to the D156 report, 2026-11-16.

Input/output: report_prepared_worker_20261116.py. One-time provenance edit for
the Claude lead handoff; results remain read from persisted lane artifacts.
"""
from pathlib import Path

path = Path(__file__).with_name('report_prepared_worker_20261116.py')
text = path.read_text()
replacements = [
    ("        ('public-collection', 'public-correction/results/pytest.xml'),",
     "        ('controls-three-worker-canary', 'controls-three-canary/results/native.xml'),\n"
     "        ('controls-three-worker-budget', 'controls-three/results/budget.xml'),\n"
     "        ('controls-three-worker-native', 'controls-three/results/native.xml'),\n"
     "        ('public-collection', 'public-correction/results/pytest.xml'),"),
    ('A separate loopback canary passed with local socket permission and an upstream MockTransport; the full controls-loopback rerun uses that same environment.',
     'A separate loopback canary passed with local socket permission and an upstream MockTransport. The serial controls-loopback rerun reached beyond 85 percent without a reported failure but timed out at 900 seconds; no completed native JUnit report or full pass is claimed for it. The controls-three rerun uses three workers and a 3600-second limit, following its own same-configuration loopback canary.'),
    ('Its result is retained separately.',
     'It failed during setup with frozen native controller bytes changed: run_native_canary, before capture or dispatch. Its result is retained separately; no second correction case was attempted.'),
    ('and report_prepared_worker_20261116.py. The transformation scripts',
     'report_prepared_worker_20261116.py and finalize_prepared_report_20261116.py. The transformation scripts'),
    ("    ledger['pins'] = pins\n",
     "    ledger['pins'] = pins\n"
     "    ledger['review_findings'] = {\n"
     "        'frozen_controller_pin_integration': 'blocked: lead owns pin edits',\n"
     "        'empty_package_initializer': 'fixed with exact source verifier',\n"
     "        'delegation_drift': 'fixed with post-preparation recheck',\n"
     "        'heavy_post_capture_reconstruction': 'replaced with fresh identity checks',\n"
     "        'reaped_worker_group_signal': 'fixed with retained PID and probe-only Darwin fallback',\n"
     "        'same_size_dependency_edit': 'fixed with required full baseline comparison'}\n")]
for old, new in replacements:
    if text.count(old) != 1:
        raise ValueError('unexpected report shape')
    text = text.replace(old, new, 1)
path.write_text(text)
