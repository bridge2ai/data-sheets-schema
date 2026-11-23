"""PR6302 reviewed D128 successor evidence, 2026-11-22.

Inputs: immutable local commits, complete Git exports, the unchanged historical
approval and its exact retained evidence. Outputs: fresh plans, two serial scan
records, three full comparisons and a proposal that confers no approval.
The frozen-tool baseline/reference are retained observations, not new scans.
No native binary, generation code, provider, network or Git mutation is used.
Each prepare/scan/compare invocation is separate; there is no batch/approval mode.
"""

import argparse
from collections import defaultdict, deque
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
SELF = 'scripts/adhoc/compare_pr6302_d128_successor_20261122.py'
EXPORTER = 'scripts/adhoc/native_u5_inputs_20261108.py'
HISTORICAL_FIXTURE = 'tests/fixtures/native_d128_approved.json'
HISTORICAL_SHA = 'b54b057ab074e1154ff05cceddc27e96fe980ad340d9ebf97669e82aca3c2373'
EVIDENCE_SHA = '16b09d196f13addd5b4b15eac3baf86d328ff3cd76131649dbca60d2e6d6f69a'
BASELINE = 'cf50d9a1c059f3b5030103378ccef33619475dde'
REFERENCE = '1de1d0ff67f8e622ce14862effcba9050d5147c2'
FROZEN = ROOT.parent / 'scratch-d128-1de1d0ff6-20261119/itemized-scanner-comparison.json'
SKILL = '.claude/skills/d4d-generation-specificity-audit'
ARRAYS = ('hits', 'violations', 'test_dependencies')
KINDS = ('relocations', 'changed_fields', 'removed', 'added')
ASSIGNMENT = 'PR6302 lead assignment 2026-11-22: reviewed guard, roster and scanner-pin successor; historical D128 decision unchanged'
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_ALLOW_PROTOCOL': '', 'GIT_CONFIG_GLOBAL': '/dev/null',
       'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1',
       'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0'}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def same(left, right):
    return encoded(left) == encoded(right)


def decode(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            need(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('nonfinite JSON value: ' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def save(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
           .replace(chr(64), '\\u0040') + '\n').encode('utf-8')
    need(not path.exists() and not path.is_symlink(), 'preserve existing output: ' + str(path))
    with path.open('xb') as stream:
        stream.write(raw)
    need(path.read_bytes() == raw, 'persisted output differs')
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def full_sha(value):
    need(type(value) is str and re.fullmatch('[0-9a-f]{40}', value) is not None,
         'full immutable commit required')
    return value


def git(repo, *args):
    completed = subprocess.run(['/usr/bin/git', '--no-replace-objects', '-c',
        'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', '-c',
        'protocol.allow=never', *args], cwd=repo, env=ENV,
        capture_output=True, timeout=120)
    need(completed.returncode == 0, 'local Git read failed: ' + completed.stderr.decode(errors='replace'))
    return completed.stdout


def array_shape(arrays):
    need(type(arrays) is dict and set(arrays) == set(ARRAYS), 'complete array roster required')
    need(all(type(rows) is list and all(type(row) is dict for row in rows)
             for rows in arrays.values()), 'complete object arrays required')


def fields(before, after):
    return sorted(key for key in set(before) | set(after)
        if (key in before) != (key in after) or not same(before.get(key), after.get(key)))


def positions(before, after):
    rows = []
    for index in range(max(len(before), len(after))):
        left, right = index < len(before), index < len(after)
        if left and right and same(before[index], after[index]):
            continue
        row = dict(index=index, before_present=left, after_present=right)
        if left: row['before'] = before[index]
        if right: row['after'] = after[index]
        if left and right: row['differing_fields'] = fields(before[index], after[index])
        rows.append(row)
    return rows


def diff_array(before, after):
    """Occurrence accounting from the reviewed H1 v3 comparator; types survive."""
    need(type(before) is list and type(after) is list
         and all(type(row) is dict for row in before + after), 'object arrays required')
    old, new = set(range(len(before))), set(range(len(after)))
    def pair(key):
        available = defaultdict(deque)
        for index in sorted(new):
            available[key(after[index])].append(index)
        pairs = []
        for index in sorted(old):
            matches = available[key(before[index])]
            if matches:
                pairs.append((index, matches.popleft()))
        for left, right in pairs:
            old.remove(left)
            new.remove(right)
        return pairs
    exact = pair(encoded)
    moved = pair(lambda row: encoded({key: value for key, value in row.items() if key != 'line'}))
    anchor = ('path', 'category', 'pattern', 'match', 'context', 'snippet')
    changed = pair(lambda row: encoded({key: row[key] for key in anchor if key in row}))
    def record(indices):
        left, right = indices
        return dict(before_index=left, after_index=right, before=before[left], after=after[right],
                    differing_fields=fields(before[left], after[right]))
    relocations = [record(indices) for indices in moved]
    need(all(row['differing_fields'] == ['line'] for row in relocations), 'non-coordinate relocation')
    ledger = dict(before_count=len(before), after_count=len(after),
        before_sha256=sha(encoded(before)), after_sha256=sha(encoded(after)),
        exact_matches=[[left, right] for left, right in exact], relocations=relocations,
        changed_fields=[record(indices) for indices in changed],
        removed=[dict(before_index=index, before=before[index]) for index in sorted(old)],
        added=[dict(after_index=index, after=after[index]) for index in sorted(new)],
        positional_differences=positions(before, after), exact_arrays_equal=same(before, after))
    validate_array(before, after, ledger)
    return ledger


def validate_array(before, after, ledger):
    need(type(ledger['before_count']) is int and type(ledger['after_count']) is int
         and ledger['before_count'] == len(before) and ledger['after_count'] == len(after),
         'complete array counts differ')
    need(sha(encoded(before)) == ledger['before_sha256']
         and sha(encoded(after)) == ledger['after_sha256'], 'ordered full-array hashes differ')
    old, new = [], []
    def index(value, rows):
        need(type(value) is int and 0 <= value < len(rows), 'invalid occurrence index')
        return value
    for pair in ledger['exact_matches']:
        need(type(pair) is list and len(pair) == 2, 'invalid exact pair')
        left, right = index(pair[0], before), index(pair[1], after)
        need(same(before[left], after[right]), 'exact occurrence changed')
        old.append(left); new.append(right)
    for kind in ('relocations', 'changed_fields'):
        for row in ledger[kind]:
            left, right = index(row['before_index'], before), index(row['after_index'], after)
            need(same(before[left], row['before']) and same(after[right], row['after']), 'changed occurrence differs')
            changed = fields(before[left], after[right])
            need(changed == row['differing_fields'] and bool(changed), 'changed-field ledger differs')
            if kind == 'relocations': need(changed == ['line'], 'relocation changed another field')
            old.append(left); new.append(right)
    for row in ledger['removed']:
        left = index(row['before_index'], before)
        need(same(before[left], row['before']), 'removed occurrence differs')
        old.append(left)
    for row in ledger['added']:
        right = index(row['after_index'], after)
        need(same(after[right], row['after']), 'added occurrence differs')
        new.append(right)
    need(sorted(old) == list(range(len(before))) and sorted(new) == list(range(len(after))),
         'duplicate, missing or extra occurrence accounting')
    if 'positional_differences' in ledger:
        need(same(ledger['positional_differences'], positions(before, after)), 'positional ledger differs')
    if 'exact_arrays_equal' in ledger:
        need(type(ledger['exact_arrays_equal']) is bool and ledger['exact_arrays_equal'] == same(before, after),
             'ordered array equality differs')


def compare(label, before, after):
    array_shape(before); array_shape(after)
    ledgers = {name: diff_array(before[name], after[name]) for name in ARRAYS}
    return {'label': label, 'arrays': ledgers,
            'exact_arrays_equal': all(row['exact_arrays_equal'] for row in ledgers.values())}


def historical(fixture_raw, evidence_raw):
    need(sha(fixture_raw) == HISTORICAL_SHA and sha(evidence_raw) == EVIDENCE_SHA,
         'historical fixture or evidence changed')
    approved, evidence = decode(fixture_raw), decode(evidence_raw)
    need(approved['decision'] == 'D128' and type(approved['version']) is int and approved['version'] == 1
         and approved['source_evidence_sha256'] == EVIDENCE_SHA
         and approved['baseline']['commit'] == BASELINE
         and approved['reference_candidate']['commit'] == REFERENCE
         and approved['tool_commit'] == REFERENCE, 'historical approval identity differs')
    frozen = {}
    for label, role in (('saved_main_cf50', 'baseline'), ('candidate', 'reference_candidate')):
        matches = [row for row in evidence['inputs'] if row['label'] == label]
        need(len(matches) == 1, 'historical input is not unique')
        value = matches[0]
        need(value['derivation_complete'] is True and same(value['source'], approved[role])
             and value['tool_commit'] == REFERENCE
             and same(value['tool_assets_sha256'], approved['tool_assets_sha256']),
             'historical source/tool pins differ')
        array_shape(value['arrays'])
        frozen[role] = value
    before, after = frozen['baseline']['arrays'], frozen['reference_candidate']['arrays']
    for name in ARRAYS:
        validate_array(before[name], after[name], approved['arrays'][name])
    need(len(approved['exact_violations']) == 9
         and same(before['violations'], approved['exact_violations'])
         and same(after['violations'], approved['exact_violations']), 'historical violation objects differ')
    return approved, frozen


def require_successor(raw, expected_sha, historical_approval):
    """The generation helper cannot approve its own proposal; this pin is reviewed."""
    need(type(expected_sha) is str and re.fullmatch('[0-9a-f]{64}', expected_sha) is not None,
         'reviewed successor pin is not supplied')
    need(sha(raw) == expected_sha, 'reviewed successor bytes changed')
    value = decode(raw)
    need(value.get('kind') == 'pr6302_d128_reviewed_successor' and type(value.get('version')) is int
         and value['version'] == 1 and value.get('assignment') == ASSIGNMENT,
         'successor is not the exact PR6302 review scope')
    need(value.get('historical_fixture_sha256') == HISTORICAL_SHA
         and value.get('historical_evidence_sha256') == EVIDENCE_SHA
         and value.get('historical_owner_decision_changed') is False,
         'successor changed historical approval')
    need(type(value.get('review_reference')) is str and bool(value['review_reference'].strip())
         and re.fullmatch('[0-9a-f]{64}', value.get('comparison_evidence_sha256', '')) is not None,
         'successor lacks explicit review/evidence identity')
    need(same(value.get('baseline'), historical_approval['baseline'])
         and same(value.get('exact_violations'), historical_approval['exact_violations']),
         'successor widened baseline or violation approval')
    need(value.get('frozen_baseline_unchanged') is True, 'current tool changed the frozen baseline')
    need(type(value.get('arrays')) is dict and set(value['arrays']) == set(ARRAYS), 'successor lacks complete arrays')
    for name in ARRAYS:
        ledger = value['arrays'][name]
        need(ledger.get('before_sha256') == historical_approval['arrays'][name]['before_sha256']
             and type(ledger.get('before_count')) is int
             and ledger['before_count'] == historical_approval['arrays'][name]['before_count'],
             'successor baseline array differs')
    full_sha(value['reference_candidate']['commit']); full_sha(value['tool_commit'])
    need(value['reference_candidate']['commit'] == value['tool_commit'], 'successor source/tool commits differ')
    identity = value['reference_candidate']
    need(set(identity) == set(historical_approval['reference_candidate'])
         and same(identity.get('physical_input_mask'), historical_approval['baseline']['physical_input_mask']),
         'successor source inventory scope differs')
    full_sha(identity['tree'])
    need(all(type(identity.get(key)) is str and re.fullmatch('[0-9a-f]{64}', identity[key])
             for key in ('committed_roster_sha256', 'physical_inputs_sha256')),
         'successor source inventory pins are incomplete')
    need(type(value.get('tool_assets_sha256')) is dict
         and set(value['tool_assets_sha256']) == set(historical_approval['tool_assets_sha256'])
         and all(type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest)
                 for digest in value['tool_assets_sha256'].values()), 'successor scanner roster differs')
    need(all(value['tool_assets_sha256'][name] == digest
             for name, digest in historical_approval['tool_assets_sha256'].items()
             if name != SKILL + '/scan.py'), 'successor changed scanner configuration or skill scope')
    return value


def exporter(repo, output):
    path = ROOT / EXPORTER
    spec = importlib.util.spec_from_file_location('pr6302_d128_exporter', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT, module.SCRATCH = repo, output / 'exports'
    module.git = lambda *args: git(repo, *args)
    return module


def source_identity(repo, manifest):
    rows = [dict(path=path, mode=row['mode'], kind='blob', git_oid=row['git_blob'],
                 bytes=row['bytes'], sha256=row['sha256']) for path, row in sorted(manifest['files'].items())]
    return dict(commit=manifest['commit'], tree=manifest['commit_tree'],
        physical_input_mask=manifest['path_mask'],
        committed_roster_sha256=sha(git(repo, 'ls-tree', '-r', '-z', manifest['commit'])),
        physical_inputs_sha256=sha(encoded(rows)))


def assets(repo, commit):
    names = git(repo, 'ls-tree', '-r', '--name-only', commit, '--', SKILL).decode().splitlines()
    need(names and len(set(names)) == len(names), 'scanner assets missing or duplicated')
    return {name: sha(git(repo, 'show', commit + ':' + name)) for name in names}


def checked_plan(args):
    raw = (args.output / 'plan.json').read_bytes()
    need(type(args.plan_sha256) is str and sha(raw) == args.plan_sha256, 'explicit plan pin differs')
    plan = decode(raw)
    need(plan.get('kind') == 'pr6302_d128_successor_plan' and type(plan.get('version')) is int
         and plan['version'] == 1 and plan.get('assignment') == ASSIGNMENT, 'plan scope differs')
    need(plan['candidate_commit'] == args.candidate and plan['repository'] == str(args.repository), 'plan source differs')
    need(set(plan['helper_assets_sha256']) == {SELF, EXPORTER, HISTORICAL_FIXTURE}, 'plan helper roster differs')
    for relative, digest in plan['helper_assets_sha256'].items():
        need(sha((ROOT / relative).read_bytes()) == digest
             and sha(git(args.repository, 'show', args.candidate + ':' + relative)) == digest,
             'helper differs from the immutable candidate: ' + relative)
    approved, frozen = historical((ROOT / HISTORICAL_FIXTURE).read_bytes(), args.frozen_evidence.read_bytes())
    need(same(plan['historical_approval'], approved), 'plan historical approval differs')
    need(same(plan['historical_evidence'], {'path': str(args.frozen_evidence), 'sha256': EVIDENCE_SHA}),
         'plan frozen evidence differs')
    inputs = exporter(args.repository, args.output)
    need(set(plan['sources']) == {'baseline', 'candidate'}, 'plan source roster differs')
    for name, commit in (('baseline', BASELINE), ('candidate', args.candidate)):
        selected = plan['sources'][name]
        need(selected['identity']['commit'] == commit and selected['label'] == 'scanner-candidate-' + commit[:9],
             'plan source role differs')
        tree, manifest = inputs.checked_scanner_input(selected['label'], selected['identity']['commit'])
        need(selected['tree'] == str(tree), 'plan physical tree differs')
        need(same(source_identity(args.repository, manifest), selected['identity']), 'source inventory changed')
        need(sha((tree.parent / 'manifest.json').read_bytes()) == selected['manifest_sha256'], 'export manifest changed')
    need(same(assets(args.repository, args.candidate), plan['tool_assets_sha256']), 'current scanner changed')
    return plan, inputs, approved, frozen


def prepare(args):
    need(not args.output.exists() and not args.output.is_symlink(), 'prepare requires a fresh output root')
    need(args.output == args.output.resolve() and not args.output.is_relative_to(args.repository),
         'output must be a physical external directory')
    need(git(args.repository, 'rev-parse', args.candidate + '^{commit}').decode().strip() == args.candidate,
         'candidate is not the explicit local commit')
    helper_pins = {}
    for relative in (SELF, EXPORTER, HISTORICAL_FIXTURE):
        raw = (ROOT / relative).read_bytes()
        need(raw == git(args.repository, 'show', args.candidate + ':' + relative), 'commit helper before preparing')
        helper_pins[relative] = sha(raw)
    approved, frozen = historical((ROOT / HISTORICAL_FIXTURE).read_bytes(), args.frozen_evidence.read_bytes())
    need(same(assets(args.repository, REFERENCE), approved['tool_assets_sha256']), 'frozen tool Git bytes differ')
    for value in frozen.values():
        source = value['source']
        need(git(args.repository, 'rev-parse', source['commit'] + '^{tree}').decode().strip() == source['tree']
             and sha(git(args.repository, 'ls-tree', '-r', '-z', source['commit'])) == source['committed_roster_sha256'],
             'frozen Git source identity differs')
    args.output.mkdir()
    (args.output / 'exports').mkdir()
    inputs = exporter(args.repository, args.output)
    sources = {}
    for name, commit in (('baseline', BASELINE), ('candidate', args.candidate)):
        label = 'scanner-candidate-' + commit[:9]
        inputs.materialize(label, commit, inputs.BASE_SCAN_PATHS)
        tree, manifest = inputs.checked_scanner_input(label, commit)
        sources[name] = dict(label=label, tree=str(tree), identity=source_identity(args.repository, manifest),
            manifest_sha256=sha((tree.parent / 'manifest.json').read_bytes()))
    need(same(sources['baseline']['identity'], approved['baseline']), 'baseline export differs from historical source')
    plan = dict(kind='pr6302_d128_successor_plan', version=1, assignment=ASSIGNMENT,
        repository=str(args.repository), candidate_commit=args.candidate, sources=sources,
        helper_assets_sha256=helper_pins, historical_approval=approved,
        historical_evidence={'path': str(args.frozen_evidence), 'sha256': EVIDENCE_SHA},
        tool_assets_sha256=assets(args.repository, args.candidate),
        scope='Two new current-tool scans plus exact retained frozen evidence; no approval or native acceptance.')
    print(json.dumps(save(args.output / 'plan.json', plan), sort_keys=True))


def load_scan(args, name, plan):
    directory = args.output / name
    run = decode((directory / 'run.json').read_bytes())
    need(type(run.get('returncode')) is int and run['returncode'] in (0, 1)
         and run.get('derivation_complete') is True and run.get('source_unchanged') is True,
         'scan is incomplete or failed')
    need(run.get('plan_sha256') == args.plan_sha256 and run.get('source') == name
         and same(run.get('source_identity'), plan['sources'][name]['identity'])
         and same(run.get('tool_assets_sha256'), plan['tool_assets_sha256']), 'scan source/tool binding differs')
    raw = (directory / 'scan.json').read_bytes()
    need(sha(raw) == run['scan_sha256'], 'complete scanner report changed')
    document = decode(raw)
    need(document.get('self_test', {}).get('passed') is True, 'scanner self-test did not pass')
    arrays = {key: document[key] for key in ARRAYS}
    array_shape(arrays)
    need(same(arrays, run['arrays']), 'persisted full arrays differ')
    return run


def scan(args):
    plan, inputs, _, _ = checked_plan(args)
    name = args.scan
    if name == 'candidate':
        load_scan(args, 'baseline', plan)
    selected = plan['sources'][name]
    tree, _ = inputs.checked_scanner_input(selected['label'], selected['identity']['commit'])
    tool = Path(plan['sources']['candidate']['tree']) / SKILL / 'scan.py'
    directory = args.output / name
    directory.mkdir()
    command = [sys.executable, '-P', '-B', str(tool), '--root', str(tree),
        '--report', str(directory / 'scan.md'), '--json', str(directory / 'scan.json'),
        '--tokens', str(tool.with_name('tokens.yaml')), '--exceptions', str(tool.with_name('exceptions.yaml')), '--full-json']
    environment = dict(ENV, PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
                       PIP_NO_INDEX='1', UV_OFFLINE='1')
    for key in ('HOME', 'TMPDIR', 'VIRTUAL_ENV'):
        if key in os.environ: environment[key] = os.environ[key]
    started = time.monotonic()
    record = dict(source=name, plan_sha256=args.plan_sha256, command=command,
        source_identity=selected['identity'], tool_assets_sha256=plan['tool_assets_sha256'],
        returncode=None, derivation_complete=False, source_unchanged=False,
        interpreter={'executable': sys.executable, 'version': sys.version})
    error = None
    stdout, stderr = b'', b''
    try:
        result = subprocess.run(command, cwd=tree, env=environment, capture_output=True, timeout=600)
        stdout, stderr = result.stdout, result.stderr
        record['returncode'] = result.returncode
        if type(result.returncode) is int and result.returncode in (0, 1):
            raw = (directory / 'scan.json').read_bytes()
            document = decode(raw)
            arrays = {key: document[key] for key in ARRAYS}
            array_shape(arrays)
            need(document.get('self_test', {}).get('passed') is True, 'scanner self-test failed')
            record.update(arrays=arrays, scan_sha256=sha(raw), derivation_complete=True)
    except BaseException as caught:
        error = caught
        if isinstance(caught, subprocess.TimeoutExpired):
            stdout, stderr = caught.stdout or b'', caught.stderr or b''
        record['failure'] = type(caught).__name__ + ': ' + str(caught)
    try:
        checked_plan(args)
        record['source_unchanged'] = True
    except BaseException as caught:
        record['source_check_failure'] = type(caught).__name__ + ': ' + str(caught)
        if error is None: error = caught
    record.update(seconds=time.monotonic() - started, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr))
    (directory / 'stdout.txt').write_bytes(stdout)
    (directory / 'stderr.txt').write_bytes(stderr)
    receipt = save(directory / 'run.json', record)
    if error is not None: raise error
    need(record['derivation_complete'], 'scanner did not produce complete arrays')
    print(json.dumps(dict(receipt, counts={key: len(rows) for key, rows in record['arrays'].items()}), sort_keys=True))


def compare_runs(args):
    plan, _, approved, frozen = checked_plan(args)
    before, after = load_scan(args, 'baseline', plan), load_scan(args, 'candidate', plan)
    legs = [compare(label, left, right) for label, left, right in (
        ('current_tool_baseline_to_current_candidate', before['arrays'], after['arrays']),
        ('frozen_tool_baseline_to_current_tool_baseline', frozen['baseline']['arrays'], before['arrays']),
        ('frozen_reference_to_current_candidate', frozen['reference_candidate']['arrays'], after['arrays']))]
    report = dict(kind='pr6302_d128_successor_comparison', version=1,
        status='complete_diagnostic_pending_review', assignment=ASSIGNMENT,
        plan_sha256=args.plan_sha256, historical_fixture_sha256=HISTORICAL_SHA,
        source_manifests=plan['sources'], helper_assets_sha256=plan['helper_assets_sha256'],
        historical_evidence_sha256=EVIDENCE_SHA, historical_owner_decision_changed=False,
        frozen_inputs=frozen, new_runs={'baseline': before, 'candidate': after}, comparisons=legs,
        fresh_scan_count=2, frozen_runs_reexecuted=False,
        tool_asset_delta=[dict(path=path, before_sha256=approved['tool_assets_sha256'].get(path),
                             after_sha256=plan['tool_assets_sha256'].get(path))
            for path in sorted(set(approved['tool_assets_sha256']) | set(plan['tool_assets_sha256']))
            if approved['tool_assets_sha256'].get(path) != plan['tool_assets_sha256'].get(path)],
        interpretation='All ordered objects and duplicate occurrences retained. New differences require explicit PR6302 review; no historical approval is rewritten.')
    receipt = save(args.output / 'comparison.json', report)
    need(legs[1]['exact_arrays_equal'], 'current scanner changed the historical baseline; no proposal emitted')
    need(same(before['arrays']['violations'], approved['exact_violations'])
         and same(after['arrays']['violations'], approved['exact_violations']),
         'unreviewed violation objects; no proposal emitted')
    proposal = dict(kind='pr6302_d128_successor_proposal', version=1, assignment=ASSIGNMENT,
        review_reference=None, comparison_evidence_sha256=receipt['sha256'],
        historical_fixture_sha256=HISTORICAL_SHA, historical_evidence_sha256=EVIDENCE_SHA,
        historical_owner_decision_changed=False, frozen_baseline_unchanged=True,
        baseline=approved['baseline'], reference_candidate=plan['sources']['candidate']['identity'],
        tool_commit=args.candidate, tool_assets_sha256=plan['tool_assets_sha256'],
        arrays={name: {key: value for key, value in ledger.items()
                      if key not in ('positional_differences', 'exact_arrays_equal')}
                for name, ledger in legs[0]['arrays'].items()}, exact_violations=approved['exact_violations'])
    print(json.dumps({'comparison': receipt, 'proposal': save(args.output / 'successor-proposal.json', proposal),
                      'approved': False}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=ROOT)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--frozen-evidence', type=Path, default=FROZEN)
    parser.add_argument('--plan-sha256')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--scan', choices=('baseline', 'candidate'))
    mode.add_argument('--compare', action='store_true')
    args = parser.parse_args()
    args.repository, args.output = args.repository.absolute(), args.output.absolute()
    full_sha(args.candidate)
    need(args.repository == args.repository.resolve(), 'repository is an alias')
    if args.prepare: prepare(args)
    elif args.scan: scan(args)
    else: compare_runs(args)


if __name__ == '__main__':
    main()
