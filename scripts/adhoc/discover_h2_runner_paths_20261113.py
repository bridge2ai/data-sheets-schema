#!/usr/bin/env python3
"""Remove personal native-executable paths from helper-2 runners, 2026-11-13.
Inputs: three explicitly owned runners. Outputs: runtime path discovery,
preserving their network, executable-name and scratch-write sandbox rules.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
names = ('run_helper_cache_tests_20261112.py', 'run_native_h2_tests_20261112.py',
         'run_native_h2_sequence_tests_20261112.py')
replacement = '''def native_paths():
    """Discover denied executable paths without invoking any executable."""
    paths = set()
    for name in ('claude', 'codex', 'gemini', 'agy'):
        paths.update(str(directory / name) for directory in (
            Path.home() / '.local/bin', Path('/opt/homebrew/bin'), Path('/usr/local/bin')))
        paths.update(str(path) for path in Path.home().glob('.nvm/versions/node/*/bin/' + name))
        found = shutil.which(name)
        if found is not None:
            paths.add(found)
    return tuple(sorted(paths))


NATIVE_PATHS = native_paths()'''
for name in names:
    path = root / 'scripts/adhoc' / name
    text = path.read_text()
    start = text.index('NATIVE_PATHS = (')
    end = text.index('\n)', start) + 2
    text = text[:start] + replacement + text[end:]
    assert text.count('import signal\n') == 1
    text = text.replace('import signal\n', 'import signal\nimport shutil\n')
    path.write_text(text)
