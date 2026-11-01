#!/usr/bin/env python3
"""#5212 round 4, 2026-11-01: offline pytest with external scratch evidence.

Inputs: --tree source/archive, --basetemp below scratch-5212fix, pytest args.
Outputs: log at caller, JSON phase ledger beside basetemp. No remote commands.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from d41_legacy_controls_20261029 import bootstrap

parser = argparse.ArgumentParser()
parser.add_argument('--tree', type=Path, required=True)
parser.add_argument('--basetemp', type=Path, required=True)
parser.add_argument('--test-overlay', action='append', default=[])
options, args = parser.parse_known_args()
root, base = options.tree.resolve(), options.basetemp.resolve()
assert 'scratch-5212fix' in base.parts
base.parent.mkdir(parents=True, exist_ok=True)
overlays = {}
for name in options.test_overlay:
    relative = Path(name)
    assert relative.parts[0] == 'tests' and '..' not in relative.parts
    source = Path(__file__).resolve().parents[2] / relative
    shutil.copyfile(source, root / relative)
    overlays[name] = hashlib.sha256(source.read_bytes()).hexdigest()
environment = bootstrap(root, base.parent)
environment['test_overlays'] = overlays
git_binary = shutil.which('git')
binary = base.parent / (base.name + '-offline-bin')
binary.mkdir(exist_ok=True)
(binary / 'git').write_text((Path(__file__).parent / 'd68_local_git_20261030.sh').read_text().replace(
    '__D68_GIT_BINARY__', shlex.quote(git_binary)))
(binary / 'git').chmod(0o700)
os.environ.update(PATH=str(binary) + os.pathsep + str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH'],
                  VIRTUAL_ENV=str(Path(sys.executable).parent.parent), POETRY_VIRTUALENVS_CREATE='false',
                  POETRY_CACHE_DIR=str(base.parent / 'poetry'))
os.environ.pop('PYTEST_DISABLE_PLUGIN_AUTOLOAD', None)
tempfile.tempdir = os.environ['TMPDIR']
import pytest

class Observer:
    reports = []
    selected = []
    errors = []

    def pytest_collection_finish(self, session):
        self.selected = [item.nodeid for item in session.items]

    @pytest.hookimpl(optionalhook=True)
    def pytest_xdist_node_collection_finished(self, node, ids):
        if self.selected:
            assert self.selected == list(ids), 'worker collections differ'
        self.selected = list(ids)

    def pytest_collectreport(self, report):
        if report.failed:
            self.errors.append({'nodeid': report.nodeid, 'message': str(report.longrepr)})

    def pytest_runtest_logreport(self, report):
        row = {'nodeid': report.nodeid, 'when': report.when, 'outcome': report.outcome,
               **({'message': str(report.longrepr)} if report.failed or report.skipped else {})}
        self.reports.append(row)
        if report.failed:
            # Preserve diagnostics during a long shard, including interruption.
            with base.with_suffix('.failures.jsonl').open('a') as stream:
                stream.write(json.dumps(row) + '\n')

observer = Observer()
code = pytest.main([*args, '--basetemp', str(base), '-p', 'no:cacheprovider'], plugins=[observer])
base.with_suffix('.json').write_text(json.dumps({'exit_code': int(code), 'args': args,
    'tree': str(root), 'environment': environment, 'selected': observer.selected,
    'reports': observer.reports, 'collection_errors': observer.errors}, indent=2))
raise SystemExit(code)
