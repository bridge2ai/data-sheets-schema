#!/usr/bin/env python3
"""U0/#4354, 2026-11-06: test unprivileged ps under network denial.

Input: macOS /bin/ps. Output: exclusive --out evidence, exact binary and result.
No recorder, native runtime, provider, or network operation is invoked.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(mode=0o700, exist_ok=False)
    source = Path('/bin/ps')
    raw = source.read_bytes()
    copied = out / 'ps-unprivileged'
    with copied.open('xb') as stream:
        stream.write(raw)
    copied.chmod(0o700)
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': str(out), 'LC_ALL': 'C'}
    command = ['/usr/bin/sandbox-exec', '-p', '(version 1)(allow default)(deny network*)',
               str(copied), '-A', '-o', 'pid=,ppid=,pcpu=,comm=']
    result = subprocess.run(command, env=env, cwd=out, capture_output=True, timeout=15)
    (out / 'ps.stdout').write_bytes(result.stdout)
    (out / 'ps.stderr').write_bytes(result.stderr)
    document = {'command': command, 'returncode': result.returncode,
                'source_mode': stat.S_IMODE(source.stat().st_mode),
                'copy_mode': stat.S_IMODE(copied.stat().st_mode),
                'source_sha256': hashlib.sha256(raw).hexdigest(),
                'copy_sha256': hashlib.sha256(copied.read_bytes()).hexdigest(),
                'same_bytes': copied.read_bytes() == raw,
                'rows': len(result.stdout.splitlines()),
                'own_pid_present': any(line.split()[0] == str(os.getpid()).encode()
                                       for line in result.stdout.splitlines() if line.split())}
    (out / 'result.json').write_text(json.dumps(document, indent=2) + '\n')
    print(json.dumps(document, sort_keys=True))
    return 0 if result.returncode == 0 and document['own_pid_present'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
