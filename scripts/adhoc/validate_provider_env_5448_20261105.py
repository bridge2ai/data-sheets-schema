#!/usr/bin/env python3
"""#5448, 2026-11-05: pinned offline provider-environment reproduction.

Inputs: local commits, explicit pytest nodes and clean/dummy environment mode.
Outputs: fresh task-owned archives, immutable commands/results/collection checks.
Never carries inherited provider credentials or endpoints; never calls providers.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT.parent
SCRATCH = EXEC / 'scratch-codex-5448-20261105'
EVIDENCE = EXEC / 'plans/reviews/codex_5448_5494_2026-11-05/5448'
PRIMARY = EXEC.parent / 'data-sheets-schema'
PYTHON = PRIMARY / '.venv/bin/python'
BASE = 'd0974d4bcc0f254272ec5a95e94d83ae801bbd38'
SNAPSHOT_PATHS = ('tests/conftest.py', 'tests/test_d69_round4_ownership.py',
                  'tests/test_fairscape_integration/test_nested_dataset_readback.py',
                  'scripts/adhoc/validate_provider_env_5448_20261105.py')
SAFE_NAMES = {'PATH', 'HOME', 'USER', 'LOGNAME', 'SHELL', 'LANG', 'LC_ALL', 'LC_CTYPE',
              'TZ', 'TERM', 'TMPDIR', 'TMP', 'TEMP', '__CF_USER_TEXT_ENCODING'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path.absolute()), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


PRODUCER = pin(Path(__file__))


def save(path, value):
    path = Path(path)
    require(path.is_absolute() and path.resolve() == path, 'canonical absolute evidence path required')
    require(path.is_relative_to(EVIDENCE) or path.is_relative_to(SCRATCH), 'task-owned evidence only')
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n'
    with path.open('xb') as stream:
        stream.write(raw)
    require(path.read_bytes() == raw, 'evidence persistence differs')


def environment(mode='clean'):
    require(mode in {'clean', 'dummy'}, 'unknown environment mode')
    env = {key: value for key, value in os.environ.items() if key in SAFE_NAMES}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='', GIT_CONFIG_NOSYSTEM='1',
               GIT_CONFIG_GLOBAL='/dev/null', GIT_OPTIONAL_LOCKS='0',
               PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
               PIP_NO_INDEX='1', UV_OFFLINE='1', G1_PROVIDER_KEYS_CLEARED='1')
    if mode == 'dummy':
        env['CBORG_API_KEY'] = 'dummy-not-a-key'
    return env


def git(*arguments, root=ROOT):
    return subprocess.check_output(['git', '--no-replace-objects', '-c', 'protocol.allow=never',
        '-C', str(root), *arguments], env=environment(), timeout=120)


def scoped_tree(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve() == path and path.is_relative_to(SCRATCH)
            and path != SCRATCH, 'fresh canonical task archive required')
    return path


def identity(tree):
    tree = scoped_tree(tree)
    marker = json.loads((tree / '.g2-archive.json').read_bytes())
    require(git('rev-parse', 'HEAD', root=tree).decode().strip() == marker['commit'], 'archive HEAD differs')
    detached = subprocess.run(['git', '-C', str(tree), 'symbolic-ref', '-q', 'HEAD'],
                              env=environment(), capture_output=True, timeout=30)
    require(detached.returncode == 1, 'archive must remain detached')
    snapshot_path = tree / '.provider-env-snapshot.json'
    if snapshot_path.exists():
        snapshot = json.loads(snapshot_path.read_bytes())
        require(snapshot['format'] == 'provider_environment_candidate_snapshot_v1'
                and snapshot['base'] == marker['commit'] == BASE
                and snapshot['copied_paths'] == list(SNAPSHOT_PATHS)
                and marker.get('candidate_snapshot') == pin(snapshot_path), 'unexpected candidate snapshot')
        for relative in SNAPSHOT_PATHS:
            require(pin(tree / relative) == snapshot['files'][relative], 'candidate file differs: ' + relative)
        changed = git('diff', '--name-only', '--ignore-submodules=all', 'HEAD', '--', root=tree).decode().splitlines()
        require(changed == snapshot['tracked_changed_paths'], 'candidate tracked path set differs')
        require(set(changed) <= set(SNAPSHOT_PATHS), 'candidate includes unauthorized tracked changes')
        patch = git('diff', '--binary', '--ignore-submodules=all', 'HEAD', '--', root=tree)
        patch_path = tree / '.provider-env-snapshot.diff'
        require(pin(patch_path) == snapshot['tracked_patch'] and patch_path.read_bytes() == patch,
                'candidate tracked patch differs')
        return marker
    require('candidate_snapshot' not in marker, 'candidate manifest is missing')
    git('diff', '--quiet', '--ignore-submodules=all', 'HEAD', '--', root=tree)
    return marker


def archive(args):
    tree = scoped_tree(args.tree)
    require(not tree.exists(), 'archive must be new; no refresh or overlay')
    helper = ROOT / 'scripts/adhoc/g2_bc1_evidence_20261101.py'
    spec = importlib.util.spec_from_file_location('provider_env_archive', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ENV = environment()
    module.archive(args.ref, tree)
    marker = json.loads((tree / '.g2-archive.json').read_bytes())
    common = Path(git('rev-parse', '--git-common-dir').decode().strip())
    objects = (ROOT / common / 'objects').resolve()
    require(objects.is_dir(), 'local object store unavailable')
    subprocess.run(['git', 'init', '--quiet', str(tree)], env=environment(), check=True, timeout=30)
    (tree / '.git/objects/info/alternates').write_text(str(objects) + '\n')
    git('update-ref', '--no-deref', 'HEAD', marker['commit'], root=tree)
    git('read-tree', marker['commit'], root=tree)
    git('update-index', '--refresh', root=tree)
    save(tree / '.provider-env-metadata.json', {'identity': identity(tree), 'producer': PRODUCER,
        'archive_helper': pin(helper), 'objects': str(objects), 'detached': True, 'overlay': False})
    require(pin(Path(__file__)) == PRODUCER, 'producer changed during archive')


def snapshot(args):
    """Copy only this task's allowed candidate files into a fresh base archive."""
    require(git('rev-parse', args.ref).decode().strip() == BASE, 'snapshot requires the assigned base')
    archive(args)
    tree = scoped_tree(args.tree)
    files, source_files = {}, {}
    for relative in SNAPSHOT_PATHS:
        source, target = ROOT / relative, tree / relative
        require(source.is_file() and source.resolve() == source and target.resolve() == target,
                'candidate files cannot use filesystem aliases')
        before = pin(source)
        raw = source.read_bytes()
        require(pin(source) == before and hashlib.sha256(raw).hexdigest() == before['sha256'],
                'candidate source changed during capture')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        require(target.read_bytes() == raw and pin(source) == before, 'candidate copy differs')
        files[relative], source_files[relative] = pin(target), before
    changed = git('diff', '--name-only', '--ignore-submodules=all', 'HEAD', '--', root=tree).decode().splitlines()
    require(set(changed) <= set(SNAPSHOT_PATHS), 'snapshot includes unauthorized tracked changes')
    patch_path = tree / '.provider-env-snapshot.diff'
    with patch_path.open('xb') as stream:
        stream.write(git('diff', '--binary', '--ignore-submodules=all', 'HEAD', '--', root=tree))
    save(tree / '.provider-env-snapshot.json', {
        'format': 'provider_environment_candidate_snapshot_v1', 'base': BASE,
        'copied_paths': list(SNAPSHOT_PATHS), 'tracked_changed_paths': changed,
        'tracked_patch': pin(patch_path), 'files': files, 'source_files': source_files,
        'producer': PRODUCER, 'limits': 'Fresh task-only snapshot; base commit plus explicit uncommitted candidate bytes.',
    })
    # The unchanged driver reads this marker into both started/result JSON.
    # Extend it only during construction of this new snapshot, before any run.
    marker_path = tree / '.g2-archive.json'
    marker = json.loads(marker_path.read_bytes())
    marker['candidate_snapshot'] = pin(tree / '.provider-env-snapshot.json')
    marker_raw = json.dumps(marker, sort_keys=True, indent=2).encode() + b'\n'
    marker_path.write_bytes(marker_raw)
    require(marker_path.read_bytes() == marker_raw, 'candidate identity did not persist')
    require(all(pin(ROOT / relative) == expected for relative, expected in source_files.items()),
            'candidate source set changed during snapshot')
    identity(tree)
    require(pin(Path(__file__)) == PRODUCER, 'producer changed during snapshot')


def test(args):
    tree = scoped_tree(args.tree)
    before = identity(tree)
    output = args.output
    require(output.is_absolute() and output.resolve() == output and output.is_relative_to(EVIDENCE)
            and output != EVIDENCE and not output.exists(), 'new external task evidence required')
    require(args.nodes and all(not node.startswith('-') for node in args.nodes), 'explicit nodes required')
    require(str(Path(sys.executable).absolute()) == str(PYTHON), 'use the primary pinned virtualenv interpreter')
    driver = ROOT / 'scripts/adhoc/bc1_g2_validate_20261103.py'
    launcher = ROOT / 'scripts/adhoc/g2_bc1_offline_20261101.py'
    arguments = [*args.nodes, '-q']
    arguments += ['--collect-only'] if args.collect else ['-n', '2', '--dist=load', '--maxschedchunk=1']
    command = ['/usr/bin/sandbox-exec', '-p', '(version 1)(allow default)(deny network*)',
               str(PYTHON), '-B', str(driver), 'test', str(tree), '--output', str(output), *arguments]
    env = environment(args.mode)
    env['PYTHONPATH'] = str(tree / 'src')
    start = {'producer': PRODUCER, 'driver': pin(driver), 'launcher': pin(launcher),
        'archive': before, 'command': command, 'mode': args.mode, 'deadline_seconds': 3600,
        'environment_policy': 'allowlisted OS variables only; all inherited credentials/endpoints discarded',
        'allowed_inherited_names': sorted(set(os.environ) & SAFE_NAMES),
        'discarded_inherited_names': sorted(set(os.environ) - SAFE_NAMES),
        'controlled_provider_names': ['CBORG_API_KEY'] if args.mode == 'dummy' else [],
        'controlled_dummy_only': args.mode == 'dummy', 'provider_environment_values_logged': False,
        'launcher_preserves_controlled_environment': True, 'os_network_policy': 'deny network*'}
    save(output.with_name(output.name + '.launcher.json'), start)
    code = subprocess.call(command, cwd=tree, env=env)
    require(identity(tree) == before, 'archive identity changed')
    require(pin(Path(__file__)) == PRODUCER and pin(driver) == start['driver']
            and pin(launcher) == start['launcher'], 'validation producer changed')
    artifacts = [pin(output / name) for name in ('started.json', 'result.json', 'pytest.log',
        'junit.xml', 'events.jsonl', 'collected.json', 'failures.jsonl') if (output / name).is_file()]
    require((output / 'result.json').is_file(), 'driver produced no terminal result')
    result = json.loads((output / 'result.json').read_bytes())
    require(result['identity'] == before and result['returncode'] == code, 'driver result differs')
    save(output.with_name(output.name + '.terminal.json'), {'producer': PRODUCER, 'archive': before,
        'mode': args.mode, 'returncode': code, 'artifacts': artifacts})
    return code


def compare_collection(args):
    inputs = []
    for path in (args.before, args.after):
        require(path.is_absolute() and path.resolve() == path and path.is_relative_to(EVIDENCE),
                'task collection evidence required')
        nodes = json.loads(path.read_bytes())
        require(isinstance(nodes, list) and nodes and all(isinstance(node, str) for node in nodes),
                'nonempty node list required')
        result = json.loads(path.with_name('result.json').read_bytes())
        started = json.loads(path.with_name('started.json').read_bytes())
        require(result['returncode'] == 0 and '--collect-only' in started['command']
                and result['identity'] == started['identity'], 'successful bound collection required')
        inputs.append((nodes, result, started))
    before, after = Counter(inputs[0][0]), Counter(inputs[1][0])
    result = {'format': 'provider_environment_collection_comparison_v1', 'producer': PRODUCER,
        'before': pin(args.before), 'after': pin(args.after),
        'before_identity': inputs[0][1]['identity'], 'after_identity': inputs[1][1]['identity'],
        'before_count': sum(before.values()), 'after_count': sum(after.values()),
        'before_distinct': len(before), 'after_distinct': len(after),
        'removed': dict(sorted((before - after).items())), 'added': dict(sorted((after - before).items())),
        'equal': before == after, 'comparison': 'exact node multiplicity; no normalization or exclusions'}
    save(args.output, result)
    require(result['equal'], 'collection differs; exact delta saved')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    for action in ('archive', 'snapshot'):
        p = commands.add_parser(action)
        p.add_argument('--ref', required=True)
        p.add_argument('--tree', type=Path, required=True)
    p = commands.add_parser('test')
    p.add_argument('--tree', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--mode', choices=('clean', 'dummy'), required=True)
    p.add_argument('--collect', action='store_true')
    p.add_argument('nodes', nargs='+')
    p = commands.add_parser('compare-collection')
    p.add_argument('--before', type=Path, required=True)
    p.add_argument('--after', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.action in {'archive', 'snapshot'}:
        (archive if args.action == 'archive' else snapshot)(args)
        return 0
    return test(args) if args.action == 'test' else compare_collection(args)


if __name__ == '__main__':
    raise SystemExit(main())
