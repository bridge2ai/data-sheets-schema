#!/usr/bin/env python3
"""2026-11-12 #5990: adapt sequence unit fixtures to explicit verified-body API.
Production entry remains covered separately and by copied-package subprocess.
"""
from pathlib import Path
W=Path(__file__).resolve().parents[2]
p=W/'tests/test_native_launch_sequence.py'; s=p.read_text().replace('seq.main(', 'run_sequence(')
s=s.replace('REAL_RUN = subprocess.run','''REAL_RUN = subprocess.run


def run_sequence(arguments):
    # Unit tests exercise the reviewed body with an explicit fixture byte capture.
    # The trusted public entry has separate load/replace and subprocess coverage.
    return seq._run_verified(arguments, verified_script=Path(seq.__file__).read_bytes(), entry_inputs={})''')
s=s.replace("'native_subscription_guard', 'native_sequence_start')", "'native_subscription_guard', 'native_sequence_start', 'native_launch_entry')")
s=s.replace("        path = p['packet-directory'] / seq.OUTPUTS[seq.COMMANDS.index(doc['command'])]", "        if 'command' not in doc:\n            return doc\n        path = p['packet-directory'] / seq.OUTPUTS[seq.COMMANDS.index(doc['command'])]")
s=s.replace("    result['registration'].write_bytes(guard.canonical({'registration': {\n        'attempt_directory': str(base / 'NEVER-RESERVED-ATTEMPT')}}))", """    digest=guard.sha(Path(seq.__file__).read_bytes())
    result['registration'].write_bytes(guard.canonical({'registration': {
        'attempt_directory': str(base / 'NEVER-RESERVED-ATTEMPT'),
        'dependencies': {'base': {'package_sources': {'src/data_sheets_schema/native_launch_sequence.py': digest}}}}}))
    result['review'].write_bytes(guard.canonical({'kind': 'd4d_native_execution_review_bundle_v3',
        'version': 3, 'registration_sha256': guard.sha(result['registration'].read_bytes()),
        'sequence_script_sha256': digest}))""")
p.write_text(s)
p=W/'tests/test_native_sequence_start.py'; p.write_text(p.read_text().replace('seq.main(', 'fixtures.run_sequence('))
