"""PR5531/D99: acknowledge intentional digest change and append inventories.

Inputs: rebuilt schema/current digest renderer. Outputs: digest test pin and
append-only inventory entries for both profiles. 2026-11-08.
"""
from pathlib import Path
from data_sheets_schema import schema_digest as digest, profiles

root = Path(__file__).resolve().parents[2]
path = root / 'tests/test_schema_sync.py'
old = 'b2d80be089a79aab0ef1a88002b94ca6'
new = digest.fingerprint(digest.digest_text('Dataset', profile=profiles.BRIDGE2AI))
neutral = digest.fingerprint(digest.digest_text('Dataset', profile=profiles.NEUTRAL))
text = path.read_text()
needle = f'            "{old}")'
assert needle in text, 'Run once against the reviewed digest pin'
text = text.replace(needle, f'            "{new}")')
needle = '        the schema declares neutral substrate term sources and describes\n        type or format. No inventory or validation constraint changes.\n'
assert needle in text
text = text.replace(needle, needle + '\n'
    f'        `{old}` -> `{new}`, 2026-11-08 (PR5531, D99):\n'
    '        nested multivalued enums explicitly render [many], including\n'
    '        data_use_permission, credit_roles and conforms_to_standard.\n'
    f'        Neutral moves from `49d14e268864c35704fd000a1b10fb05` to `{neutral}`.\n'
    '        This is a deliberate model-facing cardinality instruction change;\n'
    '        historical inventory entries and recorded digests remain unchanged.\n')
path.write_text(text)
for profile in (profiles.BRIDGE2AI, profiles.NEUTRAL):
    print(profile.name, digest.record_inventory(profile=profile))
print('bridge2ai', old, '->', new)
print('neutral 49d14e268864c35704fd000a1b10fb05 ->', neutral)
