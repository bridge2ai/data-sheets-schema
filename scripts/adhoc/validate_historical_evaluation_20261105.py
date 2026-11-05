#!/usr/bin/env python3
"""Offline #5126 validation provenance, 2026-11-05.

Inputs: local commit archives, every A21 registration JSON (including sizing),
and explicit test targets. Outputs: fresh external JSON/log evidence. Reuses
the reviewed archive and deadline runner; never imports application code here.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = 'd0974d4bcc0f254272ec5a95e94d83ae801bbd38'
SCANNER = '.claude/skills/d4d-generation-specificity-audit/scan.py'
PRESERVED = ('data/d4d_concatenated', 'data/evaluation_llm', 'data/ATTIC',
             'src/download/prompts', 'data/rubric', '.claude/agents',
             'src/download/prompts/canonical_hashes.yaml',
             'src/data_sheets_schema/shared_generation.py')
ENV = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
ENV.update(GIT_NO_LAZY_FETCH='1', GIT_CONFIG_GLOBAL='/dev/null',
           GIT_CONFIG_NOSYSTEM='1', GIT_OPTIONAL_LOCKS='0',
           GIT_ALLOW_PROTOCOL='file', PYTHONDONTWRITEBYTECODE='1')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path.resolve()), 'bytes': len(raw), 'sha256': sha(raw)}


PRODUCER = pin(Path(__file__))


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key: ' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('nonfinite JSON constant: ' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def load(path):
    return decode(path.read_bytes())


def save(path, value):
    require(path.is_absolute() and not path.is_symlink(), 'literal absolute output required')
    require(not path.resolve().is_relative_to(ROOT), 'evidence must be outside worktree')
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    require(path.read_bytes() == raw, 'evidence persistence failed')
    print(json.dumps(pin(path)), flush=True)


def git(*args, root=ROOT):
    return subprocess.check_output(['git', '--no-replace-objects', '-c',
        'protocol.allow=never', '-C', str(root), *args], env=ENV)


def module(name):
    path = ROOT / 'scripts/adhoc' / name
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def archive_identity(tree):
    marker = load(tree / '.g2-archive.json')
    commit = marker['commit']
    require(re.fullmatch('[0-9a-f]{40}', commit), 'archive commit must be full SHA')
    require(git('rev-parse', 'HEAD', root=tree).decode().strip() == commit,
            'archive metadata differs')
    require(not git('diff', '--name-only', commit, '--', root=tree),
            'archive tracked source changed')
    return marker


def string_references(value, pointer='', embedded_depth=0):
    """Include path-valued keys as well as values, at every nesting depth."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield pointer + '/@key', key
            yield from string_references(child, pointer + '/' + key.replace('~', '~0').replace('/', '~1'), embedded_depth)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from string_references(child, pointer + '/' + str(index), embedded_depth)
    elif isinstance(value, str):
        yield pointer, value
        if value.lstrip().startswith(('{', '[')):
            require(len(value.encode()) <= 64 * 1024 * 1024 and embedded_depth < 8,
                    'embedded JSON reference exceeds the explicit inspection bound')
            try:
                nested = decode(value)
            except json.JSONDecodeError:
                return  # Ordinary prose/code is still tokenized by path_reference.
            yield from string_references(nested, pointer + '/@embedded_json', embedded_depth + 1)


def path_reference(value, source_root):
    # Literal paths are kept whole, including spaces. Text citations are also
    # tokenized so a path mentioned inside explanatory metadata is not missed.
    found = []
    if value.startswith('/') and '\n' not in value and '\r' not in value:
        path = Path(value)
        relative = path.relative_to(source_root).as_posix() if path.is_relative_to(source_root) else None
        found.append({'literal': value, 'relative': relative, 'basename': path.name})
    elif '/' in value and '://' not in value and not any(c.isspace() for c in value):
        found.append({'literal': value, 'relative': value.removeprefix('./'), 'basename': PurePosixPath(value).name})
    elif re.fullmatch(r'(?=.*[A-Za-z_])[A-Za-z0-9_.-]+\.[A-Za-z0-9]+', value):
        found.append({'literal': value, 'relative': None, 'basename': value})
    for match in re.finditer(r'(?<![\w/:])/(?:[^\s`\"\x27\\;,()<>\[\]{}]+)', value):
        literal = match.group().rstrip('.')
        path = Path(literal)
        if not any(row['literal'] == literal for row in found):
            relative = path.relative_to(source_root).as_posix() if path.is_relative_to(source_root) else None
            found.append({'literal': literal, 'relative': relative, 'basename': path.name})
    for match in re.finditer(r'(?<![\w/:])(?:src|data|notes|scripts|configs|docs|\.claude|\.github)/[^\s`\";,()<>\[\]{}]+', value):
        path = match.group().rstrip('.')
        if not any(row['literal'] == path for row in found):
            found.append({'literal': path, 'relative': path, 'basename': PurePosixPath(path).name})
    return found


def closure(args):
    files = sorted(args.registrations.glob('*.json'))
    require(files and any(p.name.endswith('.sizing.json') for p in files), 'registration/sizing JSONs required')
    source_root = args.registrations.resolve().parent
    references = []
    for path in files:
        document = load(path)
        for pointer, value in string_references(document):
            for row in path_reference(value, source_root):
                references.append({'document': path.name, 'pointer': pointer, **row})
    changed = set(git('diff', '--name-only', '--no-renames', args.base, args.head).decode().splitlines())
    if args.include_working:
        changed.update(git('diff', '--name-only', '--no-renames', args.head).decode().splitlines())
        changed.update(git('ls-files', '--others', '--exclude-standard').decode().splitlines())
    matches = [{'changed': path, **row} for path in sorted(changed) for row in references
               if path == row['relative'] or (row['relative'] is None and Path(path).name == row['basename'])]
    result = {'format': 'historical_evaluation_closure_check_v1', 'base': args.base,
        'head': git('rev-parse', args.head).decode().strip(), 'include_working': args.include_working,
        'producer': PRODUCER, 'registration_documents': [pin(p) for p in files],
        'reference_count': len(references), 'references': references,
        'relative_paths': sorted({row['relative'] for row in references if row['relative'] is not None}),
        'changed_paths': sorted(changed), 'matches': matches, 'passed': not matches,
        'limits': 'All literal path values/keys and path citations across every JSON, including sizing. Bare basenames conservatively conflict. This does not authorize edits to unnamed protected assets.'}
    save(args.output, result)
    require(not matches, 'changed paths intersect the registration references')


def preservation(args):
    changed = git('diff', '--name-only', '--no-renames', args.base, args.head, '--', *PRESERVED).decode().splitlines()
    trees = {ref: {prefix: sha(git('ls-tree', '-r', ref, '--', prefix)) for prefix in PRESERVED}
             for ref in (args.base, args.head)}
    save(args.output, {'format': 'historical_evaluation_preservation_v1', 'base': args.base,
        'head': git('rev-parse', args.head).decode().strip(), 'producer': PRODUCER,
        'changed_paths': changed, 'git_tree_listing_sha256': trees, 'passed': not changed,
        'limits': 'Committed object/path/mode preservation. Runtime fixture byte preservation is tested separately.'})
    require(not changed, 'preserved committed artifact changed')


def scanner_arrays(report):
    require(report['self_test']['passed'] is True and type(report['exit']) is int
            and report['exit'] == 1, 'scanner did not complete with retained violations')
    findings = report['violations']
    listed = report['facts']['model_facing_modules']['listed_not_derived']
    require(type(findings) is list and len(findings) == 24 and type(listed) is list,
            'expected 24 complete findings and module array')
    require(all(type(row) is dict and row.get('violation') is True and row.get('path')
                and row.get('gates_in') for row in findings), 'malformed finding')
    require(all(type(name) is str for name in listed), 'malformed module list')
    if 'totals' in report:
        require(type(report['totals']['violations']) is int and report['totals']['violations'] == 24,
                'summary total conflicts with complete finding array')
    return {'violations': findings, 'listed_not_derived': listed}


def scan(args):
    tree = args.tree.resolve(strict=True)
    identity = archive_identity(tree)
    output = args.output.resolve()
    require(not output.is_relative_to(tree) and not output.is_relative_to(ROOT), 'external output required')
    output.mkdir(parents=True, exist_ok=False)
    launcher = ROOT / 'scripts/adhoc/g2_bc1_offline_20261101.py'
    command = ['/usr/bin/sandbox-exec', '-p', '(version 1)(allow default)(deny network*)',
        sys.executable, '-S', '-B', str(launcher), str(tree / SCANNER), '--root', str(tree),
        '--full-json', '--report', str(output / 'audit.md'), '--json', str(output / 'audit.json')]
    env = dict(ENV, G1_CHECKOUT_ROOT=str(tree), PYTHONPATH=str(tree / 'src'),
               PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PIP_NO_INDEX='1', UV_OFFLINE='1')
    for key in list(env):
        if any(term in key.upper() for term in ('API_KEY', 'TOKEN', 'SECRET', 'PASSWORD')):
            env.pop(key, None)
    started = {'identity': identity, 'command': command, 'deadline_seconds': 3600,
               'producer': PRODUCER, 'scanner': pin(tree / SCANNER), 'launcher': pin(launcher)}
    save(output / 'started.json', started)
    with (output / 'scan.log').open('x') as log:
        run = subprocess.run(command, cwd=tree, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=3600)
    report = load(output / 'audit.json') if (output / 'audit.json').exists() else None
    arrays = scanner_arrays(report) if report is not None else None
    ok = (run.returncode == 1 and arrays is not None and report['commit'] == identity['commit']
          and report['root'] == tree.name and pin(Path(__file__)) == PRODUCER)
    save(output / 'result.json', {'identity': identity, 'command': command, 'returncode': run.returncode,
        'passed': ok, 'deadline_seconds': 3600, 'producer': PRODUCER,
        'scanner': started['scanner'], 'launcher': started['launcher'],
        'artifacts': [pin(p) for p in sorted(output.iterdir()) if p.is_file()]})
    archive_identity(tree)
    require(ok, 'baseline/final scanner must complete with exactly 24 findings')


def compare(args):
    helper = module('compare_5213_stack_scanner_20261103.py')
    old = load(args.before)
    new = load(args.after)
    before, after = scanner_arrays(old), scanner_arrays(new)
    require(old['commit'] == args.base and new['commit'] == args.head, 'scanner commit identity differs')
    arrays = {name: helper.comparison(before[name], after[name]) for name in before}
    passed = len(before['violations']) == len(after['violations']) == 24 and all(row['equal'] for row in arrays.values())
    save(args.output, {'format': 'historical_evaluation_scanner_comparison_v1', 'passed': passed,
        'before': pin(args.before), 'after': pin(args.after), 'producer': PRODUCER,
        'arrays': arrays, 'limits': 'Exact complete finding and listed-not-derived arrays; no coordinate normalization.'})
    require(passed, 'scanner arrays differ; false comparison retained')


def test(args):
    tree = args.tree.resolve(strict=True)
    archive_identity(tree)
    require(args.workers in (0, 1, 2), 'at most two workers')
    require(args.targets and all(not target.startswith('-') for target in args.targets), 'explicit test targets only')
    require(args.output.is_absolute() and not args.output.resolve().is_relative_to(tree)
            and not args.output.resolve().is_relative_to(ROOT), 'external basetemp/evidence required')
    driver = ROOT / 'scripts/adhoc/bc1_g2_validate_20261103.py'
    rest = [*args.targets, '-q']
    if args.collect:
        rest += ['--collect-only']
    else:
        rest += ['-n', str(args.workers), '--dist=load', '--maxschedchunk=1']
    # OS denial covers non-Python children; the existing Python launcher also
    # refuses remote network and strips inherited provider API credentials.
    command = ['/usr/bin/sandbox-exec', '-p', '(version 1)(allow default)(deny network*)',
        sys.executable, '-B', str(driver), 'test', str(tree), '--output', str(args.output), *rest]
    env = dict(ENV, PYTHONPATH=str(tree / 'src'))
    for key in list(env):
        if any(term in key.upper() for term in ('API_KEY', 'TOKEN', 'SECRET', 'PASSWORD')):
            env.pop(key, None)
    save(args.output.with_name(args.output.name + '.launcher.json'),
         {'producer': PRODUCER, 'driver': pin(driver), 'command': command,
          'archive': archive_identity(tree), 'deadline_seconds': 3600,
          'os_network_policy': 'deny network*', 'credential_environment_removed': True})
    code = subprocess.call(command, cwd=tree, env=env)
    archive_identity(tree)
    require(pin(Path(__file__)) == PRODUCER, 'validation helper changed during test run')
    raise SystemExit(code)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('archive')
    p.add_argument('--tree', type=Path, required=True)
    p.add_argument('--ref', required=True)
    for action in ('closure', 'preserve', 'compare'):
        p = sub.add_parser(action)
        p.add_argument('--base', default=BASE)
        p.add_argument('--head', default='HEAD')
        p.add_argument('--output', type=Path, required=True)
        if action == 'closure':
            p.add_argument('--registrations', type=Path, required=True)
            p.add_argument('--include-working', action='store_true')
        elif action == 'compare':
            p.add_argument('--before', type=Path, required=True)
            p.add_argument('--after', type=Path, required=True)
    for action in ('scan', 'test'):
        p = sub.add_parser(action)
        p.add_argument('--tree', type=Path, required=True)
        p.add_argument('--output', type=Path, required=True)
        if action == 'test':
            p.add_argument('--workers', type=int, default=2)
            p.add_argument('--collect', action='store_true')
            p.add_argument('targets', nargs='+')
    args = parser.parse_args()
    if args.action == 'archive':
        require(args.tree.is_absolute() and args.tree.is_relative_to(ROOT.parent / 'scratch-bc1g2'), 'scratch archive required')
        os.environ.update(ENV)
        driver = module('bc1_g2_validate_20261103.py')
        driver.archive(args.ref, args.tree)
        driver.metadata(args.tree)
        # Cache stat information only in this new scratch index. Without this,
        # optional-lock-free diff checks reread the entire historical corpus.
        git('update-index', '--refresh', root=args.tree)
        archive_identity(args.tree)
    else:
        {'closure': closure, 'preserve': preservation, 'scan': scan,
         'compare': compare, 'test': test}[args.action](args)


if __name__ == '__main__':
    main()
