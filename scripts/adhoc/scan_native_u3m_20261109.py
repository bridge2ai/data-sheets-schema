"""U3-M before/after scanner evidence, 2026-11-09 (#5653).

Inputs: explicit saved tree, optional local scanner commit, fresh label. Outputs:
full JSON/Markdown/log/identity evidence under scratch-native-u1u3/u3h only.
Reuses the reviewed network/native-denied scanner sandbox; no provider calls.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1u3'
SKILL = '.claude/skills/d4d-generation-specificity-audit'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--tool-ref')
    parser.add_argument('--label', required=True)
    parser.add_argument('--bootstrap', required=True, help='completed fresh U3-M canary label')
    args = parser.parse_args()
    if ROOT.parent.name != 'd4d-executions' or not re.fullmatch('[a-z0-9][a-z0-9_-]*', args.label):
        parser.error('assigned worktree and simple fresh label required')
    spec = importlib.util.spec_from_file_location('u3f2_scan_composer',
        ROOT / 'scripts/adhoc/compose_native_u1u3_20261108.py')
    c = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c)
    c.quiet()
    c.need(SCRATCH.resolve(strict=True) == SCRATCH, 'scratch root is aliased')
    tree = args.tree.resolve(strict=True)
    c.need(tree.is_relative_to(SCRATCH), 'scan source must be retained assigned scratch')
    source_commit = c.git('rev-parse', 'HEAD', cwd=tree).decode().strip()
    c.git('diff-index', '--quiet', 'HEAD', '--', cwd=tree)
    out = SCRATCH / 'u3m' / args.label
    out.mkdir(parents=True, exist_ok=False)
    c.need(out.resolve(strict=True) == out, 'scanner output is aliased')
    if args.tool_ref:
        tool_commit = c.git('rev-parse', args.tool_ref + '^{commit}').decode().strip()
        paths = c.git('ls-tree', '-r', '--name-only', tool_commit, SKILL).decode().splitlines()
        for relative in paths:
            target = out / 'tool' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(c.strict_blob(tool_commit, relative))
        tool = out / 'tool' / SKILL / 'scan.py'
    else:
        tool_commit = c.git('rev-parse', 'HEAD').decode().strip()
        tool = ROOT / SKILL / 'scan.py'
        c.need(tool.read_bytes() == c.strict_blob(tool_commit, SKILL + '/scan.py'),
               'current scanner must be committed')
    asset_paths = c.git('ls-tree', '-r', '--name-only', tool_commit, SKILL).decode().splitlines()
    assets = {name: c.sha((tool.parent / Path(name).relative_to(SKILL)).read_bytes())
              for name in asset_paths}
    c.need(all(assets[name] == c.sha(c.strict_blob(tool_commit, name)) for name in assets),
           'scanner assets must be committed')
    if not re.fullmatch('[a-z0-9][a-z0-9_-]*', args.bootstrap):
        parser.error('literal bootstrap label required')
    canary = SCRATCH / 'u3m' / args.bootstrap
    c.need(canary.resolve(strict=True) == canary, 'bootstrap is aliased')
    dependency_canary = json.loads((canary / 'dependency-write-denied.json').read_bytes())
    c.need(dependency_canary['status'] == 'write_denied_and_exact_dependency_unchanged',
           'validated dependency write-denial canary required')
    prior = json.loads((canary / 'plan.json').read_text())
    outcome = json.loads((canary / 'outcome.json').read_bytes())
    c.need(outcome['returncode'] == 0 and outcome['worker_returncode'] == 0
           and outcome['cleanup_verified'] is True
           and outcome['worker']['source_origin_checks_passed'] is True,
           'completed successful bootstrap canary required')
    bootstrap = json.loads((canary / 'bootstrap.json').read_bytes())
    c.need(bootstrap['test_python'] == str(canary / 'venv/bin/python')
           and c.sha(Path(bootstrap['underlying_python']).read_bytes()) == bootstrap['underlying_python_sha256']
           and all(c.sha(Path(path).read_bytes()) == digest for path, digest in bootstrap['files'].items()),
           'bootstrap interpreter or startup files changed')
    c.need(c.sha((canary / 'network-denied.sb').read_bytes()) == prior['sandbox_sha256']
           == dependency_canary['policy_sha256'], 'bootstrap sandbox changed')
    env = dict(prior['environment'])
    for name in ('home', 'tmp'):
        (out / name).mkdir()
    env['HOME'] = str(out / 'home')
    env['TMPDIR'] = str(out / 'tmp')
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONPATH'] = str(tree / 'src') + ':' + str(tree)
    profile = (canary / 'network-denied.sb').read_text()
    boundary = '(require-not (subpath ' + json.dumps(str(canary)) + '))'
    c.need(profile.count(boundary) == 1, 'bootstrap sandbox output boundary differs')
    profile = profile.replace(boundary, '(require-not (subpath ' + json.dumps(str(out)) + '))', 1)
    (out / 'network-denied.sb').write_text(profile)
    command = ['/usr/bin/sandbox-exec', '-f', str(out / 'network-denied.sb'),
        str(canary / 'venv/bin/python'), '-P', '-B', str(tool), '--root', str(tree),
        '--report', str(out / 'scanner.md'), '--json', str(out / 'scanner.json'), '--full-json']
    row = dict(command=command, source_commit=source_commit, tool_commit=tool_commit,
        tool_sha256=c.sha(tool.read_bytes()), tool_assets_sha256=assets,
        timeout_seconds=3200, load_before=os.getloadavg())
    start = time.monotonic()
    try:
        with (out / 'scanner.log').open('xb') as log:
            child = subprocess.Popen(command, cwd=tree, env=env, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True)
            try:
                while child.poll() is None:
                    c.quiet()
                    if time.monotonic() - start >= 3200:
                        raise TimeoutError('scanner deadline 3200 seconds')
                    time.sleep(1)
            except BaseException:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait(timeout=5)
                raise
        row['exit_code'] = child.returncode
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            row['process_group_gone'] = True
        else:
            row['process_group_gone'] = False
            os.killpg(child.pid, signal.SIGTERM)
            raise RuntimeError('scanner exited with a surviving owned process group')
        row['tool_unchanged'] = c.sha(tool.read_bytes()) == row['tool_sha256']
        c.need(row['tool_unchanged'], 'scanner bytes changed during scan')
        row['tool_assets_unchanged'] = all(
            c.sha((tool.parent / Path(name).relative_to(SKILL)).read_bytes()) == digest
            for name, digest in assets.items())
        c.need(row['tool_assets_unchanged'], 'scanner asset bytes changed during scan')
        c.git('diff-index', '--quiet', 'HEAD', '--', cwd=tree)
        if (out / 'scanner.json').is_file():
            document = json.loads((out / 'scanner.json').read_bytes())
            row.update(hits=len(document['hits']), violations=len(document['violations']),
                       scanner_json_sha256=c.sha((out / 'scanner.json').read_bytes()))
        c.need(child.returncode in (0, 1, 2), 'scanner failed unexpectedly')
        row['derivation_complete'] = child.returncode in (0, 1)
        if row['derivation_complete']:
            c.need('scanner_json_sha256' in row, 'scanner did not persist a full JSON report')
        else:
            row['derivation_status'] = 'blocked_incomplete_derivation'
        print(json.dumps(row), flush=True)
    finally:
        row.update(seconds=time.monotonic() - start, load_after=os.getloadavg())
        (out / 'run.json').write_text(json.dumps(row, indent=2) + '\n')


if __name__ == '__main__':
    main()
