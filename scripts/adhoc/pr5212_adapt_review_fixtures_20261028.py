#!/usr/bin/env python3
"""PR #5212/D55, 2026-10-28: preserve and adapt Claude's offline D42 fixtures.

Input: read-only scratch fixture and its verified SHA256. Output: repository
test copy with only D56/D57 and acknowledged-crash expectations updated.
"""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('/private/tmp/claude-501/d42-review-Uaym/fixtures/test_d42_claude.py')


def main():
    raw = SOURCE.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == '7ec301d4e9a812f3f3e5f71c3703ca1994af3eb9b253de8e3d9fe0c5f40a5efa', digest
    text = raw.decode()
    text = ('# Preserved D42 fixture, adapted for D55/D56/D57 on 2026-10-28.\n'
            '# Original SHA256: ' + digest + '\n' + text)
    old = ('    # D41/H3 item 3: a matching override lets the run continue, marked assisted.\n'
           '    assert outcome[0] != "refused", outcome')
    new = ('    # D56: a terminal override is ineffective and must remain unrecorded.\n'
           '    assert outcome[0] == "refused" and outcome[2] == outcome[3] == 0, outcome\n'
           '    assert not data.get("latch_overrides")')
    assert text.count(old) == 1
    text = text.replace(old, new)
    old = '    record("d_forged_rechain", outcome=outcome[0], detail=outcome[1], dispatches=outcome[2], counts=outcome[3])'
    assert text.count(old) == 1
    text = text.replace(old, old + '\n    assert outcome[0] == "refused" and outcome[2] == outcome[3] == 0, outcome\n'
                        '    assert "expected=" in outcome[1] and "found=" in outcome[1]')
    text = text.replace('"""Not a D41 requirement: a local chain with no external anchor can be re-forged."""',
                        '"""D57: a re-forged local chain differs from the retained launch head."""')
    start = text.index('    resumed = plain_resume(spec, FakeMessages())', text.index('def test_fp_crash_'))
    text = text[:start] + '''    refused = plain_resume(spec, FakeMessages())
    assert refused[0] == "refused" and refused[2] == 0, refused
    events = required_events(refused[1])
    assert events, refused
    write_override(spec, events)
    resumed = plain_resume(spec, FakeMessages())
    record("fp_crash_window", resume=resumed[0], resume_detail=resumed[1],
           resume_dispatches=resumed[2], acknowledgement_required=True)
    assert resumed[0] == "completed", resumed
    assert resumed[3]["usage"]
    prov = yaml.safe_load(spec.provenance_path.read_text())
    assert prov["model"]["runtime_integrity"]["assisted"] is True


# D57: independent test launch monitor retains heads at durable appends.
pytestmark = pytest.mark.usefixtures("journal_launch_monitor")
'''
    (ROOT / 'tests/test_d42_claude_d55.py').write_text(text)
    print(digest)


if __name__ == '__main__':
    main()
