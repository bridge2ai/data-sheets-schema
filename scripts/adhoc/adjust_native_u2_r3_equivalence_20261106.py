# Purpose: compare explicit-old-values with the required truthful profile basis (#5508).
# Inputs: equivalence test. Output: narrow documented normalization; 2026-11-06.
from pathlib import Path
R=Path(__file__).resolve().parents[2]
p=R/'tests/test_native_preparer_v2_boundaries.py';s=p.read_text().replace('def test_source_commit_bytes():','def test_source_commit_bytes(isolated):');p.write_text(s)
p=R/'tests/test_native_preparer_v2_equivalence.py';s=p.read_text()
s=s.replace('    assert after == before', '''    assert set(after) == set(before)
    # The requested truthful profile basis changes recorder text and its hash.
    # Normalize only that exact provenance change; JSON numbers compare by value.
    original = tmp_path/'old-rendered'
    hash_changes = {}
    for relative in before:
        if relative.endswith('.md'):
            text = (original/relative).read_text().replace('stated by the registered caller', 'declared by source manifest')
            assert text == (destination/relative).read_text()
            hash_changes[before[relative]] = hashlib.sha256(text.encode()).hexdigest()
    for relative in before:
        if relative.endswith('.json'):
            text = (original/relative).read_text().replace('stated by the registered caller', 'declared by source manifest')
            for old_hash, new_hash in hash_changes.items():
                text = text.replace(old_hash, new_hash)
            assert json.loads(text) == json.loads((destination/relative).read_bytes())''')
s=s.replace('    assert new_pins == old_pins', '''    assert set(new_pins) == set(old_pins)
    for path, pin in old_pins.items():
        if Path(path).is_relative_to(destination):
            relative = str(Path(path).relative_to(destination))
            # Output equality was checked above, including the provenance delta.
            assert new_pins[path] == after[relative]
        else:
            assert new_pins[path] == pin''')
s=s.replace("'identical_files': before", "'old_files': before, 'new_files': after, 'pin_count': len(new_pins), 'kids_first_pins': sum('/kids_first/' in p for p in new_pins), 'allowed_difference': 'truthful profile_basis and derived instruction hashes; JSON numeric representation'")
p.write_text(s)
