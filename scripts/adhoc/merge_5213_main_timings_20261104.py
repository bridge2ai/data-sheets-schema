#!/usr/bin/env python3
"""#5213 round 6, 2026-11-04: deterministic timing union and offline evidence.

Inputs: exact preview/main Git blobs and retained validation artifacts. Outputs:
one timing-file union, fresh external audits/plans/comparisons. No measurement
is invented or relabelled. No network, Git mutation, provider or test execution.
Only --install writes the named conflicted timing file in the assigned branch.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = '2482dbdb6a02184d1d1b44cd556c0003d8f4af89'
MAIN = '6d6031792e914088823a5204f09fac6c6c1106f6'
BASE = '0ff5c9ba7665eb51b69e597c391cb1ae6a07c44c'
BRANCH = 'codex/wave7-5213-path-identity-20261031'
TIMINGS = 'utils/ci_test_durations.json'
SELF = 'scripts/adhoc/merge_5213_main_timings_20261104.py'
EVIDENCE = ROOT.parent / 'plans/reviews/pr5213_main_merge_2026-11-04'
PINS = {PREVIEW: '66797c02b0519074503825a67a3ea4026751da581a77cdcaa8b5388b2bc975e8',
        MAIN: '845434a3e72483fb81a16d1634e84b06040d4d5864a3cb6cd2720bcd2c716305'}
R5_PLAN = '1504815456da5e84f9ceb552e09af329df3bf2de72f91d3b6deec23a32f22e3e'
R5_SCAN = '087905dedc7dd4e4695d784f1e213b3cd59778550e3baca32cae5d968b81c756'
SCOPE = '3583bc40dbf800bf419899e2ae8dcb6ad4020e1ae46d624f34cd2406c2f29112'
CONTRACTS = ['scripts/adhoc/test_refresh_pr5213_integration_timings_20261103.py',
             'scripts/adhoc/test_plan_pr5213_integration_20261102.py']


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def exact(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(exact(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(exact(x, y) for x, y in zip(a, b))
    return a == b


def pairs(values):
    out = {}
    for key, value in values:
        require(key not in out, 'duplicate JSON key: ' + key)
        out[key] = value
    return out


def invalid(value):
    raise ValueError('invalid JSON constant: ' + value)


def decode(raw):
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + '\n').encode()


def save(path, value):
    with path.open('xb') as stream:
        stream.write(encode(value))


def git(*args, tree=ROOT):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0',
               GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')
    return subprocess.check_output(['git', '--no-replace-objects', '-c',
        'protocol.allow=never', '-C', str(tree), *args], env=env)


def check_release_identity(head, parents, archive_head, archived_commit):
    require(parents == [PREVIEW, MAIN], 'released merge parents differ')
    require(head not in (PREVIEW, MAIN) and len(head) == 40, 'released merge required')
    require(archive_head == archived_commit == head, 'archive is not the released merge')


def released_tree(tree):
    require(git('branch', '--show-current').decode().strip() == BRANCH, 'wrong author branch')
    require(not git('status', '--porcelain'), 'released producer must be clean')
    head = git('rev-parse', 'HEAD').decode().strip()
    parents = git('show', '-s', '--format=%P', head).decode().split()
    tree = tree.resolve(strict=True)
    require(tree.is_relative_to(ROOT.parent / 'scratch-bc1g2'), 'pinned scratch archive required')
    archive_head = git('rev-parse', 'HEAD', tree=tree).decode().strip()
    check_release_identity(head, parents, archive_head, decode((tree / '.g2-archive.json').read_bytes())['commit'])
    require(not git('diff', 'HEAD', '--', tree=tree), 'archive tracked source differs')
    require(git('rev-parse', 'HEAD^{tree}', tree=tree) == git('rev-parse', 'HEAD^{tree}'),
            'archive tree identity differs')
    for path in ('src/data_sheets_schema/shared_generation.py',
                 'src/download/prompts/canonical_hashes.yaml', SELF):
        require((tree / path).read_bytes() == git('show', head + ':' + path),
                'released archive file differs: ' + path)
    return head, tree


def physical_output(path):
    require(path.is_absolute() and '..' not in path.parts and path.is_relative_to(EVIDENCE),
            'output must be under the approved external evidence directory')
    require(path.resolve() == path and not path.is_symlink(), 'symlinked evidence destination')


def physical_target(path):
    require(path.parent.resolve(strict=True) == path.parent, 'symlinked timing parent')
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode), 'timing target must be a physical regular file')
    return info


def replace_regular(path, data):
    before_stat = physical_target(path)
    before = path.read_bytes()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.round6-timings-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        after_stat = physical_target(path)
        require((before_stat.st_dev, before_stat.st_ino) == (after_stat.st_dev, after_stat.st_ino)
                and path.read_bytes() == before, 'timing target changed during installation')
        os.chmod(temporary, stat.S_IMODE(before_stat.st_mode))
        os.replace(temporary, path)
        require(path.read_bytes() == data, 'installed timing bytes differ')
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def members(raw):
    """Return literal JSON value slices; preserve provenance and numeric tokens."""
    text = raw.decode() if isinstance(raw, bytes) else raw
    decode(text)
    decoder = json.JSONDecoder(object_pairs_hook=pairs, parse_constant=invalid)
    i = 0
    while text[i].isspace():
        i += 1
    require(text[i] == '{', 'JSON object required')
    i += 1
    result = {}
    while True:
        while text[i].isspace():
            i += 1
        if text[i] == '}':
            require(not text[i + 1:].strip(), 'trailing object content')
            return result
        key, i = decoder.raw_decode(text, i)
        while text[i].isspace():
            i += 1
        require(text[i] == ':', 'missing JSON colon')
        i += 1
        while text[i].isspace():
            i += 1
        start = i
        _, i = decoder.raw_decode(text, i)
        result[key] = text[start:i]
        while text[i].isspace():
            i += 1
        if text[i] == ',':
            i += 1
        else:
            require(text[i] == '}', 'missing JSON object delimiter')


def object_text(values, indent=2):
    return ('{\n' + ',\n'.join(' ' * indent + json.dumps(k) + ': ' + v for k, v in values.items())
            + '\n' + ' ' * (indent - 2) + '}')


def union(preview_raw, main_raw):
    old, new = decode(preview_raw), decode(main_raw)
    require(set(old) == {'schema_version', 'source', 'method', 'file_seconds', 'local_overrides'},
            'unexpected preview metadata')
    require(set(new) == {'schema_version', 'source', 'method', 'file_seconds'},
            'unexpected main metadata')
    require(type(old['schema_version']) is int and old['schema_version'] == 1
            and exact(old['schema_version'], new['schema_version']), 'schema version differs')
    for key, value in old['source'].items():
        require(key in new['source'] and exact(value, new['source'][key]),
                'historical source provenance conflict: ' + key)
    for record in (old, new):
        require(type(record['file_seconds']) is dict, 'weight map required')
        for path, weight in record['file_seconds'].items():
            require(type(path) is str and path.startswith('tests/') and path.endswith('.py')
                    and '..' not in Path(path).parts, 'invalid weight path')
            require(type(weight) in (int, float) and math.isfinite(weight) and weight > 0,
                    'invalid positive finite timing: ' + path)
    require(type(old['local_overrides']) is list and old['local_overrides'], 'local provenance required')
    local = {}
    for index, block in enumerate(old['local_overrides']):
        require(type(block['file_seconds']) is dict, 'local measurement weights missing')
        for path, value in block['file_seconds'].items():
            local[path] = (index, value, block['measured_commit'])
    current = new['source']['bc1_g2_all_files_20261104']['files']
    rows = []
    selected = {}
    for path in sorted(old['file_seconds'].keys() | new['file_seconds'].keys()):
        before = old['file_seconds'].get(path)
        after = new['file_seconds'].get(path)
        row = {'path': path, 'preview': before, 'main': after}
        if after is None:
            require(path in local and exact(local[path][1], before),
                    'preview-only weight lacks matching local measurement: ' + path)
            selected[path] = ('preview', before)
            row.update(rule='5213_local_only_measurement', local_override_index=local[path][0],
                       measured_commit=local[path][2])
        elif before is None:
            require(path in current and exact(current[path]['seconds'], after),
                    'main-only weight lacks current provenance: ' + path)
            selected[path] = ('main', after)
            row.update(rule='bc1g2_current_weight_with_retained_lineage',
                       value_kind=current[path]['value_kind'], source=current[path]['source'])
        elif exact(before, after):
            selected[path] = ('main', after)
            row['rule'] = 'identical_parent_weight'
        else:
            proof = current.get(path, {})
            require(proof.get('value_kind') == 'measured'
                    and proof.get('source') in {'41735860489', '41707437114'}
                    and exact(proof.get('seconds'), after)
                    and type(proof.get('collected_cases')) is int
                    and proof['collected_cases'] > 0
                    and sum(proof.get('outcomes', {}).values()) == proof['collected_cases'],
                    'conflicting weights lack declared complete-CI precedence: ' + path)
            selected[path] = ('main', after)
            row.update(rule='bc1g2_round3_complete_ci_supersedes_prior',
                       source=proof['source'], value_kind=proof['value_kind'])
        row['selected'] = selected[path][1]
        rows.append(row)
    old_parts, new_parts = members(preview_raw), members(main_raw)
    numeric = {'preview': members(old_parts['file_seconds']),
               'main': members(new_parts['file_seconds'])}
    source_parts = members(new_parts['source'])
    for key, raw_value in members(old_parts['source']).items():
        require(source_parts[key] == raw_value, 'historical source bytes differ: ' + key)
    metadata = {
        'kind': 'parent_weight_union_not_new_measurement', 'date': '2026-11-04',
        'preview_commit': PREVIEW, 'main_commit': MAIN,
        'preview_timing_sha256': sha(preview_raw), 'main_timing_sha256': sha(main_raw),
        'preview_method': old['method'], 'main_method': new['method'],
        'producer_path': SELF, 'producer_sha256': sha(Path(__file__).read_bytes()),
        'rules': sorted({row['rule'] for row in rows}),
        'dispositions': rows,
        'limits': 'No fresh measurement. Historical source identities, retirements and all outcomes remain literal. Obsolete weights are ignored by collection; absent weights retain the existing median fallback.'}
    out_parts = dict(new_parts)
    # Numeric token spellings are taken literally from the chosen parent.
    out_parts['file_seconds'] = object_text({path: numeric[owner][path]
                                           for path, (owner, _) in selected.items()}, indent=4)
    out_parts['local_overrides'] = old_parts['local_overrides']
    out_parts['union_provenance'] = encode(metadata).decode().rstrip('\n')
    output = (object_text(out_parts) + '\n').encode()
    parsed, literal = decode(output), members(output)
    require(set(parsed['file_seconds']) == set(selected), 'weight union differs')
    require(all(exact(parsed['file_seconds'][p], value) for p, (_, value) in selected.items()),
            'selected weight changed')
    require(literal['source'] == new_parts['source'] and literal['method'] == new_parts['method']
            and literal['local_overrides'] == old_parts['local_overrides'], 'provenance bytes changed')
    require(members(literal['union_provenance'])['preview_method'] == old_parts['method'],
            'preview method bytes changed')
    return output, {'inputs': metadata | {'dispositions': None}, 'dispositions': rows,
                    'file_count': len(selected), 'rules': dict(Counter(r['rule'] for r in rows)),
                    'output_sha256': sha(output), 'verbatim_source_sha256': sha(literal['source'].encode()),
                    'verbatim_local_overrides_sha256': sha(literal['local_overrides'].encode())}


def make_union(args):
    require(not args.output.exists(), 'fresh evidence directory required')
    raw = {ref: git('show', ref + ':' + TIMINGS) for ref in (PREVIEW, MAIN)}
    require(all(sha(value) == PINS[ref] for ref, value in raw.items()), 'input timing pin differs')
    result, proof = union(raw[PREVIEW], raw[MAIN])
    args.output.mkdir(parents=True)
    for name, contents in [('preview.json', raw[PREVIEW]), ('main.json', raw[MAIN]), ('union.json', result)]:
        with (args.output / name).open('xb') as stream:
            stream.write(contents)
    save(args.output / 'union-audit.json', proof)
    if args.install:
        require(git('branch', '--show-current').decode().strip() == BRANCH, 'wrong author branch')
        require(git('rev-parse', 'HEAD').decode().strip() == PREVIEW
                and git('rev-parse', 'MERGE_HEAD').decode().strip() == MAIN, 'wrong merge parents')
        require(git('diff', '--name-only', '--diff-filter=U').decode().splitlines() == [TIMINGS],
                'unexpected conflict roster')
        for stage, expected in ((2, raw[PREVIEW]), (3, raw[MAIN])):
            require(git('show', ':' + str(stage) + ':' + TIMINGS) == expected, 'wrong index side')
        physical_target(ROOT / TIMINGS)
        with (args.output / 'working-conflict-before.txt').open('xb') as stream:
            stream.write((ROOT / TIMINGS).read_bytes())
        replace_regular(ROOT / TIMINGS, result)
        require((ROOT / TIMINGS).read_bytes() == result, 'installed union differs')
    print(json.dumps({'output': str(args.output), 'sha256': sha(result),
                      'files': proof['file_count'], 'rules': proof['rules'], 'installed': args.install}))


def selfcheck(args):
    """Exercise actual-parent preservation and adversarial input refusals in memory."""
    raw_old, raw_new = (git('show', ref + ':' + TIMINGS) for ref in (PREVIEW, MAIN))
    require(sha(raw_old) == PINS[PREVIEW] and sha(raw_new) == PINS[MAIN], 'input pin differs')
    before, after = decode(raw_old), decode(raw_new)
    first, proof = union(raw_old, raw_new)
    require(union(raw_old, raw_new)[0] == first, 'union is not deterministic')
    rows = [{'case': 'actual_parent_union_deterministic_and_verbatim', 'passed': True}]
    local_path = next(p for p in before['file_seconds'] if p not in after['file_seconds'])
    shared_path = next(p for p in before['file_seconds'] if p in after['file_seconds']
                       and not exact(before['file_seconds'][p], after['file_seconds'][p]))

    def refused(name, old, new, message):
        try:
            union(old, new)
        except ValueError as exc:
            require(message in str(exc), name + ': unexpected refusal ' + str(exc))
            rows.append({'case': name, 'passed': True, 'refusal': str(exc)})
        else:
            raise ValueError('mutation was accepted: ' + name)

    old = deepcopy(before)
    old['file_seconds'][local_path] += 1
    refused('unproven_preview_only_measurement', encode(old), raw_new, 'lacks matching local measurement')
    new = deepcopy(after)
    new['file_seconds'][shared_path] += 1
    refused('overlap_weight_not_matching_measurement', raw_old, encode(new), 'complete-CI precedence')
    for field, value in [('source', 'retained-current'), ('value_kind', 'estimated'), ('collected_cases', -1)]:
        new = deepcopy(after)
        new['source']['bc1_g2_all_files_20261104']['files'][shared_path][field] = value
        refused('overlap_invalid_' + field, raw_old, encode(new), 'complete-CI precedence')
    new = deepcopy(after)
    new['source']['commit'] = 'f' * 40
    refused('historical_provenance_relabel', raw_old, encode(new), 'historical source provenance conflict')
    for value in (True, -1, 0, '1'):
        old = deepcopy(before)
        old['file_seconds'][local_path] = value
        refused('invalid_weight_' + repr(value), encode(old), raw_new, 'invalid positive finite timing')
    duplicate = raw_old.replace(b'"schema_version": 1,', b'"schema_version": 1, "schema_version": 1,', 1)
    refused('duplicate_json_key', duplicate, raw_new, 'duplicate JSON key')
    for token in ('NaN', 'Infinity', '-Infinity'):
        value = raw_old.replace(b'"schema_version": 1,', ('"schema_version": ' + token + ',').encode(), 1)
        refused('nonfinite_' + token, value, raw_new, 'invalid JSON constant')
    fixtures = args.output.with_name(args.output.stem + '-fixtures')
    fixtures.mkdir()

    def rejects(name, action, message):
        try:
            action()
        except ValueError as exc:
            require(message in str(exc), name + ': unexpected refusal ' + str(exc))
            rows.append({'case': name, 'passed': True, 'refusal': str(exc)})
        else:
            raise ValueError('mutation was accepted: ' + name)

    check_release_identity('a' * 40, [PREVIEW, MAIN], 'a' * 40, 'a' * 40)
    rejects('stale_archive', lambda: check_release_identity('a' * 40, [PREVIEW, MAIN], PREVIEW, PREVIEW),
            'not the released merge')
    rejects('wrong_release_parents', lambda: check_release_identity('a' * 40, [MAIN, PREVIEW], 'a' * 40, 'a' * 40),
            'parents differ')
    victim = fixtures / 'untouched.txt'
    victim.write_bytes(b'retained input\n')
    link = fixtures / 'symlink.json'
    link.symlink_to(victim)
    rejects('symlink_install_refusal', lambda: replace_regular(link, b'unwanted\n'), 'physical regular file')
    require(victim.read_bytes() == b'retained input\n', 'symlink victim changed')
    alias = fixtures / 'symlink-parent'
    alias.symlink_to(fixtures, target_is_directory=True)
    rejects('symlink_parent_install_refusal', lambda: replace_regular(alias / 'untouched.txt', b'unwanted'),
            'symlinked timing parent')
    rejects('source_evidence_refusal', lambda: physical_output(ROOT / 'unexpected.json'), 'external evidence directory')
    rejects('symlink_evidence_refusal', lambda: physical_output(alias / 'result.json'), 'symlinked evidence')
    regular = fixtures / 'regular.json'
    regular.write_bytes(b'before\n')
    replace_regular(regular, b'after\n')
    require(regular.read_bytes() == b'after\n', 'atomic regular installation failed')
    rows.append({'case': 'atomic_regular_installation', 'passed': True})
    false_result = fixtures / 'scanner-mismatch.json'
    rejects('scanner_mismatch_persisted', lambda: persist_comparison(false_result, {'synthetic': True},
            {'violations': {'equal': False, 'baseline': [1], 'candidate': [2],
                            'positional_differences': [{'index': 0}]}}), 'false comparison persisted')
    require(decode(false_result.read_bytes())['passed_vs_preview'] is False, 'false comparison was not saved')
    one_node = CONTRACTS[0] + '::JoinMeasurements::test_example'
    expected = collected_contract_nodes([one_node, one_node])
    right = [ET.Element('testcase', classname=CONTRACTS[0][:-3].replace('/', '.') + '.JoinMeasurements',
                        name='test_example') for _ in range(2)]
    require(junit_contract_nodes(right) == expected, 'duplicate JUnit identity lost')
    wrong = deepcopy(right)
    wrong[1].set('name', 'test_unrelated')
    rejects('same_count_wrong_junit_identity', lambda: require(junit_contract_nodes(wrong) == expected,
            'contract JUnit identities differ'), 'JUnit identities differ')
    rows.append({'case': 'duplicate_contract_identities_preserved', 'passed': True})
    command = [str(ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'), '-S', '-B',
               str(ROOT / 'scripts/adhoc/g2_bc1_offline_20261101.py'), 'pytest', *CONTRACTS,
               '-q', '--collect-only', '-p', 'no:cacheprovider',
               '--basetemp=' + str(fixtures / 'tmp'), '--junitxml=' + str(fixtures / 'junit.xml')]
    started = {'deadline_seconds': 3600, 'command': command}
    contract_command(started, True, fixtures)
    selected = deepcopy(started)
    selected['command'][7:7] = ['-k', 'one']
    rejects('filtered_contract_collection_refused', lambda: contract_command(selected, True, fixtures),
            'unexpected selectors')
    save(args.output, {'passed': True, 'checks': rows, 'count': len(rows),
                       'actual_union_sha256': sha(first), 'rules': proof['rules'],
                       'producer_sha256': sha(Path(__file__).read_bytes())})
    print(json.dumps({'checks': len(rows), 'output': str(args.output), 'sha256': sha(args.output.read_bytes())}))


def audit_tree(args):
    require(not git('status', '--porcelain'), 'clean merged worktree required')
    head = git('rev-parse', 'HEAD').decode().strip()
    require(git('show', '-s', '--format=%P', head).decode().split() == [PREVIEW, MAIN],
            'merge parents differ')
    require(git('merge-base', PREVIEW, MAIN).decode().strip() == BASE, 'merge base differs')
    incoming = set(git('diff', '--name-only', BASE, MAIN).decode().splitlines())
    actual = set(git('diff', '--name-only', PREVIEW, head).decode().splitlines())
    require(actual == incoming | {SELF}, 'unexpected file delta: ' + repr(actual ^ (incoming | {SELF})))
    rows = []
    for path in sorted(actual):
        raw = git('show', head + ':' + path)
        if path not in {TIMINGS, SELF}:
            require(raw == git('show', MAIN + ':' + path), 'main delta changed: ' + path)
        rows.append({'path': path, 'sha256': sha(raw),
                     'rule': 'required_union_producer' if path == SELF else
                             'weights_union' if path == TIMINGS else 'byte_identical_main_delta'})
    expected, _ = union(git('show', PREVIEW + ':' + TIMINGS), git('show', MAIN + ':' + TIMINGS))
    require(git('show', head + ':' + TIMINGS) == expected, 'union no longer reproduces')
    save(args.output, {'head': head, 'tree': git('rev-parse', 'HEAD^{tree}').decode().strip(),
                       'parents': [PREVIEW, MAIN], 'merge_base': BASE, 'files': rows,
                       'file_count': len(rows), 'producer_sha256': sha(Path(__file__).read_bytes())})
    print(json.dumps({'audit': str(args.output), 'files': len(rows), 'sha256': sha(args.output.read_bytes())}))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_plan(args):
    require(sha(args.preview_plan.read_bytes()) == R5_PLAN, 'preview plan pin differs')
    require(sha(args.scope.read_bytes()) == SCOPE, 'frozen BC1 scope differs')
    old, scope = decode(args.preview_plan.read_bytes()), decode(args.scope.read_bytes())
    head, tree = released_tree(args.tree)
    require(not args.output.exists() and not args.output.resolve().is_relative_to(tree),
            'fresh external plan directory required')
    names = ['canary', 'full-collection', 'd76-without-sg2', 'sg2-none', 'sg2-explicit',
             'sg2-conventional', 'bc1-04', 'bc1-09', 'bc1-10', 'bc1-11', 'bc1-ci-sharding']
    runs = {name: deepcopy(old['runs'][name]) for name in names}
    for index in (4, 9, 10, 11):
        require(runs[f'bc1-{index:02d}']['targets'] ==
                [p for p in scope['groups'][index] if p != 'tests/test_ci_sharding.py'],
                'frozen BC1 group differs')
    runs['timing-and-fixtures'] = {'targets': ['tests/test_ci_timing_update.py',
        'tests/test_record_required_values.py', 'tests/test_wave4_5095_review.py'], 'workers': 2}
    plan = deepcopy(old)
    plan.update(tree=str(tree), head=head, runs=runs,
                round6_producer={'path': SELF, 'sha256': sha(Path(__file__).read_bytes())},
                preview_plan_sha256=R5_PLAN,
                limits='Required round-six delta scope; overlapping canary/cohorts are observations. Offline macOS only; historical scanner baseline equality remains unmet.',
                separate_contract_files=CONTRACTS,
                changed_manifest_members={'tests/test_ci_sharding.py': 9,
                    'tests/test_preflight_resource_authority.py': 10, 'tests/test_g2_round2.py': 11})
    for key, relative in [('producer_sha256', 'scripts/adhoc/validate_5213_stack_preview_20261103.py'),
                          ('driver_sha256', 'scripts/adhoc/bc1_g2_validate_20261103.py'),
                          ('launcher_sha256', 'scripts/adhoc/g2_bc1_offline_20261101.py'),
                          ('sandbox_sha256', 'scripts/adhoc/d76_loopback_only_20261031.sb')]:
        require(sha((tree / relative).read_bytes()) == old[key], 'reviewed runner changed: ' + relative)
    require(all(sha((tree / p).read_bytes()) == value for p, value in old['protected_sha256'].items()),
            'protected source differs from preview')
    plan['coverage'] = {path: [n for n, row in runs.items() if path in row['targets']]
        for path in scope['files'] if any(t in path for t in ('specificity', 'test_profiles.py', 'test_generality_tuned.py'))}
    args.output.mkdir(parents=True)
    save(args.output / 'plan.json', plan)
    print(json.dumps({'plan': str(args.output / 'plan.json'), 'runs': len(runs),
                      'sha256': sha((args.output / 'plan.json').read_bytes())}))


def scanner_compare(args):
    require(sha(args.preview_scan.read_bytes()) == R5_SCAN, 'preview scanner report pin differs')
    comparator = load_module('round5_comparator', ROOT / 'scripts/adhoc/compare_5213_stack_scanner_20261103.py')
    before, after = decode(args.preview_scan.read_bytes()), decode(args.candidate_scan.read_bytes())
    require(before['commit'] == PREVIEW, 'wrong scanner preview commit')
    head, tree = released_tree(args.tree)
    require(after['commit'] == head and after['root'] == tree.name, 'wrong candidate scanner identity')
    for path in comparator.SOURCES:
        require((tree / path).read_bytes() == git('show', head + ':' + path),
                'scanner source differs: ' + path)
    old_arrays, new_arrays = comparator.report_arrays(before), comparator.report_arrays(after)
    comparisons = {name: comparator.comparison(old_arrays[name], new_arrays[name]) for name in old_arrays}
    persist_comparison(args.output, {'head': head, 'preview': PREVIEW, 'preview_report_sha256': R5_SCAN,
        'candidate_report_sha256': sha(args.candidate_scan.read_bytes()),
        'bc1_baseline_gate': 'unmet; owner retained exact equality',
        'producer_sha256': sha(Path(__file__).read_bytes())}, comparisons)
    print(json.dumps({'output': str(args.output), 'sha256': sha(args.output.read_bytes()), 'passed_vs_preview': True}))


def persist_comparison(output, metadata, comparisons):
    passed = all(row['equal'] for row in comparisons.values())
    save(output, metadata | {'comparisons': comparisons, 'passed_vs_preview': passed})
    require(passed, 'scanner differs from reviewed preview; false comparison persisted')


def contract_command(started, collection, directory):
    command = started['command']
    require(started['deadline_seconds'] == 3600, 'contract deadline differs')
    require(command[1:3] == ['-S', '-B'] and Path(command[3]).name == 'g2_bc1_offline_20261101.py'
            and command[4] == 'pytest' and command[5:7] == CONTRACTS, 'contract launcher/targets differ')
    require(command[0] == str(ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'),
            'contract interpreter differs')
    arguments = command[7:]
    fixed = ['-q'] + (['--collect-only'] if collection else
                      ['-n', '2', '--dist=load', '--maxschedchunk=1']) + ['-p', 'no:cacheprovider']
    require(arguments[:len(fixed)] == fixed and len(arguments) == len(fixed) + 2
            and arguments[-2] == '--basetemp=' + str(directory / 'tmp')
            and arguments[-1] == '--junitxml=' + str(directory / 'junit.xml'),
            'contract command has unexpected selectors or options')
    require(Path(command[3]).resolve() == ROOT / 'scripts/adhoc/g2_bc1_offline_20261101.py',
            'contract launcher source differs')


def junit_contract_nodes(cases):
    return Counter((case.attrib['classname'], case.attrib['name']) for case in cases)


def collected_contract_nodes(nodes):
    result = Counter()
    for node in nodes:
        parts = node.split('::')
        require(len(parts) >= 2 and parts[0].endswith('.py'), 'invalid contract node')
        classname = '.'.join([parts[0][:-3].replace('/', '.'), *parts[1:-1]])
        result[(classname, parts[-1])] += 1
    return result


def contract_summary(args):
    head, tree = released_tree(args.tree)
    full = decode((args.collection / 'collected.json').read_bytes())
    collection_result = decode((args.collection / 'result.json').read_bytes())
    result = decode((args.run / 'result.json').read_bytes())
    require(collection_result['returncode'] == result['returncode'] == 0, 'contract command failed')
    require(collection_result['identity'] == result['identity'], 'contract source identity differs')
    require(result['identity']['commit'] == head
            and result['identity'] == decode((tree / '.g2-archive.json').read_bytes()),
            'contract evidence is not the released merge')
    for directory, collection in ((args.collection, True), (args.run, False)):
        started = decode((directory / 'started.json').read_bytes())
        require(started['identity'] == result['identity'], 'contract start/result identity differs')
        contract_command(started, collection, directory)
        require(all(started['protected_hashes'][p] == sha((tree / p).read_bytes()) for p in
                    ('src/data_sheets_schema/shared_generation.py', 'notes/bc1_shared_generation_patch_2026-10-27.json')),
                'contract protected hash differs')
    require({n.split('::')[0] for n in full} == set(CONTRACTS), 'contract file roster differs')
    expected = Counter(full)
    events = [decode(line) for line in (args.run / 'events.jsonl').read_bytes().splitlines()]
    for phase in ('setup', 'call', 'teardown'):
        selected = [e for e in events if e['when'] == phase]
        require(Counter(e['nodeid'] for e in selected) == expected
                and all(e['outcome'] == 'passed' for e in selected), 'contract phase coverage differs')
    cases = list(ET.parse(args.run / 'junit.xml').iter('testcase'))
    require(len(cases) == sum(expected.values()) and not any(
        c.find(tag) is not None for c in cases for tag in ('failure', 'error', 'skipped')), 'contract XML differs')
    require(junit_contract_nodes(cases) == collected_contract_nodes(full), 'contract JUnit identities differ')
    files = {str(d / n): sha((d / n).read_bytes()) for d, names in [
        (args.collection, ['started.json', 'result.json', 'collected.json', 'pytest.log']),
        (args.run, ['started.json', 'result.json', 'events.jsonl', 'junit.xml', 'pytest.log'])] for n in names}
    save(args.output, {'identity': result['identity'], 'passed': len(cases), 'files': files,
                       'limits': 'Separate adhoc contracts; not credited to full tests/ collection.',
                       'producer_sha256': sha(Path(__file__).read_bytes())})
    print(json.dumps({'passed': len(cases), 'output': str(args.output), 'sha256': sha(args.output.read_bytes())}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    p = commands.add_parser('union')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--install', action='store_true')
    p = commands.add_parser('audit')
    p.add_argument('--output', type=Path, required=True)
    p = commands.add_parser('selfcheck')
    p.add_argument('--output', type=Path, required=True)
    p = commands.add_parser('plan')
    for flag in ('tree', 'output', 'preview-plan', 'scope'):
        p.add_argument('--' + flag, type=Path, required=True)
    p = commands.add_parser('scanner')
    for flag in ('tree', 'output', 'preview-scan', 'candidate-scan'):
        p.add_argument('--' + flag, type=Path, required=True)
    p = commands.add_parser('contracts')
    for flag in ('tree', 'collection', 'run', 'output'):
        p.add_argument('--' + flag, type=Path, required=True)
    args = parser.parse_args()
    physical_output(args.output)
    {'union': make_union, 'selfcheck': selfcheck, 'audit': audit_tree, 'plan': make_plan,
     'scanner': scanner_compare, 'contracts': contract_summary}[args.action](args)
