#!/usr/bin/env python3
"""2026-11-12 #5992/#5993: report local commits and saved offline test evidence.
Inputs: three owned branches, scratch results and previous hardening handoff.
Outputs: archived prior handoff and updated Markdown/JSON in report worktree.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

E = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
S = E / 'scratch-h3-launch-hardening-20261112'
R = E / 'codex-development-efficiency-20261111'
H = R / 'notes/development_efficiency_20261111/handoffs/codex-h3-launch-sequence-hardening-20261112'
PROTECTED = ('src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json')


def git(tree, *args):
    return subprocess.check_output(['git', '-C', str(tree), *args]).decode().strip()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    branches = {}
    for name, cohort in (('launch-sequence-hardening', 'design-5993-whole'),
                         ('failure-record', 'design-carry-failure'),
                         ('incomplete-capture-retention', 'design-carry-retention')):
        tree = E / ('codex-native-' + name + '-20261112')
        head = git(tree, 'rev-parse', 'HEAD')
        status = git(tree, 'status', '--porcelain')
        assert not status, (name, status)
        same = {}
        for path in (*PROTECTED, 'src/data_sheets_schema/native_subscription_guard.py'):
            base = '7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1' if path in PROTECTED else 'c1ad9baa1'
            expected = subprocess.check_output(['git', '-C', str(tree), 'show', base + ':' + path])
            same[path] = (tree / path).read_bytes() == expected
        assert all(same.values())
        tested = Path(json.loads((S / 'tests' / cohort / 'plan.json').read_bytes())['source_root'])
        source_pins = []
        for path in ('src/data_sheets_schema/native_capture_words.py',
                     'src/data_sheets_schema/native_sequence_start.py',
                     'src/data_sheets_schema/native_launch_sequence.py',
                     'src/data_sheets_schema/native_launch_entry.py',
                     'src/data_sheets_schema/native_subscription_capture.py',
                     'tests/test_native_sequence_start.py', 'tests/test_native_launch_sequence.py',
                     'tests/test_native_launch_entry.py'):
            assert (tree / path).read_bytes() == (tested / path).read_bytes(), (name, path)
            source_pins.append(pin(tested / path))
        branches[name] = {'head': head, 'branch': git(tree, 'branch', '--show-current'),
            'clean': True, 'unchanged': same, 'tested_source_pins': source_pins,
            'issue_commits': {issue: git(tree, 'log', '-1', '--format=%H', '--grep=' + issue)
                             for issue in ('5992', '5993')},
            'carry_messages': git(tree, 'log', '-2', '--format=%B')}
    cohorts = []
    for directory in sorted((S / 'tests').glob('design-*')):
        if not (directory / 'outcome.json').exists():
            raise ValueError('unfinished cohort: ' + str(directory))
        cases = ET.parse(directory / 'pytest.xml').getroot().findall('.//testcase')
        cohorts.append({'name': directory.name, 'cases': len(cases),
            'failures': sum(row.find('failure') is not None for row in cases),
            'errors': sum(row.find('error') is not None for row in cases),
            'skipped': sum(row.find('skipped') is not None for row in cases),
            'outcome': json.loads((directory / 'outcome.json').read_bytes()),
            'pins': [pin(directory / name) for name in ('outcome.json', 'pytest.xml', 'pytest.log')]})
    for required in ('design-5992-composed', 'design-5993-whole', 'design-carry-failure', 'design-carry-retention'):
        row = next(row for row in cohorts if row['name'] == required)
        assert not row['failures'] and not row['errors'] and row['outcome']['returncode'] == 0
    compositions = [{'composition': pin(path), 'restoration': pin(path.parent / 'config-restoration.json')}
                    for path in sorted(S.glob('design-*/composition.json'))]
    original = branches['launch-sequence-hardening']['issue_commits']
    md = f'''# Start-claim design ruling: helper 3 handoff

Issue 5992: {original['5992']}. Issue 5993: {original['5993']}.

The journal hash chain and consecutive event filenames detect interior removal or alteration. Nothing anchors the last event: deleting a start claim at the tail can renew that direction, just as deleting the existing limits-refusal latch at the tail can remove that refusal. Both limitations have explicit scratch-only regression witnesses. A complete consistent older copy of the state is not detected.

Final branch heads after carrying both commits:

'''
    for row in branches.values():
        md += f"- {row['branch']}: {row['head']}.\n"
    md += '\nSaved test counts (overlapping cohorts, not a unique-test total):\n\n'
    for row in cohorts:
        md += (f"- {row['name']}: {row['cases']} cases, {row['failures']} failures, "
               f"{row['errors']} errors, {row['skipped']} skipped; exit {row['outcome']['returncode']}.\n")
    md += '''
The first journal canary failed because a fixture timestamp call lacked its required label; that was corrected before its passing rerun. The uncomposed whole run had one genuine-registration fixture setup failure because the protected main RunSpec lacks native_shared_generation_version. The private four-postimage composition supplies the approved protected code; all final whole-file runs use that composition. Both earlier failures remain in the saved evidence.

## Implementation and review

The local capture-word journal is now version 2. A closed sequence_start event binds the normalized UTC direction, host confirmation, registration digest, word digest, packet path and existing common chain/authority fields. Owner starts also append events and remain repeatable. Delegated replay is registration-wide, including after word renewal and through another packet. The append uses the existing authority lock and file-plus-directory fsync before any child command. The separate start directory is removed; no filesystem identity is persisted.

The sequence never initializes the journal. Missing, empty, replaced, unreadable or unrecorded word state refuses before capture. Version 1 journals can be read only as historical evidence; current activation, starts and latch writes refuse. No registered document kind or version changed.

The verified entry supplies a one-use per-invocation namespace binding covering the namespace, argument list, captured source bytes and captured registration/review map by identity. The body consumes it before parsing or packet effects; the entry expires it on return. Ordinary imported calls, including loaded-A with reviewed retained-B bytes and even a populated input map, refuse. Fixtures use the real entry with both source pins and apply only a test-local clock substitution after verified compilation. Both supported module entry paths are exercised with fabricated commands in an isolated copied package. This boundary assumes the trusted entry and interpreter are intact; it is not protection against arbitrary code already controlling Python globals.

The read-only adversarial pass checked event closure, current-word selection after start events, registration-wide direction normalization, historical format routing, durability, entry binding lifetime, and module execution as main. The accepted unanchored-tail limitation is disclosed above. No additional strengthening was silently included.

## Optional separate strengthening proposal

Propose a separate commit anchoring the committed event count and tip hash in retained authority, with a crash-safe fail-closed append/update protocol under the existing lock. An independently retained tip would make deletion of a tail event disagree with authority. Replacing authority by rename must also preserve lock continuity, so the protocol needs its own review. This is a proposal, not an implemented optional commit, and it still cannot detect restoring a complete consistent older authority plus journal. No inode or filesystem identity is proposed.

## Integration and bounds

Both fixes were cherry-picked with origin references onto the failure-record and incomplete-capture-retention branches; exact mappings and messages are in JSON. Retention is taken under D141, not optional. No rebase was performed. The four protected files remain byte-identical to main on all three actual branches, and guard v1 is unchanged. Approved protected post-images exist only in private test compositions, whose temporary CI configurations were restored byte-exactly.

The earlier failure-record handoff's statement that these hardening repairs remain unresolved is superseded by this handoff. Independent review and lead integration remain outstanding. Nothing was pushed or published. No real native executable, probe, capture, reservation, provider or model call occurred; synthetic word and test state stayed in this helper's scratch.
'''
    backup = S / 'design-prior-handoff'
    backup.mkdir()
    for suffix in ('.md', '.json'):
        (backup / ('handoff' + suffix)).write_bytes(H.with_suffix(suffix).read_bytes())
    result = {'status': 'implemented-carried-tested-pending-independent-review', 'commits': original,
              'branches': branches, 'cohorts': cohorts, 'compositions': compositions,
              'tail_deletion_detected': False, 'whole_state_rollback_detected': False,
              'optional_strengthening_implemented': False, 'retention_taken': True,
              'prior_handoff': [pin(backup / ('handoff' + suffix)) for suffix in ('.md', '.json')],
              'summary_markdown': md}
    js = json.dumps(result, indent=2) + '\n'
    assert '@' not in md and '@' not in js
    H.with_suffix('.md').write_text(md)
    H.with_suffix('.json').write_text(js)
    for suffix in ('.md', '.json'):
        print(json.dumps(pin(H.with_suffix(suffix))))


if __name__ == '__main__':
    main()
