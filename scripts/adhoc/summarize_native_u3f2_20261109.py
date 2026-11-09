"""U3-F2 evidence reconciliation and owner handoff, 2026-11-09.

Inputs: retained sequential test runs, full scanner reports, raw parity and new
owner bundle. Outputs: exact findings/counts/digests under scratch-native-u1u3/
u3f2. No packet installation, network, provider or native execution.
"""
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('u3f2_summary_base',
    ROOT / 'scripts/adhoc/summarize_native_u3f_20261109.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
s.OUT = s.SCRATCH / 'u3f2'


def scans(before_label, after_label, composed_label):
    paths = [s.OUT / name / 'scanner.json' for name in (before_label, after_label, composed_label)]
    reports = [json.loads(path.read_bytes()) for path in paths]
    runs = [json.loads((path.parent / 'run.json').read_bytes()) for path in paths]
    assert runs[0]['source_commit'] == runs[1]['source_commit'] == 'cf50d9a1c059f3b5030103378ccef33619475dde'
    assert runs[0]['tool_commit'] == 'bb287d90a61af18b320efe9eabf720d0f77fd72f'
    assert runs[1]['tool_commit'] == runs[2]['tool_commit']
    assert runs[1]['tool_sha256'] == runs[2]['tool_sha256']
    for run, path in zip(runs, paths):
        assert run['exit_code'] in (0, 1) and run['tool_unchanged']
        assert run['scanner_json_sha256'] == s.sha(path.read_bytes())
        assert run['seconds'] < 3300
    baseline = json.loads((s.SCRATCH / 'baseline-scanner.json').read_bytes())
    before = reports[0]
    assert before['violations'] == baseline['violations'] and len(before['violations']) == 9
    result = []
    for label, report, path, run in zip((before_label, after_label, composed_label), reports, paths, runs):
        differences = [row for row in report['violations'] if row not in before['violations']]
        result.append(dict(label=label, hits=len(report['hits']), violations=len(report['violations']),
            finding_by_finding=[dict(before=row, exact_matches=[v for v in report['violations'] if v == row])
                               for row in before['violations']],
            exact_nine_violation_parity=report['violations'] == before['violations'],
            extra_violations=differences, full_hits_equal_to_before=report['hits'] == before['hits'],
            sha256=s.sha(path.read_bytes()), source_commit=run['source_commit'],
            tool_commit=run['tool_commit'], tool_sha256=run['tool_sha256']))
    s.save('scanner-comparison.json', result)
    assert all(row['exact_nine_violation_parity'] for row in result), 'scanner violations changed'
    print(json.dumps([{k:v for k,v in row.items() if k != 'finding_by_finding'} for row in result]))


def packets(manifest_path):
    import os
    import subprocess
    if os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock'):
        raise RuntimeError('quiet window is active')
    manifest = json.loads(Path(manifest_path).read_bytes())
    tree, bundle = Path(manifest['tree']), Path(manifest['owner_bundle'])
    paths = [str(bundle / (row['name'] + '.patch')) for row in manifest['packets']]
    env = dict(PATH='/usr/bin:/bin', GIT_NO_LAZY_FETCH='1',
               GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null')
    command = ['git', '--no-replace-objects', '-c', 'core.hooksPath=/dev/null',
               '-c', 'protocol.allow=never', 'apply', '--check']
    subprocess.run(command + paths, cwd=ROOT, env=env, check=True, timeout=60)
    subprocess.run(command + ['--reverse'] + paths, cwd=tree, env=env, check=True, timeout=60)
    for row in manifest['packets']:
        assert s.sha((ROOT / row['target']).read_bytes()) == row['preimage_sha256']
        assert s.sha((tree / row['target']).read_bytes()) == row['postimage_sha256']
        assert s.sha((bundle / (row['name'] + '.patch')).read_bytes()) == row['patch_sha256']
        assert row['changed_from_u1'] == (row['name'] == 'canonical_hashes')
    result = dict(manifest=str(Path(manifest_path).resolve()), owner_bundle=str(bundle),
        forward_check=True, reverse_check=True, packet_hashes_verified=True,
        worktree_packets_installed=False, packets=manifest['packets'])
    s.save('owner-packet-verification.json', result)
    pointer = s.SCRATCH / 'owner-packets/u3f2-current.json'
    with pointer.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(owner_bundle=str(bundle), verified_packets=len(paths))))


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'scans':
        scans(*sys.argv[2:])
    elif mode == 'parity':
        s.parity(sys.argv[2])
        rows = json.loads((s.OUT / (sys.argv[2] + '-comparison.json')).read_bytes())
        assert len(rows) == 14 and all(row['equal'] for row in rows), 'raw instruction bytes differ'
    elif mode == 'summary':
        s.summary()
    elif mode == 'packets':
        packets(sys.argv[2])
    else:
        raise SystemExit('unknown mode')
