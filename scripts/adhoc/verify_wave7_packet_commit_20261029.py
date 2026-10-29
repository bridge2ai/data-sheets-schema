#!/usr/bin/env python3
# Purpose: verify Wave7 evidence from committed Git blobs, including ignored pytest logs.
# Inputs: local commit, relative packet path and optional extra files; output: JSON verification.
# Refs #5212 / #5162; 2026-10-29. Read-only Git; no network, tests or providers.
"""Verify every manifest digest against the commit, not merely the working tree."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=dict(os.environ, GIT_NO_LAZY_FETCH='1')).stdout


def safe(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError('relative repository path required')
    return path.as_posix()


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main(options):
    commit = git('rev-parse', options.commit + '^{commit}').decode().strip()
    packet = safe(options.packet)
    manifest_name = packet + '/manifest.json'
    manifest_raw = git('show', commit + ':' + manifest_name)
    manifest = json.loads(manifest_raw)
    files = {}
    for name, expected in sorted(manifest['files'].items()):
        path = packet + '/' + safe(name)
        actual = identity(git('show', commit + ':' + path))
        if actual != expected:
            raise ValueError('committed evidence differs: ' + path)
        files[path] = actual
    extras = {}
    for name in options.extra:
        name = safe(name)
        raw = git('show', commit + ':' + name)
        if raw != (ROOT / name).read_bytes():
            raise ValueError('committed extra differs from reviewed worktree: ' + name)
        extras[name] = identity(raw)
    result = {'commit': commit, 'packet': packet, 'manifest': identity(manifest_raw),
              'verified_file_count': len(files), 'files': files, 'extras': extras,
              'all_packet_blobs_verified': True, 'network_or_provider_calls': False}
    if options.output:
        with options.output.open('x') as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write('\n')
    print(json.dumps({'commit': commit, 'verified_file_count': len(files),
                      'manifest_sha256': result['manifest']['sha256'],
                      'extras': extras, 'all_packet_blobs_verified': True}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', default='HEAD')
    parser.add_argument('--packet', required=True)
    parser.add_argument('--extra', action='append', default=[])
    parser.add_argument('--output', type=Path)
    main(parser.parse_args())
