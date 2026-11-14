#!/usr/bin/env python3
"""Repair G07-F6 and adapt its offline runner, 2026-11-12.
Inputs: candidate observer and G07 runner. Outputs: alias-aware observer and
helper-2 runner. Serves the Claude lead helper-2 assignment; no pin updates.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
path = root / 'src/data_sheets_schema/native_shared_observations.py'
text = path.read_text()
old = """                message=value.get('message')
                if value.get('model',runtime['model'])!=runtime['model'] or (
                        type(message) is dict and message.get('model',runtime['model'])!=runtime['model']):
                    raise ValueError('native event contradicts the selected model')"""
new = "                native_model_aliases.require_frame_models(value,aliases)"
assert text.count(old) == 1
text = text.replace('from data_sheets_schema import native_shared_contract as c',
    'from data_sheets_schema import native_shared_contract as c\nfrom data_sheets_schema import native_model_aliases')
text = text.replace('        callback_ids=set()',
    '        aliases=native_model_aliases.model_aliases(runtime)\n        callback_ids=set()')
path.write_text(text.replace(old, new))
runner = root / 'scripts/adhoc/run_native_g07_tests_20261112.py'
text = runner.read_text().replace('codex-native-main-integration-20261112', 'codex-native-observer-alias-20261112').replace(
    'scratch-native-main-integration-20261112', 'scratch-h2-observer-alias-20261112')
text = text.replace('Offline G07 packet and capture test runner, 2026-11-12.',
    'Offline helper-2 observer and test repair runner, 2026-11-12.')
(root / 'scripts/adhoc/run_native_h2_tests_20261112.py').write_text(text)
