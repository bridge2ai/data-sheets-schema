#!/usr/bin/env python3
# Bind legacy149 reuse to the exact reviewed F4 leaf-test change, 2026-11-14.
# Inputs: frozen legacy invocation/census, local Git objects and source bytes.
# Outputs (main only): exclusive scope/reuse record and source/search snapshots.
# validate_reuse is read-only. No project imports, pytest or acceptance of other runs.
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
ORIGINAL = '2070a2116ceb5b1f5dd9a870c803ee3311d298b9'
CORRECTION = '21367471df2e7d2f761153e1b91b218a705c62c6'
LEAF = 'tests/test_native_publication_signals.py'
FILES = ('tests/test_native_execution.py', 'tests/test_native_receipt_origin_reporting.py')
SOURCE_SCOPE = ('src', 'tests', 'notes/matched_cborg_2026-09-13', 'pyproject.toml',
                'poetry.lock', 'conftest.py', '.github/workflows/main.yaml')
BEFORE_SHA = '56e04021c3f4f7b9976029b198b71f324031ab7d98c1b232b31ea7f848894a75'
AFTER_SHA = '254de126c8e4cb00197b31679f1829c4d4191a86f7e20b4cd3aedc52cd9397d2'
EXACT_ARTIFACTS = {
    'legacy-full-serial/command.json': '6f2cd666649bb1874ed135b5c8b6f4236e773dd733ac937d4594b4e88aa1e8b2',
    'legacy-full-serial/outcome.json': 'da0ccde79c1271213267fb8982e1472bfc17fcfc44614425179659776dfb332a',
    'legacy-full-serial/pytest.xml': 'c039d76f68a85eeec1110807c11f1e1c6f157d044841ea2cf96a59d25650ef06',
    'legacy-collection-census/census.json': 'e829f55eb11351a759265a760efa47759763d6ad52c86c3f643205813e0f8a48',
}
DEST = SCRATCH / 'legacy-leaf-reuse-6217-f4'
RECORD = DEST / 'reuse.json'


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def checked(record):
    require(pin(record['path']) == record, 'retained reuse pin changed: ' + record['path'])
    return record


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def scope_proof(final_head):
    require(git('rev-parse', 'HEAD').decode().strip() == final_head, 'final HEAD differs from current checkout')
    git('merge-base', '--is-ancestor', ORIGINAL, CORRECTION)
    git('merge-base', '--is-ancestor', CORRECTION, final_head)
    require(not git('status', '--porcelain', '--', *SOURCE_SCOPE), 'source scope is dirty')
    changed = git('diff', '--name-only', ORIGINAL, final_head, '--', *SOURCE_SCOPE).decode().splitlines()
    require(changed == [LEAF], 'legacy reuse allows exactly the reviewed leaf-test delta')
    require(not git('diff', '--name-only', CORRECTION, final_head, '--', *SOURCE_SCOPE),
            'source changed after reviewed leaf correction')
    require(git('diff', '--name-only', CORRECTION + '^', CORRECTION, '--', *SOURCE_SCOPE).decode().splitlines() == [LEAF],
            'correction commit changes other test/production scope')
    before = git('show', ORIGINAL + ':' + LEAF)
    after = git('show', CORRECTION + ':' + LEAF)
    require(sha(before) == BEFORE_SHA and sha(after) == AFTER_SHA and (ROOT / LEAF).read_bytes() == after,
            'reviewed leaf before/after/current bytes differ')
    old = b"    assert (evidence / 'final.json').read_bytes() == c.canonical(result)\n"
    new = (b'    # Final evidence uses the frozen pretty attribution encoding.\n'
           b"    assert (evidence / 'final.json').read_bytes() == engine.draft._encoded(result)\n")
    require(before.count(old) == 1 and before.replace(old, new) == after,
            'leaf change exceeds the exact reviewed oracle correction')
    # Same ignored-inclusive inventory contract as the runner, without imports.
    inventory = subprocess.check_output(['rg', '--files', '--hidden', '--no-ignore', '--null',
        'src', 'tests', '-g', '*.py', '-g', '*.pyi'], cwd=ROOT)
    actual = {name for name in inventory.split(b'\0') if name}
    tracked = set(git('ls-files', '-z').split(b'\0'))
    require(actual <= tracked, 'untracked or ignored Python source prevents reuse')
    return {'changed': changed, 'before_sha256': BEFORE_SHA, 'after_sha256': AFTER_SHA,
            'source_scope': list(SOURCE_SCOPE), 'ignored_inclusive_python_inventory': True}


def evidence_proof():
    evidence = []
    for name, digest in EXACT_ARTIFACTS.items():
        record = pin(SCRATCH / name)
        require(record['sha256'] == digest, 'not the exact retained legacy invocation/census: ' + name)
        evidence.append(record)
    command = json.loads((SCRATCH / 'legacy-full-serial/command.json').read_bytes())
    expected = [str(ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'), '-m', 'pytest', '-q',
        '-p', 'no:cacheprovider', *FILES, '--basetemp=' + str(SCRATCH / 'legacy-full-serial/cases'),
        '--junitxml=' + str(SCRATCH / 'legacy-full-serial/pytest.xml')]
    require(command['command'] == expected and command['cwd'] == str(ROOT) and command['head'] == ORIGINAL,
            'legacy invocation identity or selected files differ')
    outcome = json.loads((SCRATCH / 'legacy-full-serial/outcome.json').read_bytes())
    require(outcome['returncode'] == 0 and outcome['counts'] == {'total': 149, 'failed': 0, 'error': 0, 'skipped': 0},
            'legacy invocation is not the retained clean149 run')
    census = json.loads((SCRATCH / 'legacy-collection-census/census.json').read_bytes())
    require(census['head'] == ORIGINAL and census['cwd'] == str(ROOT) and tuple(census['files']) == FILES
            and census['status'] == 'verified' and census['returncode'] == 0
            and census['tests_executed'] is False and census['node_count'] == 149,
            'collection census identity or outcome differs')
    for key in ('command', 'log', 'nodes', 'producer', 'inventory_helper'):
        evidence.append(checked(census[key]))
    for record in census['source_pins'].values():
        evidence.append(checked(record))
    collection_command = json.loads(Path(census['command']['path']).read_bytes())
    require(collection_command['head'] == ORIGINAL and collection_command['kind'] == 'pytest_collection_only'
            and collection_command['cwd'] == str(ROOT) and '--collect-only' in collection_command['command']
            and collection_command['source_pins'] == census['source_pins'], 'collection command differs')
    nodes = json.loads(Path(census['nodes']['path']).read_bytes())
    expected_nodes = {(row['classname'], row['name']) for row in nodes}
    cases = ET.parse(SCRATCH / 'legacy-full-serial/pytest.xml').getroot().findall('.//testcase')
    actual_nodes = {(row.attrib['classname'], row.attrib['name']) for row in cases}
    require(len(nodes) == len(expected_nodes) == len(cases) == len(actual_nodes) == 149
            and actual_nodes == expected_nodes and all(not list(row) for row in cases),
            'legacy JUnit is not the exact all-passed collected149 identities')
    require({row['file'] for row in nodes} == set(FILES), 'collection contains unrelated files')
    evidence.append(pin(SCRATCH / 'legacy-full-serial/pytest.log'))
    return evidence, nodes


def validate_reuse(root, scratch, recorded_head, final_head, required_file, cohort_directory):
    require(Path(root) == ROOT and Path(scratch) == SCRATCH, 'reuse called from another checkout/scratch')
    require(recorded_head == ORIGINAL and required_file in FILES
            and Path(cohort_directory) == SCRATCH / 'legacy-full-serial',
            'reuse is limited to the exact legacy149 invocation and its two selected files')
    record = json.loads(RECORD.read_bytes())
    require(record['original_head'] == ORIGINAL and record['correction_commit'] == CORRECTION
            and record['files'] == list(FILES), 'reuse record identity differs')
    for item in record['evidence']:
        checked(item)
    evidence, nodes = evidence_proof()
    scope = scope_proof(final_head)
    require(record['scope_proof'] == scope, 'current scope no longer matches the reviewed leaf-only change')
    chosen = [row for row in nodes if row['file'] == required_file]
    return {'passed': True, 'original_head': ORIGINAL, 'recorded_head': ORIGINAL, 'final_head': final_head,
        'correction_commit': CORRECTION, 'required_file': required_file, 'test_nodes': chosen,
        **scope, 'evidence': [pin(RECORD), pin(Path(__file__).resolve()), *evidence],
        'reason': 'Exact clean149 invocation and collection census reused across only the reviewed, unimported publication-test oracle correction; original HEAD2070 remains explicit. No other invocation or test-proof exception is authorized.'}


def save(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    require(path.read_bytes() == raw, 'saved reuse evidence differs')


def main():
    require(not DEST.exists(), 'retain earlier reuse evidence')
    final = git('rev-parse', 'HEAD').decode().strip()
    scope = scope_proof(final)
    evidence, nodes = evidence_proof()
    search = ['rg', '--hidden', '--no-ignore', '-n', 'test_native_publication_signals',
              'src', 'tests', 'utils', 'conftest.py', 'pyproject.toml', '.github']
    found = subprocess.run(search, cwd=ROOT, capture_output=True, check=False)
    require(found.returncode == 1 and not found.stdout and not found.stderr,
            'publication test acquired a reference; repeat dependency review')
    DEST.mkdir()
    for name, raw in (('before-publication-test.py', git('show', ORIGINAL + ':' + LEAF)),
                      ('corrected-publication-test.py', (ROOT / LEAF).read_bytes()),
                      ('reviewed-leaf.patch', git('diff', ORIGINAL, CORRECTION, '--', LEAF))):
        save(DEST / name, raw)
        evidence.append(pin(DEST / name))
    result = {'original_head': ORIGINAL, 'correction_commit': CORRECTION, 'recorded_current_head': final,
        'files': list(FILES), 'scope_proof': scope, 'evidence': evidence,
        'selected_node_count': len(nodes), 'selected149_unchanged': True,
        'dependency_review': {'ignored_inclusive_search': search, 'returncode': found.returncode,
            'stdout': found.stdout.decode(), 'stderr': found.stderr.decode(),
            'basis': ['Exact two-file pytest invocation; no publication-test import/reference in searched source/config.',
                'Root conftest only excludes standalone demonstrations; tests conftest isolates environment and watches notes, without sibling collection imports.',
                'Legacy authority hashes only package sources and fixed controller modules; tests outside the consumed closure do not affect admission.',
                'The reviewed change touches only an assertion and adjacent comment; production, selected tests, shared fixtures and conftest remain byte-identical.']},
        'limits': ['Historical HEAD2070 test evidence, not a claim that old final artifacts were replayed at the corrected HEAD.',
                   'Only legacy-full-serial and its exact collection census qualify; fresh whole-file publication proof remains required.'],
        'producer': pin(Path(__file__).resolve())}
    save(RECORD, (json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
    proofs = [validate_reuse(ROOT, SCRATCH, ORIGINAL, final, file, SCRATCH / 'legacy-full-serial') for file in FILES]
    print(json.dumps({'record': pin(RECORD), 'passed_files': [row['required_file'] for row in proofs],
                      'selected_node_count': len(nodes)}))


if __name__ == '__main__':
    main()
