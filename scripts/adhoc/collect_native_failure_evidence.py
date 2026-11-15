"""Collect bounded, redacted offline diagnostics; inputs: base and destination.

Outputs: sanitized tails and per-file redaction manifest. Issues 6261/6262,
2026-11-15. Configs, environment files and caches are excluded.
"""
import argparse
import json
import os
from pathlib import Path
import re
import stat

FILE_LIMIT = 2 * 1024 * 1024
TOTAL_LIMIT = 24 * 1024 * 1024
COUNT_LIMIT = 128
NAMES = {'stderr.txt', 'control.jsonl', 'transcript.jsonl', 'host-controller-timing.jsonl'}
DIRECTORY_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY


def identity(info):
    return info.st_dev, info.st_ino


def candidates(directory, relative=Path('.')):
    # Every listing and child open is anchored to the already opened parent.
    for name in sorted(os.listdir(directory), key=lambda name: (name not in NAMES, name)):
        try:
            listed = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if relative.name == 'native-attempt':
                if stat.S_ISREG(listed.st_mode) and (name in NAMES or
                        (name.startswith('host-clock-') and name.endswith('.json'))):
                    yield directory, relative / name, listed
            elif stat.S_ISDIR(listed.st_mode):
                child = os.open(name, DIRECTORY_FLAGS, dir_fd=directory)
                try:
                    if identity(os.fstat(child)) == identity(listed):
                        yield from candidates(child, relative / name)
                finally:
                    os.close(child)
        except OSError:
            continue


def redact(raw):
    text = raw.decode('utf-8', errors='strict')
    counts, placeholders = {}, []
    roots = [('workspace', os.environ.get('GITHUB_WORKSPACE', str(Path.cwd()))),
             ('runner_home', str(Path.home()))]
    rules = []
    for label, root in sorted(roots, key=lambda item: len(item[1]), reverse=True):
        if root and root != '/':
            rules.append((label, re.escape(root.rstrip('/')) + r'(?:/[^\s"\x27<>\\]*)?'))
    values = {value for name, value in os.environ.items()
              if value and re.search('TOKEN|KEY|SECRET|PASSWORD|AUTH|CREDENTIAL|COOKIE', name, re.I)}
    values |= {json.dumps(value)[1:-1] for value in values}
    if values:
        rules.append(('environment', '|'.join(re.escape(value) for value in sorted(values, key=len, reverse=True))))
    rules.extend([
        ('bearer', r'(?i)bearer\s+[A-Za-z0-9._~+/=-]+'),
        ('github', r'(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]+'),
        ('api_key', r'sk-[A-Za-z0-9_-]+'),
        ('aws', r'(?:AKIA|ASIA|AIDA|AROA|AIPA|ANPA|ANVA|ASCA)[A-Z0-9]{16}'),
        ('email', r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+\x40[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),
    ])
    for label, pattern in rules:
        placeholder = '[' + label.upper() + ']'
        text, count = re.subn(pattern, lambda match: placeholder, text)
        counts[label] = count
        if count:
            placeholders.append(placeholder)
    return text.encode('utf-8'), counts, placeholders


def collect(base, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    rows, used = [], 0
    omitted = {'unsafe_encoding': 0, 'redaction_expansion': 0, 'unsafe_open': 0}
    base_fd = os.open(base, DIRECTORY_FLAGS)
    try:
        for parent, relative, listed in candidates(base_fd):
            if len(rows) >= COUNT_LIMIT or used >= TOTAL_LIMIT:
                break
            limit = min(FILE_LIMIT, TOTAL_LIMIT - used)
            try:
                leaf = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                with os.fdopen(leaf, 'rb') as stream:
                    opened = os.fstat(stream.fileno())
                    if not stat.S_ISREG(opened.st_mode) or identity(opened) != identity(listed):
                        omitted['unsafe_open'] += 1
                        continue
                    size = opened.st_size
                    stream.seek(max(0, size - limit))
                    raw = stream.read(limit)
                # A partial first line may start inside a credential. Discard it.
                if size > limit:
                    raw = raw.partition(b'\n')[2]
                raw, counts, placeholders = redact(raw)
                # Redaction expansion must never exceed the original output bounds.
                if len(raw) > limit:
                    omitted['redaction_expansion'] += 1
                    continue
            except UnicodeError:
                omitted['unsafe_encoding'] += 1
                continue
            except OSError:
                omitted['unsafe_open'] += 1
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            used += len(raw)
            rows.append({'path': relative.as_posix(), 'source_bytes': size,
                         'saved_bytes': len(raw), 'tail_truncated': size > limit,
                         'redactions': counts, 'placeholders': placeholders})
    finally:
        os.close(base_fd)
    manifest = {'file_limit': FILE_LIMIT, 'total_limit': TOTAL_LIMIT, 'count_limit': COUNT_LIMIT,
                'saved_bytes': used, 'files': rows, 'omitted': omitted,
                'scope': 'Redacted offline diagnostics; incomplete leading lines and unsafe files omitted; tails are not replay evidence.'}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('basetemp')
    parser.add_argument('destination')
    args = parser.parse_args()
    collect(args.basetemp, args.destination)
