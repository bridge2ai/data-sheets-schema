"""Prepare an offline installed-dependency closure for D148 tests, 2026-11-14.

Inputs: primary physical site-packages and this checkout's declared runtime
dependencies plus pytest, xdist, packaging and psutil. Outputs: a new test-only
venv in assigned scratch and an exact copy/hash ledger. No resolution/download,
primary environment mutation, symlinked payloads or reduced manifest checks.
Run --plan, then --canary (one distribution), then --apply. Each distribution's
complete installed RECORD payload is copied; only excluded pyc caches are omitted.
"""
import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tomllib
import venv

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-manifest-integration-20261114/continuation'


def normalized(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-site', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan', action='store_true')
    mode.add_argument('--canary', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = p.parse_args()
    assert sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode
    source = args.source_site.resolve(strict=True)
    output = args.output.absolute()
    assert output.resolve() == output and output.parent == SCRATCH and not output.is_symlink()
    assert source == ROOT.parents[1] / 'data-sheets-schema/.venv/lib/python3.13/site-packages'
    sys.path.append(str(source))  # plain path: never execute the site's .pth files
    from packaging.markers import default_environment
    from packaging.requirements import Requirement
    from packaging.specifiers import SpecifierSet
    installed = {}
    for dist in metadata.distributions(path=[str(source)]):
        name = normalized(dist.metadata['Name'])
        assert name not in installed, name
        installed[name] = dist
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text())['tool']['poetry']['dependencies']
    env = default_environment()
    seeds = []
    for name, spec in project.items():
        if name == 'python':
            continue
        if isinstance(spec, dict) and 'python' in spec:
            if not SpecifierSet(spec['python']).contains(env['python_full_version']):
                continue
        seeds.append(name)
    seeds += ['pytest', 'pytest-xdist', 'psutil', 'packaging']
    selected, examined, queue = {}, {}, [Requirement(name) for name in seeds]
    while queue:
        requirement = queue.pop()
        name = normalized(requirement.name)
        assert name in installed, ('missing installed dependency', str(requirement))
        dist = installed[name]
        assert requirement.specifier.contains(dist.version, prereleases=True), (
            'installed version violates dependency metadata', str(requirement), dist.version)
        extras = selected.setdefault(name, set())
        extras.update(requirement.extras)
        if name in examined and examined[name] == extras:
            continue
        examined[name] = set(extras)
        for raw in dist.requires or []:
            dependency = Requirement(raw)
            if dependency.marker is None or any(dependency.marker.evaluate({**env, 'extra': extra})
                                                for extra in {'', *extras}):
                queue.append(dependency)
    site = output / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
    rows = []
    for name in sorted(selected):
        dist = installed[name]
        assert dist.files is not None, name
        payloads = []
        for relative in dist.files:
            if str(relative).endswith('.pyc'):
                continue
            assert not Path(relative).is_absolute(), (name, str(relative))
            src = Path(dist.locate_file(relative)).resolve(strict=True)
            dst = Path(os.path.abspath(site / relative))
            assert dst.is_relative_to(output) and src.is_file(), (name, str(relative))
            payloads.append({'source': str(src), 'destination': str(dst), 'bytes': src.stat().st_size})
        rows.append({'name': name, 'version': dist.version, 'extras': sorted(selected[name]),
                     'files': payloads, 'bytes': sum(row['bytes'] for row in payloads)})
    plan = {'source_site': str(source), 'output': str(output), 'seeds': seeds, 'distributions': rows,
            'distribution_count': len(rows), 'file_count': sum(len(row['files']) for row in rows),
            'bytes': sum(row['bytes'] for row in rows), 'scope': 'synthetic offline test environment only'}
    plan_path = SCRATCH / (output.name + '-plan.json')
    if args.plan:
        write(plan_path, plan)
        print(json.dumps({key: value for key, value in plan.items() if key != 'distributions'}, indent=2))
        return
    assert json.loads(plan_path.read_bytes()) == plan, 'installed closure changed since planning'
    canary_path = SCRATCH / (output.name + '-canary.json')
    if args.canary:
        assert not output.exists()
        venv.EnvBuilder(with_pip=False, symlinks=True).create(output)
        chosen = [row for row in rows if row['name'] == 'packaging']
        assert len(chosen) == 1
    else:
        canary = json.loads(canary_path.read_bytes())
        assert canary['status'] == 'verified' and canary['distribution'] == 'packaging'
        assert all(sha(Path(row['destination'])) == row['sha256'] for row in canary['copied'])
        chosen = [row for row in rows if row['name'] != 'packaging']
    copied = []
    for distribution in chosen:
        for item in distribution['files']:
            src, dst = Path(item['source']), Path(item['destination'])
            expected = sha(src)
            assert src.stat().st_size == item['bytes']
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                assert dst.is_file() and not dst.is_symlink() and sha(dst) == expected
            else:
                with src.open('rb') as origin, dst.open('xb') as target:
                    shutil.copyfileobj(origin, target)
                dst.chmod(src.stat().st_mode & 0o777)
            assert sha(dst) == expected
            copied.append({**item, 'sha256': expected})
    result = {'status': 'verified', 'distribution': 'packaging' if args.canary else 'remaining closure',
              'copied': copied, 'file_count': len(copied), 'bytes': sum(row['bytes'] for row in copied)}
    write(canary_path if args.canary else SCRATCH / (output.name + '-copied.json'), result)
    print(json.dumps({key: value for key, value in result.items() if key != 'copied'}, indent=2))


if __name__ == '__main__':
    main()
