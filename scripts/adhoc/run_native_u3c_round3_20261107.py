"""Round-3 offline validation, 2026-11-07; serves the U3-C re-merge brief.

Inputs: explicit pytest nodes and fresh output under scratch-native-u3c-r3.
Outputs: inherited isolated-runner evidence. Adds UTC-aware deadline and
native-executable denial without changing the inherited tested runner.
"""
import importlib.util
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3c-r3'
spec = importlib.util.spec_from_file_location('u3a_runner', ROOT / 'scripts/adhoc/run_native_u3a_tests_20261107.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.PROFILE += '(deny process-exec (regex #"/(claude|codex|gemini|agy)(/|$)"))\n'

original_make_venv = runner.make_test_venv


def nested_dependency_venv(out, dependencies):
    """Make installed dependencies visible to test-created nested venvs.

    Those fixtures append this site directory without processing its .pth
    paths. Link dependency entries, excluding startup hooks and project code;
    never execute dependency editable-install hooks or change the dependency venv.
    """
    python = original_make_venv(out, dependencies)
    site = out / 'venv/lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
    links = {}
    for item in sorted(dependencies.iterdir()):
        if (item.name.endswith('.pth') or item.name.startswith('__editable__')
                or item.name in {'__pycache__', 'sitecustomize.py', 'usercustomize.py', 'data_sheets_schema'}):
            continue
        target = site / item.name
        if target.exists():
            continue
        target.symlink_to(item, target_is_directory=item.is_dir())
        links[item.name] = str(item)
    runner.save(out / 'dependency-links.json', links)
    return python


class DeadlineClock:
    """Count elapsed suspend time as well as monotonic elapsed time."""
    def __init__(self):
        self.mono = time.monotonic()
        self.wall = time.time()

    def monotonic(self):
        return self.mono + max(time.monotonic() - self.mono, time.time() - self.wall)

    sleep = staticmethod(time.sleep)


if __name__ == '__main__':
    if '--nested-dependencies' in sys.argv:
        sys.argv.remove('--nested-dependencies')
        runner.make_test_venv = nested_dependency_venv
    if '--out' not in sys.argv:
        raise SystemExit('--out required')
    output = Path(sys.argv[sys.argv.index('--out') + 1]).absolute()
    if output.parent != SCRATCH or output != output.resolve():
        raise SystemExit('output must be a new direct child of assigned scratch')
    runner.time = DeadlineClock()
    raise SystemExit(runner.main())
