"""Inventory merge pins without rotating any production or test constant.

Inputs: candidate commit, current checkout, external scratch. Outputs: complete
old/current/actual pin ledger, generated Markdown, and unapplied review-only diff.
Serves D148 manifest integration, Codex 196 handoff, 2026-11-14.
"""
import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCAN = '.claude/skills/d4d-generation-specificity-audit/scan.py'
AUTHORITY = 'src/data_sheets_schema/native_execution_authority_v2.py'
SUMMARIES = ('_NATIVE_V2_RENDER_SOURCES', '_NATIVE_V2_INTEGRATED_RENDER_SOURCES')
CONSTANTS = (
    ('src/data_sheets_schema/native_attribution_controller.py', 'SOURCES_SHA256', 'src/data_sheets_schema/native_controller_sources_v1.json'),
    ('src/data_sheets_schema/native_attribution_controller_v2.py', 'SOURCES_SHA256', 'src/data_sheets_schema/native_controller_sources_v2.json'),
    ('src/data_sheets_schema/native_shared_authority_wire.py', 'CONTROLLER_SOURCES_SHA256', 'src/data_sheets_schema/native_controller_sources_v2.json'),
    ('tests/test_native_shared_permission_protocol.py', 'CONTROL_SHA', 'notes/matched_cborg_2026-09-13/native_controls/native_control.py'),
    ('tests/test_native_h1_scanner_authority.py', 'REVIEWED', AUTHORITY),
)
PROTECTED = ('src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
    'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, check=True).stdout


def constants(raw):
    nodes = {target.id: node.value for node in ast.parse(raw).body if isinstance(node, ast.Assign)
             for target in node.targets if isinstance(target, ast.Name)}
    def evaluate(node):
        if isinstance(node, ast.Dict):
            value = {}
            for key, item in zip(node.keys, node.values):
                if key is None:
                    value.update(evaluate(nodes[item.id]))
                else:
                    value[ast.literal_eval(key)] = ast.literal_eval(item)
            return value
        return ast.literal_eval(node)
    return nodes, evaluate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    args = parser.parse_args()
    scratch = args.scratch.resolve(strict=True)
    def before(path):
        return git('show', args.candidate + ':' + path)
    def current(path):
        return (ROOT / path).read_bytes()
    rows = []
    def row(location, target, old_pin, current_pin, historical=False):
        old_actual, actual = sha(before(target)), sha(current(target))
        proposed = current_pin if historical else actual
        rows.append(dict(location=location, target=target, old_pin=old_pin, current_pin=current_pin,
            candidate_sha256=old_actual, working_sha256=actual, proposed_pin=proposed,
            pin_changed_by_merge=old_pin != current_pin, source_changed_by_merge=old_actual != actual,
            disposition='historical contract retained' if historical else
                        'review-only rotation' if current_pin != proposed else 'unchanged; exact bytes match'))
    for path, name, target in CONSTANTS:
        b, be = constants(before(path)); a, ae = constants(current(path))
        row(path + ':' + name, target, be(b[name]), ae(a[name]))
    for version in ('v1', 'v2'):
        path = 'src/data_sheets_schema/native_controller_sources_' + version + '.json'
        b, a = json.loads(before(path)), json.loads(current(path))
        row(path + ':file', path, sha(before(path)), sha(current(path)))
        rows.append(dict(location=path + ':source_commit', target=path, old_pin=b['source_commit'],
            current_pin=a['source_commit'], proposed_pin=a['source_commit'],
            disposition='unchanged' if b['source_commit'] == a['source_commit'] else 'changed',
            pin_changed_by_merge=b['source_commit'] != a['source_commit']))
        for name, item in a['modules'].items():
            row(path + ':modules.' + name, item['path'], b['modules'][name]['sha256'], item['sha256'])
            at_commit = sha(git('show', a['source_commit'] + ':' + item['path']))
            rows[-1]['at_source_commit_sha256'] = at_commit
            assert at_commit == item['sha256'] == rows[-1]['working_sha256']
    b, be = constants(before(SCAN)); a, ae = constants(current(SCAN))
    for summary in SUMMARIES:
        old, new = be(b[summary]), ae(a[summary])
        for target, value in new.items():
            row(SCAN + ':' + summary, target, old[target], value, historical=summary == SUMMARIES[0])
    protected = {path: {'candidate': sha(before(path)), 'working': sha(current(path))} for path in PROTECTED}
    assert all(item['candidate'] == item['working'] for item in protected.values())
    report = {'candidate': args.candidate, 'head': git('rev-parse', 'HEAD').decode().strip(),
        'rows': rows, 'protected': protected, 'applied_rotations': 0,
        'pin_changes': [r for r in rows if r['pin_changed_by_merge']],
        'proposed_rotations': [r for r in rows if r['proposed_pin'] != r['current_pin']]}
    # Do not update historical summaries. This diff is necessary identity review
    # only; the scanner's v2 AST contracts also need a reviewed v3 successor.
    patches = []
    for path in (SCAN, CONSTANTS[-1][0]):
        original = current(path).decode()
        old_pin = next(r['current_pin'] for r in report['proposed_rotations'] if r['location'].startswith(path + ':'))
        assert original.count(old_pin) == 1
        proposal = original.replace(old_pin, sha(current(AUTHORITY)), 1)
        patches.extend(difflib.unified_diff(original.splitlines(True), proposal.splitlines(True),
            fromfile='a/' + path, tofile='b/' + path))
    (scratch / 'pin-proposal-review-only.diff').write_text(''.join(patches))
    (scratch / 'pin-inventory.json').write_text(json.dumps(report, indent=2) + '\n')
    lines = ['| Pin location and target | Candidate pin | Merged pin | Review proposal | Disposition |',
             '| --- | --- | --- | --- | --- |']
    for item in rows:
        lines.append('| ' + ' | '.join([item['location'] + '<br>' + item['target'], item['old_pin'],
            item['current_pin'], item['proposed_pin'], item['disposition']]) + ' |')
    (scratch / 'pin-inventory.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({k: report[k] for k in ('candidate', 'head', 'applied_rotations', 'pin_changes', 'proposed_rotations', 'protected')}, indent=2))


if __name__ == '__main__':
    main()
