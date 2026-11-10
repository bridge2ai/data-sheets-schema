#!/usr/bin/env python3
"""Inventory bounded package download caches, 2026-11-10; PR 5711 coordination.

Inputs: fixed pip/Poetry-artifact/uv-wheel/sdist/npm-content cache roots.
Output: one Markdown note with allocated sizes, timestamps, archive headers,
npm index provenance, and a read-only visible-open-file snapshot. No deletion,
installation or environment traversal. Ignored files are included; symlinks
are not followed. APFS clones and cross-tree hardlinks limit reclaim estimates.
"""
import argparse
import base64
import datetime as dt
import json
import os
from pathlib import Path
import stat
import subprocess
import time
import urllib.parse


USER_ROOT = Path('/Users/marcin')
ROOTS = [
    USER_ROOT / 'Library/Caches/pip', USER_ROOT / '.cache/pip',
    USER_ROOT / 'Library/Caches/pypoetry/artifacts',
    USER_ROOT / '.cache/pypoetry/artifacts',
    USER_ROOT / '.cache/uv/wheels-v5', USER_ROOT / '.cache/uv/wheels-v7',
    USER_ROOT / '.cache/uv/sdists-v9/pypi', USER_ROOT / '.cache/uv/sdists-v10/pypi',
    USER_ROOT / '.npm/_cacache/content-v2',
]
NOTE = Path('notes/reviews/python_download_cache_candidates_20261110.md')


def utc(value):
    return dt.datetime.fromtimestamp(value, dt.timezone.utc).isoformat(timespec='seconds')


def info(path, st):
    return dict(path=str(path), allocated=st.st_blocks * 512, apparent=st.st_size,
                links=st.st_nlink, inode=st.st_ino, device=st.st_dev,
                born=utc(st.st_birthtime), modified=utc(st.st_mtime),
                accessed=utc(st.st_atime))


def inventory(root):
    result = dict(root=str(root), status='complete', allocated=0, apparent=0,
                  count=0, files=[], errors=[], newest=None, symlinks=0)
    if not root.exists() or root.is_symlink():
        result['status'] = 'absent or symlink: not traversed'
        return result
    result['directory_times'] = info(root, root.stat())
    started, seen = time.monotonic(), set()
    def onerror(exc):
        result['errors'].append(str(exc))
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
        kept = []
        for name in dirs:
            path = Path(directory) / name
            if path.is_symlink():
                result['symlinks'] += 1
            elif name not in {'.venv', 'venv', 'node_modules', '.git'}:
                kept.append(name)
        dirs[:] = kept
        for name in files:
            path = Path(directory) / name
            try:
                st = path.lstat()
            except OSError as exc:
                result['errors'].append(str(exc))
                continue
            if stat.S_ISLNK(st.st_mode):
                result['symlinks'] += 1
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            result['count'] += 1
            identity = st.st_dev, st.st_ino
            if identity not in seen:
                seen.add(identity)
                result['allocated'] += st.st_blocks * 512
                result['apparent'] += st.st_size
            row = info(path, st)
            result['files'].append(row)
            if result['newest'] is None or row['modified'] > result['newest']['modified']:
                result['newest'] = row
        if time.monotonic() - started > 45 or result['count'] > 150000:
            result['status'] = 'bounded partial inventory'
            break
    result['files'].sort(key=lambda row: (-row['allocated'], row['path']))
    result['files'] = result['files'][:60]
    return result


def npm_provenance(rows):
    targets = {}
    for row in rows:
        parts = Path(row['path']).parts
        if 'content-v2' in parts:
            offset = parts.index('content-v2')
            if parts[offset + 1] == 'sha512':
                targets[''.join(parts[offset + 2:])] = row
    root = USER_ROOT / '.npm/_cacache/index-v5'
    started = time.monotonic()
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [name for name in dirs if not (Path(directory) / name).is_symlink()]
        for name in files:
            path = Path(directory) / name
            if path.is_symlink():
                continue
            try:
                lines = path.read_text(errors='replace').splitlines()
            except OSError:
                continue
            for line in lines:
                try:
                    record = json.loads(line.split('\t', 1)[1])
                    integrity = record.get('integrity') or ''
                    if not integrity.startswith('sha512-'):
                        continue
                    hex_digest = base64.b64decode(integrity.split('-', 1)[1]).hex()
                    if hex_digest not in targets:
                        continue
                    key = record.get('key', '')
                    if 'https://' in key:
                        url = urllib.parse.urlsplit(key[key.index('https://'):])
                        safe = (url.path.rsplit('/', 1)[-1] + ' (registry host: '
                                + (url.hostname or 'unknown') + ')')
                        targets[hex_digest].setdefault('npm_origins', set()).add(safe)
                except (ValueError, IndexError, TypeError):
                    continue
        if time.monotonic() - started > 30:
            return 'bounded partial npm index lookup'
    return 'complete npm index lookup for selected blob paths; no integrity rehash'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=NOTE)
    args = parser.parse_args()
    started = utc(time.time())
    roots = [inventory(root) for root in ROOTS]
    candidates = sorted([row for root in roots for row in root['files']
                         if row['allocated'] >= 32 * 1024**2],
                        key=lambda row: -row['allocated'])[:80]
    for row in candidates:
        with open(row['path'], 'rb') as source:
            magic = source.read(8)
        row['header'] = ('gzip' if magic.startswith(b'\x1f\x8b') else
                         'zip' if magic.startswith(b'PK\x03\x04') else 'unclassified')
        row['magic'] = magic.hex()
    provenance = npm_provenance(candidates)
    old_npm = [row for row in candidates if row['header'] == 'gzip'
               and row['modified'] < '2026-11-01T00:00:00+00:00'
               and row['links'] == 1
               and any(origin.startswith('codex-') and origin.endswith('(registry host: registry.npmjs.org)')
                       for origin in row.get('npm_origins', []))]
    old_npm_bytes = sum(row['allocated'] for row in old_npm)
    old_helper = subprocess.run(['/usr/bin/python3', '-B',
        'scripts/adhoc/inspect_download_cache_candidates_20261110.py', '--verify-candidates'],
        capture_output=True, text=True, timeout=35, check=True)
    homebrew = json.loads(old_helper.stdout)
    combined_proposal_bytes = old_npm_bytes + homebrew['allocated_bytes_sum']
    try:
        opened = subprocess.run(['/usr/sbin/lsof', '-nP', '-Fpcfn'],
                                capture_output=True, text=True, timeout=30)
        handles, pid, command, fd = [], None, None, None
        for line in opened.stdout.splitlines():
            if line.startswith('p'):
                pid = line[1:]
            elif line.startswith('c'):
                command = line[1:]
            elif line.startswith('f'):
                fd = line[1:]
            elif line.startswith('n') and any(line[1:].startswith(str(root) + '/') for root in ROOTS):
                handles.append(dict(pid=pid, command=command, fd=fd, path=line[1:]))
        lsof = dict(returncode=opened.returncode, stderr=opened.stderr[:2500], handles=handles)
    except subprocess.TimeoutExpired:
        lsof = dict(error='lsof exceeded 30 seconds; open-handle evidence unavailable', handles=[])
    end = utc(time.time())
    vfs = os.statvfs(USER_ROOT)
    lines = ['# Package download cache inventory, 2026-11-10', '',
             f'Observed {started} to {end}. Read-only inventory; no deletion authorized or performed.', '',
             f'Available bytes at report time: {vfs.f_bavail * vfs.f_frsize:,}.', '',
             'Allocated bytes are inode st_blocks × 512, deduplicated within each root only. '
             'APFS sharing and hardlinks mean allocated totals are not guaranteed reclaimed bytes. '
             'File timestamps were sampled before header reads; access times may be incomplete or stale.', '',
             'Excluded: uv/archive-v0, uv/environments-v2, uv/git-v0, uv/builds-v0, editable '
             'source caches, Poetry virtualenvs, installed environments, repositories and run evidence. '
             'uv wheel/sdist contents are inventoried without calling them disposable download archives.', '',
             f'Narrow proposal for owner consideration: {len(old_npm)} individually listed npm gzip blobs '
             f'identified by the existing index as Codex downloads, each modified before 2026-11-01 '
             f'and having one hardlink, total {old_npm_bytes:,} allocated bytes '
             f'({old_npm_bytes/1024**3:.3f} GiB). These are download archives, not the installed executables. '
             'No deletion is authorized; verify activity again immediately before any approved cleanup.', '',
             f"Together with the three Homebrew archives, this bounded proposal totals "
             f"{combined_proposal_bytes:,} allocated bytes ({combined_proposal_bytes/1024**3:.3f} GiB). "
             'That is an allocation estimate, not a guaranteed free-space gain.', '',
             '| Root | Allocated GiB | Files | Latest file modification UTC | Status |',
             '|---|---:|---:|---|---|']
    for root in roots:
        lines.append(f"| `{root['root']}` | {root['allocated']/1024**3:.3f} | {root['count']} | "
                     f"{root['newest']['modified'] if root['newest'] else 'none observed'} | "
                     f"{root['status']}; errors={len(root['errors'])}; symlinks skipped={root['symlinks']} |")
    lines += ['', '## Largest individual candidate files', '',
              'Headers identify archive formats only; they do not validate complete archive contents. '
              'npm package filenames and registry hosts come from existing cache index entries, '
              'without network calls or copying request URLs, headers, credentials, or email addresses.', '',
              '| Allocated bytes | Apparent bytes | Links | Born UTC | Modified UTC | Accessed UTC | Header | Exact path |',
              '|---:|---:|---:|---|---|---|---|---|']
    for row in candidates:
        lines.append(f"| {row['allocated']} | {row['apparent']} | {row['links']} | {row['born']} | "
                     f"{row['modified']} | {row['accessed']} | {row['header']} ({row['magic']}) | `{row['path']}` |")
    lines += ['', '## Exact npm proposal subset', '',
              'Every path below is included in the narrow allocated-byte sum above. This list is a proposal only.', '']
    for row in old_npm:
        lines.append(f"- `{row['path']}` ({row['allocated']:,} allocated bytes; "
                     + '; '.join(sorted(row['npm_origins'])) + ')')
    lines += ['', '## npm index provenance', '', provenance, '']
    for row in candidates:
        if 'content-v2' in row['path']:
            origins = sorted(row.get('npm_origins', []))
            lines.append(f"- `{row['path']}`: " + ('; '.join(origins) if origins else 'no matching index URL observed'))
    lines += ['', '## Visible open handles', '',
              'One non-root lsof snapshot; absence is not proof of future non-use or visibility '
              'into every process. Active npm/package jobs may open files after this snapshot.', '',
              '```json', json.dumps(lsof, indent=2), '```', '',
              '## Preserved Homebrew three-archive result', '',
              'Reverified with `scripts/adhoc/inspect_download_cache_candidates_20261110.py --verify-candidates`. '
              f"The three archives total {homebrew['allocated_bytes_sum']:,} allocated bytes "
              f"({homebrew['allocated_mib_sum']:.3f} MiB), consistent with the initial 611.6 MiB result. "
              'All three headers are gzip and each has one hardlink. The Boost archive has an access '
              'timestamp older than 180 days, which is only a staleness signal. lsof return code 1 with '
              'empty stdout/stderr means no matching visible open files in that snapshot, not a future-use guarantee.', '',
              '```json', json.dumps(homebrew, indent=2), '```', '',
              'Provenance helpers: `scripts/adhoc/inspect_download_cache_candidates_20261110.py` and '
              '`scripts/adhoc/inspect_python_download_caches_20261110.py`.', '',
              '## Limitations and proposed scope', '',
              'Only confirmed npm gzip blobs or explicit wheel/source archive files are individual '
              'download candidates. No uv extracted tree is proposed for deletion. npm content cache '
              'is distinct from installed node_modules, but deletion still requires explicit owner '
              'approval and a fresh activity/handle check. Cache index entries may refer to content '
              'removed individually, so prefer the package manager cleanup mechanism after reviewing '
              'active installers. Do not run cleanup while an installer is using the cache.', '',
              'Atime age alone is not disposal authority; no full-home absence or exhaustive safe-space '
              'claim is made. Missing roots were checked directly, independent of gitignore.']
    for root in roots:
        if root['errors']:
            lines += ['', f"Errors for {root['root']}: " + '; '.join(root['errors'][:5])]
    output = '\n'.join(lines) + '\n'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output)
    if args.output.read_text() != output:
        raise RuntimeError('report readback differs')
    print(json.dumps(dict(note=str(args.output.resolve()), bytes=len(output.encode()),
                         roots=[{k:v for k,v in root.items() if k not in {'files','directory_times','newest'}} for root in roots],
                         selected_candidate_bytes=sum(row['allocated'] for row in candidates),
                         proposed_old_codex_archives=len(old_npm), proposed_old_codex_bytes=old_npm_bytes,
                         combined_proposal_bytes=combined_proposal_bytes,
                         lsof=lsof), indent=2))


if __name__ == '__main__':
    main()
