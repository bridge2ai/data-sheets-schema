"""Run bounded offline native-label checks and retain receipts, 2026-11-19.

Inputs: this checkout, the shared test interpreter and a fresh scratch leaf.
Outputs: command, source/environment identity, pytest log/JUnit and wall time.
Serves the native CLI model-label amendment; never invokes a native binary.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time
import venv
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python')
SCRATCH = ROOT.parent / 'scratch-native-cli-label-20261119'


def test_python():
    """Reuse dependencies without executing the shared editable-checkout .pth.

    Same plain-path bootstrap as run_h3_ci_tests_20261112.make_test_venv.
    Ordinary subprocess startup must also select this source namespace.
    """
    location = SCRATCH / 'environment'
    site = location / 'lib' / ('python%d.%d' % sys.version_info[:2]) / 'site-packages'
    dependency = PYTHON.parent.parent / 'lib' / ('python%d.%d' % sys.version_info[:2]) / 'site-packages'
    paths = [ROOT / 'src', ROOT]
    if (ROOT / 'fairscape_models/fairscape_models').is_dir():
        paths.append(ROOT / 'fairscape_models')
    paths.append(dependency)
    wanted = ''.join(str(path) + '\n' for path in paths)
    pth = site / 'native_integration_paths.pth'
    custom = site / 'sitecustomize.py'
    inert = '# Isolated test prefix; shared editable startup hooks are not executed.\n'
    if not location.exists():
        venv.EnvBuilder(with_pip=False, symlinks=True).create(location)
        pth.write_text(wanted)
        custom.write_text(inert)
    if pth.read_text() != wanted or custom.read_text() != inert:
        raise ValueError('isolated test environment changed')
    return location / 'bin/python'


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def main():
    if sys.argv[1:] == ['--origin-only']:
        import data_sheets_schema
        origins = sorted(str(Path(path).resolve()) for path in data_sheets_schema.__path__)
        if origins != [str(ROOT / 'src/data_sheets_schema')]:
            raise ValueError('test package namespace includes another checkout')
        print(json.dumps(dict(package_paths=origins, python=sys.executable, prefix=sys.prefix)))
        return 0
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['canary', 'focused', 'native', 'collect', 'd128'])
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or Path(args.label).name != args.label:
        parser.error('label must be one fresh leaf name')
    out = SCRATCH / args.label
    out.mkdir(parents=True, exist_ok=False)
    python = test_python()
    files = {
        'canary': ['tests/test_native_model_aliases.py::test_exact_declared_pair_is_detached_and_has_no_prefix_inference'],
        'focused': ['tests/test_native_model_aliases.py', 'tests/test_native_u4b_runtime.py',
                    'tests/test_native_u4b_probe_sequence.py', 'tests/test_native_cli_model_labels.py',
                    'tests/test_native_model_label_producers.py', 'tests/test_native_u4b_a3_policy.py'],
        'native': sorted(str(path.relative_to(ROOT)) for path in (ROOT / 'tests').glob('test_native*.py')),
        'collect': ['tests'],
        'd128': ['tests/test_native_d128_scanner_comparison.py'],
    }[args.mode]
    command = [str(python), '-P', '-m', 'pytest', *files, '-q', '-p', 'no:cacheprovider',
               '--basetemp', str(out / 'basetemp'), '--junitxml', str(out / 'junit.xml')]
    if args.mode == 'native':
        command += ['-n', '4', '--dist', 'load', '--maxschedchunk=1']
    if args.mode == 'collect':
        command += ['--collect-only']
    env = os.environ.copy()
    env.update(CI='true', PYTHONPATH=str(ROOT / 'src'), PYTHONPYCACHEPREFIX=str(out / 'pycache'),
               PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1')
    for key in ('PYTEST_ADDOPTS', 'PYTEST_CURRENT_TEST'):
        env.pop(key, None)
    origin_env = dict(env)
    origin_env.pop('PYTHONPATH', None)
    origin = subprocess.check_output([str(python), '-B', str(Path(__file__).resolve()),
                                      '--origin-only'], cwd=ROOT, env=origin_env, text=True)
    (out / 'origins.json').write_text(origin)
    record = dict(mode=args.mode, command=command, cwd=str(ROOT), started_at=now(),
                  head=git('rev-parse', 'HEAD'), source_status=git('status', '--porcelain'),
                  environment={key: env[key] for key in ('CI', 'PYTHONPATH', 'PYTHONPYCACHEPREFIX')},
                  interpreter=subprocess.check_output([str(python), '--version'], text=True).strip(),
                  source_origins=json.loads(origin),
                  helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out / 'command.json').write_text(json.dumps(record, indent=2) + '\n')
    started = time.monotonic()
    with (out / 'pytest.log').open('w') as log:
        process = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    record.update(finished_at=now(), wall_seconds=time.monotonic() - started, returncode=process.returncode)
    record['log_sha256'] = hashlib.sha256((out / 'pytest.log').read_bytes()).hexdigest()
    collected = re.findall(r'(\d+) tests? collected', (out / 'pytest.log').read_text())
    if collected:
        record['collected_tests'] = int(collected[-1])
    if (out / 'junit.xml').is_file():
        tree = ET.parse(out / 'junit.xml')
        suites = [tree.getroot()] if tree.getroot().tag == 'testsuite' else list(tree.getroot())
        record['counts'] = {key: sum(int(suite.get(key, 0)) for suite in suites)
                            for key in ('tests', 'failures', 'errors', 'skipped')}
    (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({key: record[key] for key in ('mode', 'head', 'returncode', 'wall_seconds')},
                     sort_keys=True), flush=True)
    if 'counts' in record:
        print(json.dumps(record['counts'], sort_keys=True), flush=True)
    print(str(out / 'result.json'), flush=True)
    return process.returncode


if __name__ == '__main__':
    raise SystemExit(main())
