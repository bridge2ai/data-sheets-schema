"""Merge the lead's candidate into the accepted manifest branch, 2026-11-14.

Inputs: accepted b91ecef87 and candidate 087a8d954 in the shared local Git store.
Outputs: merge/conflict provenance and the later focused integration handoff in
the assigned sibling scratch directory. No push, fetch, provider or native run.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BEFORE = 'b91ecef876170603653ad300d0e6566ae2995f16'
CANDIDATE = '087a8d954c20c1640f99683179047aaa32139e3d'
OUT = ROOT.parent / 'scratch-native-manifest-integration-20261114/continuation/candidate-integration'
SELF = str(Path(__file__).resolve().relative_to(ROOT))


def git(*args, check=True):
    return subprocess.run(['git', '--no-replace-objects', *args], cwd=ROOT,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def start():
    assert git('rev-parse', 'HEAD').stdout.decode().strip() == BEFORE
    assert git('rev-parse', '087a8d954').stdout.decode().strip() == CANDIDATE
    assert git('branch', '--show-current').stdout.decode().strip() == 'codex/native-manifest-integration-20261114'
    status = git('status', '--porcelain').stdout.decode().splitlines()
    assert status in ([], ['?? ' + SELF]), status
    OUT.mkdir()
    result = git('merge', '--no-commit', '--no-ff', CANDIDATE, check=False)
    (OUT / 'merge.stdout').write_bytes(result.stdout)
    (OUT / 'merge.stderr').write_bytes(result.stderr)
    unmerged = git('ls-files', '-u').stdout.decode().splitlines()
    paths = sorted({line.split('\t', 1)[1] for line in unmerged})
    stages = []
    for line in unmerged:
        meta, relative = line.split('\t', 1)
        stage = meta.split()[-1]
        raw = git('show', ':' + stage + ':' + relative).stdout
        target = OUT / 'conflicts' / (relative + '.stage-' + stage)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        stages.append({'path': relative, 'stage': stage, 'saved': str(target),
                       'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    data = {'before': BEFORE, 'candidate': CANDIDATE, 'returncode': result.returncode,
            'unmerged_index': unmerged, 'conflicts': paths, 'stages': stages,
            'diff_stat': git('diff', '--stat', BEFORE).stdout.decode()}
    save(OUT / 'merge-start.json', data)
    assert result.returncode == 0 or result.returncode == 1 and paths
    print(json.dumps({key: data[key] for key in ('before', 'candidate', 'returncode', 'conflicts')}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start', 'resolve'))
    args = parser.parse_args()
    if args.action == 'start':
        start()
    else:
        resolve()


def resolve():
    relative = 'src/data_sheets_schema/native_shared_capture_orchestration.py'
    assert git('diff', '--name-only', '--diff-filter=U').stdout.decode().splitlines() == [relative]
    path = ROOT / relative
    source = path.read_text()
    candidate = git('show', ':3:' + relative).stdout.decode()
    begin, end = 'def _base(', '\ndef initialize('
    original = candidate[candidate.index(begin):candidate.index(end)]
    resolved = original.replace('_admission=None):', "_admission=None, _manifest_mode='full'):", 1)
    anchor = '    # Standalone helpers need the same bounded, byte-keyed schema derivation\n'
    assert anchor in resolved
    resolved = resolved.replace(anchor, '    from . import native_environment_manifest\n' + anchor, 1)
    block = """        with controls_orchestration.loaded_controls() as controls:
            value = registration.verified(e.raw, classifier_projection=controls)
        composition, spec, captured_selection = reconstruct_composition(
            value['composition_raw_json'].encode('utf-8'))
"""
    assert resolved.count(block) == 1
    nested = "        with native_environment_manifest.verification_scope(mode=_manifest_mode):\n"
    nested += ''.join('    ' + line for line in block.splitlines(keepends=True))
    resolved = resolved.replace(block, nested, 1)
    result = source[:source.index(begin)] + resolved + source[source.index(end):]
    assert not any(marker in result for marker in ('<<<<<<<', '=======', '>>>>>>>'))
    path.write_text(result)
    git('add', relative)
    save(OUT / 'resolutions.json', [{'path': relative, 'conflict_hunks': source.count('<<<<<<<'),
        'resolution': 'Keep the candidate launch_derivations scope around all of _base; nest the manifest verification scope only around registration verification and composition reconstruction. Preserve full default and all light helper callers, callback prefix changes and live identity checks.',
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}])
    # Candidate whitespace is inherited evidence, outside this resolution.
    git('diff', '--check', '--cached', CANDIDATE)
    print(json.dumps({'resolved': relative, 'remaining': git('diff', '--name-only', '--diff-filter=U').stdout.decode()}))


if __name__ == '__main__':
    main()
