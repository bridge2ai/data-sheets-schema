"""Preserve full environment baseline in D156 resume checks, 2026-11-16.

Inputs/outputs: environment verifier, prepared worker, and regression tests.
One-time transformation for the capture-order helper branch; no pin edits.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError('unexpected source shape: ' + str(path))
    path.write_text(text.replace(old, new, 1))


source = ROOT / 'src/data_sheets_schema/native_environment_manifest.py'
replace(source,
    "    full result's file identities; a changed payload refuses without rehashing.\n"
    '    """\n'
    "    if mode not in ('full', 'light'):",
    "    full result's file identities; a changed payload refuses without rehashing.\n"
    "    Prepared mode requires that baseline and never regenerates after capture.\n"
    '    """\n'
    "    if mode not in ('full', 'light', 'prepared'):")
replace(source,
    "        if memo is None:\n            if len(state['full']) >= 64:",
    "        if memo is None:\n            if mode == 'prepared':\n                raise ValueError('prepared environment verification requires a process full baseline')\n            if len(state['full']) >= 64:")
worker = ROOT / 'src/data_sheets_schema/native_prepared_worker.py'
replace(worker, "environment_mode='light'", "environment_mode='prepared'")
replace(worker, 'and runs a light census.', 'and compares a fresh census to the full preparation baseline.')
tests = ROOT / 'tests/test_native_prepared_worker.py'
replace(tests, "call[2] == 'light'", "call[2] == 'prepared'")
replace(tests, 'test_each_recheck_requests_fresh_light_verification',
        'test_each_recheck_requires_fresh_census_against_prepared_baseline')
tests = ROOT / 'tests/test_native_environment_manifest.py'
with tests.open('a') as stream:
    stream.write('''


def test_prepared_verification_requires_existing_full_baseline(installed, tmp_path, monkeypatch):
    pin = m.write(tmp_path / 'prepared.json')
    state = m._process_state()
    state['full'].clear()
    def forbidden():
        raise AssertionError('prepared check must not regenerate')
    monkeypatch.setattr(m, 'generate', forbidden)
    with pytest.raises(ValueError, match='requires a process full baseline'):
        m.verify(pin, mode='prepared')


def test_prepared_census_rejects_same_size_payload_edit(installed, tmp_path, monkeypatch):
    pin = m.write(tmp_path / 'prepared.json')
    original = m.verify(pin)
    def forbidden():
        raise AssertionError('prepared check must not regenerate')
    monkeypatch.setattr(m, 'generate', forbidden)
    assert m.verify(pin, mode='prepared') == original
    target = installed.root / 'file.py'
    before = target.read_bytes()
    target.write_bytes(before.replace(b'True', b'None'))
    assert target.stat().st_size == len(before)
    with pytest.raises(ValueError, match='installed payload changed'):
        m.verify(pin, mode='prepared')
''')
