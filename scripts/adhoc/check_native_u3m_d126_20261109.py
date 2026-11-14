#!/usr/bin/env python3
"""U3-M D126 coordinate gate, 2026-11-09; no rendering or project imports.

Inputs: explicit completed --run directories and independently pinned U3-H raw
witnesses. Output: fresh private JSON under u3m, including verbatim old/new
changed lines. Physical paths and byte changes are never normalised. A moved,
added or missing D126 line stops this item; incomplete evidence also refuses.
--self-check exercises invented shifted/extra/missing lines, not real approval.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
EXEC = next(path for path in ROOT.parents if path.name == 'd4d-executions')
BASE = EXEC / 'scratch-native-u1u3/u3m'
LOCK = EXEC / 'plans/native_quiet_window.lock'
H = EXEC / 'scratch-native-u1u3/u3h/composed-r1-d114/cases/popen-gw0'
TARGET = 'test_d126_in_checkout_manifest_pins_every_native_instruction_delta'
PINS = {
    False: ('test_d126_in_checkout_manifest0', '05acd0f8b9b900b75781182d7228bf96a4c5324e3abddee92f403ddf58d02b0a'),
    True: ('test_d126_in_checkout_manifest1', 'fee08f5c24b36861268e83ebf39e48d1cd4ae3fdd005e75f851ab076795d33f5'),
}
ROSTER = dict(zip(('header:source_bundle', 'header:source_manifest', 'helper:chunk_check',
    'helper:source_scope', 'helper:phase1_receipts', 'helper:draft', 'helper:audit_evidence',
    'helper:final_evidence', 'helper:final_scope', 'helper:final_receipts', 'helper:recorder'),
    (1057, 1058, 1184, 1190, 1208, 1250, 1256, 1262, 1274, 1280, 1286)))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def quiet():
    require(not os.path.lexists(LOCK), 'quiet-window lock is active')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(items):
    value = {}
    for key, item in items:
        require(key not in value, 'duplicate JSON key')
        value[key] = item
    return value


class Evidence:
    def __init__(self):
        self.files = {}

    def read(self, path):
        quiet()
        require(path.is_absolute() and path.resolve(strict=True) == path and path.is_file(),
                'expected a physical file: ' + str(path))
        require(0 < path.stat().st_size <= 16 * 1024 * 1024, 'empty/oversized evidence')
        raw = path.read_bytes()
        row = dict(path=str(path), bytes=len(raw), sha256=sha(raw))
        require(self.files.setdefault(str(path), row) == row, 'evidence changed between reads')
        return raw

    def load(self, path):
        return json.loads(self.read(path), object_pairs_hook=unique,
                          parse_constant=lambda value: require(False, 'nonfinite JSON'))

    def verify(self):
        for path in tuple(self.files):
            self.read(Path(path))


def raw_delta(before, after):
    left, right = before.splitlines(keepends=True), after.splitlines(keepends=True)
    changes = []
    for index in range(max(len(left), len(right))):
        a, b = (left[index] if index < len(left) else None), (right[index] if index < len(right) else None)
        if a != b:
            changes.append(dict(line_index1=index + 1,
                before=None if a is None else a.decode('utf-8'), after=None if b is None else b.decode('utf-8'),
                before_sha256=None if a is None else sha(a), after_sha256=None if b is None else sha(b)))
    return changes, len(left), len(right)


def witness(path, evidence):
    data = evidence.load(path)
    require(data.get('decision') == 'D126' and type(data.get('u4b_runtime')) is bool,
            'D126 witness identity missing')
    before, after = (evidence.read(path.with_name(name + '-instruction.txt')) for name in ('before', 'after'))
    require(sha(before) == data['before_sha256'] and sha(after) == data['after_sha256'], 'instruction hash differs')
    actual, left, right = raw_delta(before, after)
    rows = data['changed_lines']
    require(type(rows) is list and all(type(row) is dict and type(row.get('role')) is str
            and type(row.get('line_index1')) is int for row in rows), 'malformed changed-line roster')
    require(len({row['role'] for row in rows}) == len(rows), 'duplicate changed-line role')
    declared = [{key: row[key] for key in ('line_index1', 'before', 'after', 'before_sha256', 'after_sha256')}
                for row in rows]
    valid = (left == right and len(actual) == len(rows) == 11
             and declared == actual and data.get('expected_change_count') == 11
             and data.get('observed_change_count') == 11 and data.get('unchanged_line_count') == left - 11
             and all(type(data.get(key)) is int for key in
                     ('expected_change_count', 'observed_change_count', 'unchanged_line_count')))
    return dict(path=str(path), document=data, actual_changed_lines=actual,
                before_line_count=left, after_line_count=right, exact_eleven_line_witness=valid)


def compare(old, new):
    a, b = ({row['role']: row for row in rows} for rows in (old, new))
    pairs = [dict(role=role, old=a[role], new=b[role]) for role in a if role in b]
    moved = [row for row in pairs if row['old']['line_index1'] != row['new']['line_index1']]
    added, missing = ([dict(role=role, new=b[role]) for role in b if role not in a],
                      [dict(role=role, old=a[role]) for role in a if role not in b])
    return dict(moved=moved, added=added, missing=missing,
                same_position_changed_bytes=[row for row in pairs
                    if row not in moved and (row['old']['before'] != row['new']['before']
                                             or row['old']['after'] != row['new']['after'])],
                stop_at_d126_item=bool(moved or added or missing))


def completed(run, evidence):
    require(run.is_absolute() and run.resolve(strict=True) == run and run.is_dir()
            and run != BASE and run.is_relative_to(BASE), 'run must be a physical U3-M directory')
    outcome = evidence.load(run / 'outcome.json')
    worker = evidence.load(run / 'worker-outcome.json')
    require(outcome.get('cleanup_verified') is True and outcome.get('interrupted') is None
            and outcome.get('forced_cleanup') is False and not outcome.get('observed_surviving_pids')
            and not outcome.get('observation_errors') and worker.get('source_origin_checks_passed') is True
            and outcome.get('worker') == worker and outcome.get('returncode') == worker.get('returncode')
            and type(worker.get('returncode')) is int and worker['returncode'] in (0, 1), 'run is not verified terminal')
    stability, plan = evidence.load(run / 'source-stability.json'), evidence.load(run / 'plan.json')
    require(stability['before'] == stability['after'] and stability['before']['status'] == ''
            and stability['before']['head'] == plan['source_commit'], 'run source identity changed')
    cases = [dict(name=node.get('name'), status=('failed' if node.find('failure') is not None
             or node.find('error') is not None else 'skipped' if node.find('skipped') is not None else 'passed'))
             for node in ET.fromstring(evidence.read(run / 'pytest.xml')).iter('testcase')
             if node.get('classname') == 'tests.test_native_u4b_a5_producer_integration'
             and (node.get('name') or '').startswith(TARGET + '[')]
    require(1 <= len(cases) <= 2, 'run must contain one or two D126 cases')
    paths = []
    for parent, dirs, files in os.walk(run / 'cases', followlinks=False):
        dirs[:] = [name for name in dirs if not (Path(parent) / name).is_symlink()]
        if 'd126-instruction-delta.json' in files:
            paths.append(Path(parent) / 'd126-instruction-delta.json')
    return cases, sorted(paths)


def failure_snapshots(run, evidence):
    result = []
    directory = run / 'd126-failures'
    if not directory.exists():
        return result
    require(directory.resolve(strict=True) == directory and directory.is_dir(), 'failure directory is aliased')
    for path in sorted(directory.glob('*.json')):
        data = evidence.load(path)
        require(data.get('kind') == 'native_u3m_d126_failure', 'unexpected failure snapshot')
        row = dict(path=str(path), snapshot=data)
        if data.get('before') and data.get('after'):
            raws = []
            for key in ('before', 'after'):
                pin = data[key]
                require(Path(pin['file']).name == pin['file'], 'failure raw path must be a basename')
                raw = evidence.read(path.with_name(pin['file']))
                require(sha(raw) == pin['sha256'] and len(raw) == pin['bytes'], 'failure raw hash differs')
                raws.append(raw)
            delta, left, right = raw_delta(*raws)
            row.update(actual_changed_lines=delta, before_line_count=left, after_line_count=right,
                       extra_positions=[line for line in delta if line['line_index1'] not in ROSTER.values()],
                       missing_roles=[dict(role=role, line_index1=index) for role, index in ROSTER.items()
                                      if index not in {line['line_index1'] for line in delta}])
        result.append(row)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, action='append', default=[])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()
    quiet()
    require(args.out.is_absolute() and args.out.parent.resolve(strict=True) == args.out.parent
            and args.out.is_relative_to(BASE) and args.out.suffix == '.json'
            and not os.path.lexists(args.out), 'output must be fresh private U3-M JSON')
    require(bool(args.run) != args.self_check and len(set(args.run)) == len(args.run), 'choose unique runs or self-check')
    evidence = Evidence()
    result = dict(kind='native_u3m_d126_coordinate_review', version=1, status='incomplete',
                  stop_at_d126_item=True, native_acceptance=False, public_ready=False,
                  scope='Raw private evidence. No path/byte normalisation; no assertion or approval changes.')
    code = 2
    try:
        if args.self_check:
            old = [dict(role='header', line_index1=2, before='a\n', after='b\n')]
            shifted = deepcopy(old); shifted[0]['line_index1'] = 3
            require(compare(old, shifted)['stop_at_d126_item'], 'shifted-line canary failed')
            require(compare(old, old + [dict(role='extra', line_index1=4, before='c', after='d')])['added'], 'extra-line canary failed')
            require(compare(old, [])['missing'] and not compare(old, old)['stop_at_d126_item'], 'missing/unchanged canary failed')
            result.update(status='invented_coordinate_canary_passed', stop_at_d126_item=False,
                          controls=['shifted_line', 'extra_line', 'missing_line', 'unchanged'])
            code = 0
        else:
            frozen = {}
            for variant, (folder, digest) in PINS.items():
                path = H / folder / 'd126-in-checkout-discriminator/d126-instruction-delta.json'
                require(sha(evidence.read(path)) == digest, 'independent frozen D126 witness changed')
                frozen[variant] = witness(path, evidence)
                require(frozen[variant]['document']['u4b_runtime'] is variant
                        and frozen[variant]['exact_eleven_line_witness']
                        and {row['role']: row['line_index1'] for row in frozen[variant]['document']['changed_lines']} == ROSTER,
                        'frozen role/coordinate roster differs')
            result['runs'], result['comparisons'], seen = [], [], set()
            for run in args.run:
                cases, paths = completed(run, evidence)
                failures = failure_snapshots(run, evidence)
                result['runs'].append(dict(path=str(run), cases=cases, failure_snapshots=failures))
                for path in paths:
                    fresh = witness(path, evidence)
                    variant = fresh['document']['u4b_runtime']
                    suffix = '[u4b-runtime]' if variant else '[historical-runtime]'
                    require(sum(case['name'] == TARGET + suffix and case['status'] == 'passed'
                                for case in cases) == 1, 'raw witness lacks its unique passed runtime case')
                    require(variant not in seen, 'duplicate runtime variant across supplied runs')
                    seen.add(variant)
                    row = compare(frozen[variant]['document']['changed_lines'], fresh['document']['changed_lines'])
                    row.update(u4b_runtime=variant, frozen=frozen[variant], fresh=fresh)
                    row['stop_at_d126_item'] |= not fresh['exact_eleven_line_witness']
                    result['comparisons'].append(row)
            expected = [(case, run) for run in result['runs'] for case in run['cases']]
            complete = (1 <= len(expected) <= 2 and len(seen) == len(expected)
                        and all(case['status'] == 'passed' for case, _ in expected))
            stop = not complete or any(row['stop_at_d126_item'] for row in result['comparisons'])
            result.update(status='stop_at_d126_item' if stop else 'supplied_d126_coordinates_unchanged',
                          stop_at_d126_item=stop, supplied_cases_complete=complete,
                          runtime_variants_reviewed=sorted(seen), both_runtime_variants_reviewed=seen == {False, True})
            code = 1 if stop else 0
        evidence.verify()
    except Exception as error:
        code = 2
        result.update(status='refused_incomplete_evidence', stop_at_d126_item=True,
                      error=type(error).__name__ + ': ' + str(error))
    result['evidence_files'] = list(evidence.files.values())
    result['helper_sha256'] = sha(Path(__file__).read_bytes())
    quiet()
    raw = (json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    with args.out.open('xb') as stream:
        stream.write(raw)
    require(args.out.read_bytes() == raw, 'output did not persist unchanged')
    print(json.dumps(dict(path=str(args.out), bytes=len(raw), sha256=sha(raw),
                         status=result['status'], stop_at_d126_item=result['stop_at_d126_item'])))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
