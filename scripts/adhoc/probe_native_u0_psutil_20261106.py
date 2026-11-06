#!/usr/bin/env python3
"""U0/#4354, 2026-11-06: probe sandboxed process visibility, no recorder.

Inputs: physical venv psutil. Output: exclusive --out JSON. No command arguments
or environment values are collected. This does not qualify a host timing gate.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    sys.path.append(str(Path(sys.executable).parent.parent / 'lib' /
                        ('python' + sys.version.split()[0].rsplit('.', 1)[0]) / 'site-packages'))
    import psutil
    document = {'format': 'native_u0_psutil_visibility_v1', 'pid': os.getpid(),
                'rows': [], 'errors': [], 'not_a_gate': True}
    processes = list(psutil.process_iter())
    document['enumerated'] = len(processes)
    for process in processes:
        try:
            process.cpu_percent()
        except psutil.Error as exc:
            document['errors'].append({'pid': process.pid, 'stage': 'prime', 'error': type(exc).__name__})
    time.sleep(1)
    for process in processes:
        try:
            document['rows'].append({'pid': process.pid, 'ppid': process.ppid(),
                                     'cpu_percent': process.cpu_percent(), 'name': process.name()})
        except psutil.Error as exc:
            document['errors'].append({'pid': process.pid, 'stage': 'sample', 'error': type(exc).__name__})
    with args.out.open('x') as stream:
        json.dump(document, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'enumerated': document['enumerated'], 'observed': len(document['rows']),
                      'errors': len(document['errors'])}))


if __name__ == '__main__':
    main()
