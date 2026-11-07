# Purpose: update U2 regression fixtures for explicit v2 inputs (#5508), 2026-11-06.
# Inputs: existing tests and retained M7 packet. Outputs: tests and saved fixture.
from pathlib import Path
import shutil
R=Path(__file__).resolve().parents[2]
p=R/'tests/test_native_authority_v2.py';s=p.read_text()
s=s.replace("    assert new.verified(raw)[1]['schema_version'] == 2", "    assert new.verified(raw)[1]['schema_version'] == 2\n    assert json.loads(raw)['controller_authority'] == {'version': 2, 'manifest': str(v2.SOURCES_PATH), 'sha256': v2.SOURCES_SHA256, 'sources': v2.controller_sources()}")
s=s.replace("        assert modules['prepare_direct'].__file__", "        assert modules['prepare_registration'] is modules['prepare_registration_v2']\n        assert modules['prepare_direct'].__file__")
s=s.replace("['--output', '/unused', '--project', 'NEUTRAL']", "['--output', '/unused', '--project', 'NEUTRAL', *DIRECT_ARGS]")
s=s.replace("['--projects', 'NEUTRAL', '--canary-order', 'NEUTRAL_agentic_rep2']", "['--projects', 'NEUTRAL', '--canary-order', 'NEUTRAL_agentic_rep2', *API_ARGS]")
s=s.replace("'--claude-executable', str(fake), '--cohort', 'authority_v2_offline_test'", "*DIRECT_ARGS, '--claude-executable', str(fake)")
s=s.replace("        pins = value['pinned_files']", "        assert value['authority_version'] == 2\n        assert value['controller_sources_sha256'] == v2.SOURCES_SHA256\n        value = direct.generation.require_envelope(value)\n        assert value['kind'] == 'd4d_direct_arm_registration_v2'\n        pins = value['pinned_files']")
s=s.replace('ROOT_UNUSED', '')
s += '''\n\nDIRECT_ARGS = ['--claude-executable', '/unused', '--cohort', 'offline', '--label-date', '2026-09-13', '--run-date', '2026-09-14', '--runaway-guard-usd', '60']
API_ARGS = ['--cohort', 'generalized_v10', '--label-date', '2026-09-13', '--run-date', '2026-09-14', '--series', 'generalized_v10_2026-09-13', '--authorization', 'user: +$200, 2026-09-13', '--additional-usd', '200', '--per-attempt-usd', '5', '--claude-executable', '/unused']
'''
p.write_text(s)
p=R/'tests/test_native_preparer_v2_equivalence.py';s=p.read_text().replace('import sys', 'import sys\nimport shutil\nfrom tests.test_native_authority_v2 import API_ARGS')
s=s.replace("    old.main()", "    old_pins = {}\n    new_pins = {}\n    old_sha, new_sha = old.sha, new.sha\n    def capture(target, original, path):\n        value = original(path)\n        target[str(Path(path).resolve())] = value\n        return value\n    monkeypatch.setattr(old, 'sha', lambda path: capture(old_pins, old_sha, path))\n    monkeypatch.setattr(new, 'sha', lambda path: capture(new_pins, new_sha, path))\n    old.main()")
s=s.replace('    metadata = {', "    shutil.move(destination, tmp_path/'old-rendered')\n    metadata = {")
s=s.replace("'--external-sources', str(BASE/'external_clinical')])", "'--external-sources', str(BASE/'external_clinical'), '--external-sources', str(BASE/'kids_first'), *API_ARGS])")
s=s.replace('    assert after == before', '''    assert after == before
    # Only the versioned preparer and explicit metadata JSON are additional identities.
    old_pins.pop(str(BASE/'prepare_registration.py'))
    new_pins.pop(str(BASE/'prepare_registration_v2.py'))
    new_pins.pop(str(external))
    assert new_pins == old_pins
    assert sum('/kids_first/' in path for path in new_pins) >= 129''')
p.write_text(s)
fixture=R/'tests/fixtures/native_u2_m7';fixture.mkdir(exist_ok=True)
for name in ('registration.json','composition.json','verified.json'):
    shutil.copyfile(R.parent/'scratch-native-u2/v1-replay-final'/name,fixture/name)
# Retain the old generator as provenance, not an always-skipped CI test.
shutil.copyfile(R/'tests/test_native_authority_replay_v1.py', R/'scripts/adhoc/generate_native_u2_m7_fixture_20261106.py')
(R/'tests/test_native_authority_replay_v1.py').write_text('''"""Saved M7 bytes remain version-specific without environment-gated CI skips."""
import json
from pathlib import Path
import pytest
from data_sheets_schema import native_attribution_registration_v2 as v2
from data_sheets_schema import native_attribution_registration as v1

FIXTURE = Path(__file__).parent/'fixtures/native_u2_m7'

def test_saved_m7_record_refuses_v2():
    raw = (FIXTURE/'registration.json').read_bytes()
    evidence = json.loads((FIXTURE/'verified.json').read_bytes())
    assert v1._sha(raw) == evidence['registration_sha256']
    assert v1._sha((FIXTURE/'composition.json').read_bytes()) == evidence['composition_sha256']
    assert json.loads(raw)['checker_source_tree_sha256'] != v1._code_pins()
    with pytest.raises(ValueError, match='unsupported native attribution registration version'):
        v2.verified(raw)
''')
