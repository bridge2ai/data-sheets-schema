#!/usr/bin/env python3
"""Summarize saved U3-C4 validation and scope evidence, 2026-11-07.

Inputs: immediate run directories below scratch-native-u3c-r4 and local Git
objects. Output: one new JSON manifest below that scratch root. Retain B smoke
JSON files before cases cleanup, without overwriting evidence or deleting any
file. No tests, production imports, network, provider or native calls.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3c-r4'
BASE = '1e784ed9101d4f43e6115ca60d4f0ebc14dae308'
MERGE = 'ea1689e96372da5d5d33f40ba6b02103012f9a3d'
AUTHORITY = 'src/data_sheets_schema/native_execution_authority_v2.py'
REGISTRATION = 'src/data_sheets_schema/native_execution_registration_v2.py'
SMOKES = frozenset(('cpu-smoke.json', 'cpu-smoke-assembly.json'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > 128 * 1024 * 1024:
            raise ValueError('not a bounded regular evidence file: ' + str(path))
        raw = stream.read()
        after = os.fstat(stream.fileno())
    fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    current = path.lstat()
    if any(getattr(before, key) != getattr(after, key) or
           getattr(after, key) != getattr(current, key) for key in fields):
        raise ValueError('evidence changed while reading: ' + str(path))
    return raw


def artifact(path):
    raw = read(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def save_new(path, raw):
    path = Path(path)
    if not path.parent.resolve(strict=True).is_relative_to(SCRATCH.resolve(strict=True)):
        raise ValueError('output must stay inside C4 scratch')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if read(path) != raw:
        raise ValueError('persisted output differs: ' + str(path))


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode()


def retain_smokes(directory):
    cases, retained = directory / 'cases', directory / 'retained-smoke'
    manifest = retained / 'manifest.json'
    if manifest.exists():
        value = json.loads(read(manifest))
        for item in value['files']:
            relative = Path(item['retained_relative'])
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('unsafe retained smoke path')
            path = retained / relative
            if path.resolve(strict=True) != path.absolute():
                raise ValueError('symlink in retained smoke path')
            pin = artifact(path)
            if (pin['bytes'], pin['sha256']) != (item['bytes'], item['sha256']):
                raise ValueError('retained smoke evidence changed')
        return {'manifest': artifact(manifest), **value, 'cases_present': cases.exists()}
    found = []
    if cases.exists():
        if cases.is_symlink():
            raise ValueError('cases root is a symlink')
        for parent, dirs, files in os.walk(cases, followlinks=False):
            dirs[:] = [name for name in dirs if not (Path(parent) / name).is_symlink()]
            for name in sorted(SMOKES.intersection(files)):
                source = Path(parent) / name
                if source.resolve(strict=True) != source.absolute():
                    raise ValueError('symlink in smoke evidence path')
                raw = read(source)
                json.loads(raw)
                found.append((source.relative_to(cases), raw))
    if not found:
        return {'files': [], 'cases_present': cases.exists(),
                'limitation': 'No retained smoke evidence; absence after cases removal proves nothing.'}
    retained.mkdir(exist_ok=False)
    rows = []
    for relative, raw in sorted(found):
        target = retained / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        save_new(target, raw)
        rows.append({'source_relative': str(Path('cases') / relative),
                     'retained_relative': str(relative), 'bytes': len(raw), 'sha256': sha(raw)})
    value = {'version': 1, 'files': rows}
    save_new(manifest, encoded(value))
    return {'manifest': artifact(manifest), **value, 'cases_present': True}


def summarize_run(directory):
    result = {'directory': str(directory), 'artifacts': {}, 'evidence_errors': []}
    for name in ('plan.json', 'outcome.json', 'worker-outcome.json', 'source-stability.json',
                 'pytest.xml', 'pytest.log', 'pytest-command.json', 'network.json',
                 'origins-before.json', 'origins-after.json', 'subprocess-origins.json'):
        path = directory / name
        if path.exists():
            result['artifacts'][name] = artifact(path)
    for name in ('plan', 'outcome', 'source-stability'):
        path = directory / (name + '.json')
        if path.exists():
            result[name.replace('-', '_')] = json.loads(read(path))
    result['tested_commit'] = result.get('plan', {}).get('source_commit')
    cases = []
    xml = directory / 'pytest.xml'
    if xml.exists():
        tree = ET.fromstring(read(xml))
        for number, item in enumerate(tree.iter('testcase')):
            status = ('errors' if item.find('error') is not None else
                      'failed' if item.find('failure') is not None else
                      'skipped' if item.find('skipped') is not None else 'passed')
            detail = item.find('error') if status == 'errors' else item.find('failure')
            if status == 'skipped': detail = item.find('skipped')
            cases.append({'ordinal': number, 'classname': item.get('classname', ''),
                'name': item.get('name', ''), 'status': status, 'seconds': item.get('time'),
                'message': None if detail is None else detail.get('message'),
                'detail': None if detail is None else detail.text})
        counts = Counter(row['status'] for row in cases)
        result['counts'] = {key: counts[key] for key in ('passed', 'failed', 'errors', 'skipped')}
        result['testcases'] = cases
        result['junit_suites'] = [dict(node.attrib) for node in tree.iter('testsuite')]
        duplicate = Counter((row['classname'], row['name']) for row in cases)
        result['repeated_case_names'] = [{'classname': key[0], 'name': key[1], 'occurrences': n}
                                        for key, n in duplicate.items() if n > 1]
    log = directory / 'pytest.log'
    if log.exists():
        text = read(log).decode('utf-8', errors='replace')
        result['collection_count_observations'] = re.findall(r'\b(\d+) tests? collected\b', text)
        result['terminal_summary_lines'] = [line for line in text.splitlines()
            if re.search(r'\b\d+ (passed|failed|errors?|skipped|deselected|tests? collected)\b', line)][-12:]
    outcome = result.get('outcome', {})
    stable = result.get('source_stability', {})
    result['literal_test_pass'] = bool(cases and all(row['status'] == 'passed' for row in cases)
        and outcome.get('returncode') == 0 and outcome.get('cleanup_verified') is True
        and outcome.get('observed_surviving_pids') == []
        and outcome.get('worker', {}).get('source_origin_checks_passed') is True
        and stable.get('unchanged') is True)
    result['counting_scope'] = 'Actual JUnit testcase outcomes for this run only; no cross-run sum.'
    result['retained_smoke'] = retain_smokes(directory)
    for relative in ('graph-census/census.json', 'census.json'):
        path = directory / relative
        if path.exists():
            value = json.loads(read(path))
            result['graph_census'] = {'artifact': artifact(path), 'evidence': value}
            break
    return result


def git(*arguments, missing=False):
    env = {'PATH': '/usr/bin:/bin', 'GIT_NO_LAZY_FETCH': '1', 'GIT_ALLOW_PROTOCOL': '',
           'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}
    result = subprocess.run(['/usr/bin/git', '--no-replace-objects', *arguments], cwd=ROOT,
        env=env, capture_output=True, timeout=30, check=False)
    if result.returncode:
        if missing: return None
        raise ValueError('local Git read failed: ' + result.stderr.decode(errors='replace'))
    return result.stdout


def blob(ref, path):
    return git('show', ref + ':' + path, missing=True)


def scope_evidence():
    head = git('rev-parse', 'HEAD').decode().strip()
    names = git('ls-tree', '-r', '--name-only', BASE).decode().splitlines()
    protected = {path for path in names if path.endswith('/canonical_hashes.yaml')}
    protected.add('src/data_sheets_schema/shared_generation.py')
    frozen = {path for path in names if path.startswith('src/data_sheets_schema/native_')
        and path.endswith('.py') and path.rsplit('/', 1)[-1].startswith(
            ('native_execution', 'native_attribution', 'native_supervisor', 'native_attempt_supervisor'))}
    frozen -= {AUTHORITY, REGISTRATION}
    frozen.update(('src/data_sheets_schema/native_controller_sources_v1.json',
                   'src/data_sheets_schema/native_controller_sources_v2.json',
                   'notes/claudecode_direct/prepare_direct_v2.py',
                   'notes/claudecode_direct/prepare_direct.py',
                   'notes/claudecode_direct/run_direct_canary_awake.py'))
    for manifest in ('native_controller_sources_v1.json', 'native_controller_sources_v2.json'):
        value = json.loads(blob(BASE, 'src/data_sheets_schema/' + manifest))
        frozen.update(row['path'] for row in value['modules'].values())

    def compare(paths, reference):
        rows = []
        for path in sorted(paths):
            before, after = blob(reference, path), blob(head, path)
            actual = ROOT / path
            rows.append({'path': path, 'reference_exists': before is not None,
                'reference_sha256': None if before is None else sha(before),
                'head_sha256': None if after is None else sha(after),
                'unchanged': before is not None and before == after,
                'working_file': artifact(actual) if actual.is_file() and not actual.is_symlink() else None})
        return rows

    before, after = ast.parse(blob(MERGE, AUTHORITY)), ast.parse(blob(head, AUTHORITY))
    def without_roster(tree):
        found = [node for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'CONSUMER_OWNED_MODULES' for t in node.targets)]
        if len(found) != 1: raise ValueError('authority roster assignment is not unique')
        tree.body.remove(found[0])
        return ast.dump(tree, include_attributes=False), ast.unparse(found[0])
    old_ast, old_roster = without_roster(before)
    new_ast, new_roster = without_roster(after)
    changed = git('diff', '--name-only', BASE, head, '--', 'src', 'scripts/adhoc').decode().splitlines()
    return {'head': head, 'head_and_parents': git('show', '-s', '--format=%H %P', head).decode().strip(),
        'base': BASE, 'a4_merge': MERGE,
        'merge_commits_and_parents': git('log', '--merges', '--format=%H %P', BASE + '..' + head).decode().splitlines(),
        'working_status': git('status', '--porcelain', '--untracked-files=all').decode(),
        'protected': compare(protected, BASE), 'frozen_v1_u2_and_pinned_helpers': compare(frozen, BASE),
        'a_registration': compare([REGISTRATION], MERGE),
        'a_authority_only_roster_ast_changed': old_ast == new_ast,
        'a_authority_roster_before': old_roster, 'a_authority_roster_after': new_roster,
        'changed_sources': compare(changed, BASE)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise ValueError('summary output already exists')
    runs = []
    for directory in sorted(SCRATCH.iterdir()):
        if directory.is_dir() and not directory.is_symlink() and (directory / 'outcome.json').is_file():
            try:
                runs.append(summarize_run(directory))
            except Exception as exc:
                runs.append({'directory': str(directory), 'evidence_errors': [type(exc).__name__ + ': ' + str(exc)],
                             'literal_test_pass': False})
    value = {'created_utc': datetime.now(timezone.utc).isoformat(), 'version': 1,
        'script': artifact(Path(__file__)), 'scratch': str(SCRATCH), 'runs': runs,
        'git_scope': scope_evidence(),
        'limits': ['No tests or measurements rerun.', 'No pass inferred from exit zero alone.',
                   'Repeated runs are separate evidence; counts are never added across runs.',
                   'A successful import census does not prove projection lifetime or D execution admission.']}
    save_new(args.out, encoded(value))
    print(json.dumps(artifact(args.out), sort_keys=True))


if __name__ == '__main__':
    main()
