#!/usr/bin/env python3
"""Issue 6200 integration proof setup, 2026-11-13.

Inputs: this branch's committed source and the previous offline runner.
Outputs: a provenance-preserving runner or a fresh exact Git export outside E.
No network, provider, native executable or source pin rotation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = Path.home() / 'agent-work/data-sheets-schema/helper2-integration-fixes-20261113'


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def make_runner():
    source = ROOT.parent / 'codex-development-efficiency-20261111/scripts/adhoc/run_h2_pins_admission_20261113.py'
    raw = source.read_text()
    raw = raw.replace('"-p", "h2_public_path_timing_20261112", ', '')
    raw = raw.replace('def sandbox_profile():', 'def sandbox_profile(allow_loopback=False):')
    raw = raw.replace("'(version 1)\\n(allow default)\\n(deny network*)\\n'", "'''(version 1)\\n(allow default)\\n(deny network*)\\n''' + ('''(allow network-bind (local ip \"localhost:*\"))\\n(allow network-inbound (local ip \"localhost:*\"))\\n(allow network-outbound (remote ip \"localhost:*\"))\\n''' if allow_loopback else '') +")
    raw = raw.replace('profile.write_text(sandbox_profile(),', 'profile.write_text(sandbox_profile(allow_loopback=bool(args.lane)),')
    start = raw.index('def network_witness():')
    end = raw.index('\n\ndef worker(args):', start)
    raw = raw[:start] + '''def network_witness(out, allow_loopback=False):
    previous = Path.cwd()
    name = 'network-denial-witness.sock'
    sock = socket.socket(socket.AF_UNIX if allow_loopback else socket.AF_INET)
    try:
        os.chdir(out)
        try:
            if allow_loopback:
                sock.bind(name)
                sock.listen(1)
            else:
                sock.bind(('127.0.0.1', 0))
        except OSError as exc:
            if exc.errno != errno.EPERM:
                raise
            return {'network_operation_denied': True, 'errno': exc.errno,
                    'operation': 'Unix-domain listener' if allow_loopback else 'loopback bind',
                    'pid': os.getpid(), 'external_address_attempted': False,
                    'scope': 'OS deny network* with explicit CI localhost IP allowances only'}
        raise RuntimeError('OS network denial self-check unexpectedly permitted the operation')
    finally:
        sock.close()
        if allow_loopback:
            (out / name).unlink(missing_ok=True)
        os.chdir(previous)
''' + raw[end:]
    raw = raw.replace('network_witness())', 'network_witness(out, allow_loopback=bool(args.lane)))')
    raw = raw.replace('str(ROOT), "--child-check"],', 'str(ROOT), "--child-check",\n         "--out", str(out), *(["--lane", args.lane] if args.lane else [])],')
    raw = raw.replace('timeout=30, check=True)', "timeout=30, check=False)\n    save(out / 'subprocess-origin-result.json', {'returncode': witness.returncode,\n         'stdout': witness.stdout, 'stderr': witness.stderr})\n    witness.check_returncode()")
    raw = raw.replace('"network": network_witness()', '"network": network_witness(\n            args.out.resolve(strict=True), allow_loopback=bool(args.lane))')
    raw = raw.replace('def parent(args):\n', "def parent(args):\n    hold = ROOT.with_name(ROOT.name + '.hold.json')\n    if hold.exists():\n        raise SystemExit('validation export held before launch: ' + str(hold))\n")
    raw = raw.replace('codex-development-efficiency-20261111', ROOT.name)
    raw = raw.replace('helper2-pins-admission-20261113', BASE.name)
    raw = raw.replace("tree.name not in ('before', 'after', 'fixed', 'unaffected')", "not tree.name.replace('-', '').isalnum()")
    raw = raw.replace('only exact outside-execution CI exports allowed', 'only exact offline integration exports allowed')
    raw = raw.replace('parser.add_argument("--scanner", action="store_true")',
        'parser.add_argument("--scanner", action="store_true")\n    parser.add_argument("--lane", choices=("budget", "native", "audit"))')
    raw = raw.replace('command += args.nodes\n    commit =',
        'if args.lane:\n        command += ["--lane", args.lane]\n    command += args.nodes\n    commit =')
    raw = raw.replace('env = clean_environment(out, python.parent)', '''env = clean_environment(out, python.parent)
    if args.lane in ('native', 'audit'):
        env['PYTHONPATH'] = 'src:notes/matched_cborg_2026-09-13:notes/matched_cborg_2026-09-13/native_controls'
    elif args.lane == 'budget':
        env.pop('PYTHONPATH', None)''')
    raw = raw.replace('command += args.nodes\n    save(out / "pytest-command.json"', '''if args.lane:
        import shlex
        import yaml
        workflow = yaml.safe_load((ROOT / '.github/workflows/main.yaml').read_text())
        job = 'offline-audit' if args.lane == 'audit' else 'offline-canary'
        prefix = {'audit': 'Exercise native audit', 'native': 'Exercise native canary',
                  'budget': 'Exercise experimental canary'}[args.lane]
        step = next(step for step in workflow['jobs'][job]['steps']
                    if step.get('name', '').startswith(prefix))
        for key, value in step.get('env', {}).items():
            assert os.environ.get(key) == str(value), (key, os.environ.get(key), value)
        argv = shlex.split(step['run'])
        assert argv[:5] == ['poetry', 'run', 'python', '-m', 'pytest']
        command = [arg for arg in argv[5:] if not arg.startswith('--junitxml=')]
        command += ['--junitxml', str(out / 'pytest.xml'), '--basetemp', str(out / 'cases')]
        save(out / 'ci-lane.json', {'job': job, 'step': step,
             'workflow_sha256': digest(ROOT / '.github/workflows/main.yaml'),
             'local_interpreter': sys.version, 'local_platform': sys.platform,
             'scope': 'exact CI env, PYTHONPATH and file list; isolated local interpreter'})
    else:
        command += args.nodes
    save(out / "pytest-command.json"''')
    raw = raw.replace('(not args.nodes and not args.scanner)', '(not args.nodes and not args.scanner and not args.lane)')
    raw = raw.replace('"--out and either explicit tests/ nodes or --scanner are required"',
        '"--out and explicit tests, --scanner, or --lane are required"')
    (ROOT / 'scripts/adhoc/run_h2_integration_20261113.py').write_text(raw)
    print(json.dumps({'runner_source': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}))


def export(label):
    BASE.mkdir(parents=True, exist_ok=True)
    tree = BASE / label
    tree.mkdir()
    commit = git(ROOT, 'rev-parse', 'HEAD')
    git(tree, 'init', '-q')
    (tree / '.git/objects/info/alternates').write_text(
        git(ROOT, 'rev-parse', '--path-format=absolute', '--git-path', 'objects') + '\n')
    git(tree, 'symbolic-ref', 'HEAD', 'refs/heads/offline-' + label)
    git(tree, 'update-ref', 'HEAD', commit)
    git(tree, 'read-tree', '-mu', 'HEAD')
    git(tree, 'config', '--local', 'd4d.ciRepositoryUrl', 'https://github.com/bridge2ai/data-sheets-schema.git')
    prior = Path.home() / 'agent-work/data-sheets-schema/helper2-pins-admission-20261113/fixed/fairscape_models'
    shutil.copytree(prior, tree / 'fairscape_models', dirs_exist_ok=True)
    manifest = BASE / (label + '.json')
    manifest.write_text(json.dumps({'tree': str(tree), 'commit': commit,
        'source': str(ROOT), 'submodule_source': str(prior)}, indent=2) + '\n')
    print(manifest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runner', action='store_true')
    parser.add_argument('--export')
    args = parser.parse_args()
    if args.runner:
        make_runner()
    if args.export:
        export(args.export)
