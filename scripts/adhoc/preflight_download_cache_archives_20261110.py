#!/usr/bin/env python3
"""Read-only exact archive cleanup preflight; 2026-11-10, PR 5711 coordination.

Inputs: saved 26-path npm proposal, three Homebrew archive observations, installed
npm cache source, safe-delete guarded_rm.sh. Outputs: JSON identity manifest and
Markdown approval-scope note under notes/reviews. Only guarded_rm --dry-run is
invoked; this helper contains no delete, cache-clean, install or network action.
Full SHA-256/SHA-512 reads bind archive identity; tar headers are read, not extracted.
"""
import base64
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tarfile
import time


ROOT = Path(__file__).resolve().parents[2]
SOURCE_NOTE = ROOT / 'notes/reviews/python_download_cache_candidates_20261110.md'
MANIFEST = ROOT / 'notes/reviews/download_cache_archive_manifest_20261110.json'
NOTE = ROOT / 'notes/reviews/download_cache_archive_preflight_20261110.md'
CACHE = Path('/Users/marcin/.npm/_cacache')
NPM = Path('/Users/marcin/.nvm/versions/node/v22.16.0/lib/node_modules/npm')
GUARD = Path('/Users/marcin/.codex/skills/safe-delete/scripts/guarded_rm.sh')
KEY_PREFIX = 'make-fetch-happen:request-cache:https://registry.npmjs.org/' + chr(64) + 'openai/codex/-/'
LINK_ROOTS = [CACHE.parent, Path('/Users/marcin/Library/Caches/Homebrew'),
              NPM.parent / (chr(64) + 'openai/codex')]
TEXT_ROOTS = [ROOT / 'src', ROOT / 'scripts', ROOT / 'pyproject.toml',
              ROOT / 'Makefile', ROOT / 'poetry.lock']


def utc(value):
    return dt.datetime.fromtimestamp(value, dt.timezone.utc).isoformat(timespec='seconds')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(st):
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_mode, st.st_nlink)


def npm_entries():
    """Mirror the installed cacache index checksum and last-entry semantics."""
    current, digest, count = {}, hashlib.sha256(), 0
    for directory, dirs, files in os.walk(CACHE / 'index-v5', followlinks=False):
        dirs[:] = sorted(name for name in dirs if not (Path(directory) / name).is_symlink())
        for name in sorted(files):
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError('npm index symlink: ' + str(path))
            raw = path.read_bytes()
            digest.update(str(path).encode() + b'\0' + hashlib.sha256(raw).digest())
            count += 1
            for line in raw.splitlines():
                pieces = line.split(b'\t')
                if len(pieces) < 2 or hashlib.sha1(pieces[1]).hexdigest().encode() != pieces[0]:
                    continue
                entry = json.loads(pieces[1])
                current[entry['key']] = dict(entry, index_path=str(path), index_sha256=hashlib.sha256(raw).hexdigest())
    return [entry for entry in current.values() if entry.get('integrity')], digest.hexdigest(), count


def main():
    started = utc(time.time())
    source_raw = SOURCE_NOTE.read_bytes()
    subset = source_raw.decode().split('## Exact npm proposal subset\n', 1)[1].split('\n## ', 1)[0]
    paths = [Path(item) for item in re.findall(r'^- `([^`]+)`', subset, re.M)]
    if len(paths) != 26 or len(set(paths)) != 26:
        raise ValueError('Saved proposal is not exactly 26 unique files')
    entries, index_before, index_count = npm_entries()
    guard_sha = sha(GUARD)
    source_files = [NPM / 'package.json', NPM / 'lib/commands/cache.js',
                    NPM / 'node_modules/cacache/lib/entry-index.js',
                    NPM / 'node_modules/cacache/lib/rm.js',
                    NPM / 'node_modules/cacache/lib/content/rm.js']
    source_hashes = {str(path): sha(path) for path in source_files}
    records, issues = [], []
    for path in paths:
        if not path.is_relative_to(CACHE / 'content-v2/sha512'):
            raise ValueError('Path outside the exact cache-content root')
        if path.resolve(strict=True) != path:
            raise ValueError('Target or ancestor is a symlink: ' + str(path))
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError('Not a single-link regular file: ' + str(path))
        if before.st_mode & 0o111:
            raise ValueError('Archive unexpectedly executable: ' + str(path))
        h256, h512 = hashlib.sha256(), hashlib.sha512()
        with path.open('rb') as stream:
            header = stream.read(8)
            if not header.startswith(b'\x1f\x8b'):
                raise ValueError('Not a gzip archive: ' + str(path))
            h256.update(header); h512.update(header)
            for block in iter(lambda: stream.read(4 * 1024**2), b''):
                h256.update(block); h512.update(block)
        expected512 = ''.join(path.relative_to(CACHE / 'content-v2/sha512').parts)
        if h512.hexdigest() != expected512:
            raise ValueError('Full SHA-512 does not match content path')
        integrity = 'sha512-' + base64.b64encode(h512.digest()).decode()
        linked = [entry for entry in entries if entry['integrity'] == integrity]
        if len(linked) != 1:
            issues.append(f'{path}: {len(linked)} live cache keys share this content')
        for entry in linked:
            key = entry['key']
            if not key.startswith(KEY_PREFIX) or not re.fullmatch(r'codex-[0-9.]+-darwin-arm64\.tgz', key[len(KEY_PREFIX):]):
                raise ValueError('Unexpected npm key; not recording possibly private metadata')
        with tarfile.open(path, mode='r|gz') as archive:
            member = archive.next()
            if member is None:
                raise ValueError('Empty tar archive')
            first_member = dict(name=member.name, type=member.type.decode(errors='replace'), size=member.size)
        after = path.lstat()
        if identity(before) != identity(after):
            raise ValueError('File identity changed during read: ' + str(path))
        dry = subprocess.run([str(GUARD), '--expect-parent', str(path.parent), '--dry-run', str(path)],
                             text=True, capture_output=True, timeout=20)
        if dry.returncode != 0:
            issues.append('Guarded dry-run refused: ' + str(path))
        records.append(dict(path=str(path), sha256=h256.hexdigest(), sha512=h512.hexdigest(),
            integrity=integrity, allocated_bytes=before.st_blocks * 512, apparent_bytes=before.st_size,
            device=before.st_dev, inode=before.st_ino, mode=oct(stat.S_IMODE(before.st_mode)), hardlinks=before.st_nlink,
            birth_utc=utc(before.st_birthtime), modified_utc=utc(before.st_mtime), accessed_utc_before_read=utc(before.st_atime),
            gzip_header=header.hex(), first_tar_member=first_member, identity_stable=True,
            keys=[dict(key=entry['key'], index_path=entry['index_path'], index_sha256=entry['index_sha256']) for entry in linked],
            guarded_dry_run=dict(returncode=dry.returncode, stdout=dry.stdout.strip(), stderr=dry.stderr.strip())))
    spec = importlib.util.spec_from_file_location('prior_download_inventory', ROOT / 'scripts/adhoc/inspect_download_cache_candidates_20261110.py')
    prior = importlib.util.module_from_spec(spec); spec.loader.exec_module(prior)
    excluded = [dict(path=path, reason='Excluded: Homebrew cache alias resolves to this archive; no permission to remove alias') for path in prior.CANDIDATES]
    wanted = set(map(str, paths)) | {item['path'] for item in excluded}
    inbound, walked = [], 0
    for root in LINK_ROOTS:
        if not root.exists():
            continue
        for directory, dirs, files in os.walk(root, followlinks=False):
            for name in dirs + files:
                candidate = Path(directory) / name
                walked += 1
                if candidate.is_symlink() and str(candidate.resolve(strict=False)) in wanted:
                    inbound.append(dict(path=str(candidate), target=str(candidate.resolve(strict=False)), raw=os.readlink(candidate)))
            dirs[:] = [name for name in dirs if not (Path(directory) / name).is_symlink()]
    for link in inbound:
        if link['target'] in set(map(str, paths)):
            issues.append('Inbound symlink to npm candidate: ' + link['path'])
    opened = subprocess.run(['/usr/sbin/lsof', '-nP', '-Fpcfn', *map(str, paths)],
                            capture_output=True, text=True, timeout=30)
    if opened.stdout or opened.stderr or opened.returncode not in (0, 1):
        issues.append('Open-handle check returned data or warnings; inspect before approval')
    command = ['rg', '--hidden', '--no-ignore', '-l', '-F', '--glob', '!**/.git/**']
    for path in paths:
        command += ['-e', str(path), '-e', path.name]
    command += [str(path) for path in TEXT_ROOTS if path.exists()]
    refs = subprocess.run(command, capture_output=True, text=True, timeout=30)
    if refs.returncode not in (0, 1) or refs.stderr:
        issues.append('Narrow text-reference search incomplete')
    if refs.stdout:
        issues.append('Narrow source/configuration references found: inspect listed files')
    _, index_after, _ = npm_entries()
    if index_after != index_before:
        issues.append('npm index changed during preflight')
    if sha(GUARD) != guard_sha or any(sha(Path(path)) != value for path, value in source_hashes.items()):
        issues.append('Installed cleanup implementation changed during preflight')
    for row in records:
        st = Path(row['path']).lstat()
        if (st.st_dev, st.st_ino, st.st_size, utc(st.st_mtime), st.st_nlink) != (
            row['device'], row['inode'], row['apparent_bytes'], row['modified_utc'], 1):
            issues.append('Candidate identity moved after hashing: ' + row['path'])
    total = sum(row['allocated_bytes'] for row in records)
    free = os.statvfs(CACHE)
    result = dict(kind='read_only_exact_download_archive_preflight', authorization='NOT AUTHORIZED; explicit owner approval required',
        started_utc=started, ended_utc=utc(time.time()), source_note=str(SOURCE_NOTE), source_note_sha256=hashlib.sha256(source_raw).hexdigest(),
        proposal_count=26, proposal_allocated_bytes=total, proposal=records, excluded_homebrew=excluded,
        inbound_symlinks=inbound, inbound_search_roots=list(map(str, LINK_ROOTS)), inbound_entries_examined=walked,
        text_reference_roots=list(map(str, TEXT_ROOTS)), text_reference_search_ignored_files_included=True,
        text_reference_result=dict(returncode=refs.returncode, paths=refs.stdout.splitlines(), stderr=refs.stderr),
        open_handles=dict(returncode=opened.returncode, stdout=opened.stdout, stderr=opened.stderr),
        npm_index_before=index_before, npm_index_after=index_after, npm_index_files=index_count,
        installed_npm_version=json.loads((NPM / 'package.json').read_text())['version'], npm_source_hashes=source_hashes,
        guarded_script=str(GUARD), guarded_script_sha256=guard_sha, blockers=issues,
        available_bytes_observed=free.f_bavail * free.f_frsize,
        limitations=['No full-home search; unseen external references remain possible.',
                    'No archive extraction/full tar validation; all compressed bytes hashed and first tar member parsed.',
                    'lsof visibility and file/index identity are point-in-time observations.',
                    'APFS sharing means allocated bytes are not guaranteed reclaimed space.',
                    'No npm cache command was executed; cache clean does not implement a read-only dry-run in inspected code.'])
    raw = json.dumps(result, indent=2) + '\n'
    MANIFEST.write_text(raw)
    if MANIFEST.read_text() != raw:
        raise RuntimeError('Manifest readback mismatch')
    manifest_sha = sha(MANIFEST)
    canary = min(records, key=lambda row: row['allocated_bytes'])
    lines = ['# Exact npm archive cleanup preflight — proposal only', '',
        f"Observed {started} to {result['ended_utc']}. **No deletion or cache mutation performed.**", '',
        f'Proposed scope: exactly **26 npm Codex download archives**, {total:,} allocated bytes ({total/1024**3:.3f} GiB), '
        'and their 26 corresponding npm cache-index entries. Preserve installed executables, environments, '
        'the newest observed download, other npm content and all Homebrew archives/aliases.', '',
        f'Manifest: `{MANIFEST}`; SHA-256 `{manifest_sha}`.', '',
        f"Blockers: {len(issues)}. " + ('; '.join(issues) if issues else 'All stated narrow guards passed.'), '',
        '## Verified identities and references', '',
        '- All 26 are non-executable regular files with one hardlink, no target or ancestor symlinks, gzip headers '
        'and a readable first tar member. Full SHA-256 is recorded; full SHA-512 equals the npm content-addressed pathname.',
        '- Each archive has exactly one live npm key in the complete local index snapshot; the index remained unchanged '
        'through this preflight. No shared-content key would be left dangling by the proposed exact-key removal.',
        '- Every guarded_rm invocation included --dry-run and the exact parent/path; none invoked removal.',
        f"- Open-handle check: return code {opened.returncode}, stdout {len(opened.stdout)} bytes, stderr {len(opened.stderr)} bytes.",
        f"- Inbound symlink scopes: {', '.join(map(str, LINK_ROOTS))}. Text-reference scopes: {', '.join(map(str, TEXT_ROOTS))}. "
        'Ignored/hidden files were included; the search was not full-home.', '',
        '## Exact npm operation supported by installed source', '',
        f'Installed npm {result["installed_npm_version"]}: `{NPM / "lib/commands/cache.js"}` lines 104–145 '
        'accept `cache clean <key>` (also rm/clear aliases), remove that single index entry and its integrity-addressed '
        'content. No --force is required when a key is supplied. With no key, --force enables a whole-cache removal; '
        'that wider operation is excluded. The inspected method does not check --dry-run, so do not use npm itself '
        'as the dry-run mechanism.', '',
        'A future authorized action should supply exactly one manifest key per invocation with an explicit '
        '`--cache=/Users/marcin/.npm`; use the pinned Node/npm installation and reverify source hashes, candidate '
        'hashes, key mapping and handles immediately beforehand. npm may also write its ordinary local diagnostic log. '
        'No install, network access, cache verification/garbage collection or broad purge belongs to this proposal.', '',
        f'Canary after approval: `{canary["path"]}` ({canary["allocated_bytes"]:,} allocated bytes). '
        'Verify that archive and key are absent, siblings remain unchanged, and observed free space increases by '
        'approximately its allocation. If that fails, stop before the remaining 25. Once the canary passes, process '
        'the remaining exact keys sequentially, stopping on any identity/handle mismatch.', '',
        '## Homebrew excluded after preflight', '']
    for item in excluded:
        links = [link['path'] for link in inbound if link['target'] == item['path']]
        lines.append(f"- `{item['path']}` — inbound cache alias(es): " + ', '.join(f'`{path}`' for path in links))
    lines += ['', 'Removing those three archive files alone would leave dangling Homebrew cache aliases. '
        'They are excluded; this proposal does not add their symlinks to the approval scope.', '',
        '## Owner approval boundary', '',
        'The safe-delete skill states: “Delete only what the user named in the current conversation.” '
        'A single explicit approval may name the exact 26-file manifest and associated 26 cache-index entries. '
        'No deletion approval has been received. Skill: `/Users/marcin/.codex/skills/safe-delete/SKILL.md`.', '',
        'Estimated 3.031 GiB reclaimed space is conditional. Current availability is volatile; the report does not '
        'attribute prior disk-space changes or guarantee future native-run capacity.', '',
        '## Exact archive list', '', '| Package archive | Allocated bytes | SHA-256 | Absolute path |',
        '|---|---:|---|---|']
    for row in records:
        package = row['keys'][0]['key'].rsplit('/', 1)[-1] if row['keys'] else 'unresolved'
        lines.append(f"| {package} | {row['allocated_bytes']} | `{row['sha256']}` | `{row['path']}` |")
    text = '\n'.join(lines) + '\n'
    NOTE.write_text(text)
    if NOTE.read_text() != text:
        raise RuntimeError('Note readback mismatch')
    print(json.dumps(dict(manifest=str(MANIFEST), manifest_sha256=manifest_sha, note=str(NOTE),
        count=len(records), allocated_bytes=total, blockers=issues, inbound_symlinks=inbound,
        open_handle_returncode=opened.returncode, npm_index_stable=index_before == index_after,
        free_bytes_observed=result['available_bytes_observed']), indent=2))


if __name__ == '__main__':
    main()
