# Purpose: apply G1 review fixes; inputs: checked-out source; outputs: source edits.
# Issues 6204, 6209, 6210, 6219, 6226, 6228; 2026-11-14.
from pathlib import Path
import sys
p = Path('src/data_sheets_schema/native_permission_probe.py')
s = p.read_text()
if sys.argv[1] == '6204':
    anchor = '\n\ndef require_u4_runtime'
    s = s.replace(anchor, '''

@contextmanager
def _cleanup_signals():
    previous = {number: signal.signal(number, signal.SIG_IGN)
                for number in (signal.SIGINT, signal.SIGTERM)}
    try:
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)
''' + anchor, 1)
    for start, end in [('def _version(', '\n\ndef _run_native('), ('def _run_native(', '\n\ndef _inventory(')]:
        a = s.index(start)
        b = s.index(end, a)
        part = s[a:b]
        a1 = part.index('    finally:\n') + len('    finally:\n')
        # The cleanup block ends at the next top-level function-body statement.
        lines = part[a1:].splitlines(keepends=True)
        n = next((i for i, line in enumerate(lines) if line.strip() and not line.startswith('        ')), len(lines))
        part = part[:a1] + '        with _cleanup_signals():\n' + ''.join('    '+line if line.strip() else line for line in lines[:n]) + ''.join(lines[n:])
        s = s[:a] + part + s[b:]
p.write_text(s)
if sys.argv[1] == '6219':
    p = Path('src/data_sheets_schema/native_u4b_probe_sequence.py')
    s = p.read_text()
    start = s.index("    _new(root / 'expectation.json', expected_raw)", s.index('def produce_bound_probe'))
    end = s.index('\n\n\ndef validate_bound_probe', start)
    body = s[start:end]
    s = s[:start] + '    try:\n' + ''.join('    '+line+'\n' for line in body.splitlines()) + '''    except BaseException as exc:
        _new(root / 'bound-failure.json', canonical({
            'error_type': type(exc).__name__, 'message': str(exc),
            'authorization_sha256': sha(authorization_raw),
            'permission_directory_exists': (root / 'permission').exists()}))
        raise
''' + s[end:]
    p.write_text(s)
