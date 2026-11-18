"""Separate measured timings from issue 6289 scheduling estimates, 2026-11-18.

Inputs: 7b9497fc1 checkout and its a6d773e6a parent timing snapshot.
Outputs: measured base, bound estimates, sharder implementation and documentation.
Serves PR 5968, F1; no history or existing timing test changes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    timings = root / 'utils/ci_test_durations.json'
    current = json.loads(timings.read_bytes())
    base_raw = subprocess.check_output(['git', 'show',
        'a6d773e6a^:utils/ci_test_durations.json'], cwd=root)
    base = json.loads(base_raw)
    changed = {key: value for key, value in current['file_seconds'].items()
               if base['file_seconds'].get(key) != value}
    assert len(changed) == 25
    estimates = {'schema_version': 1, 'base_sha256': hashlib.sha256(base_raw).hexdigest(),
        'source': {'issue_6289_20261118': current['source']['issue_6289_20261118']},
        'file_seconds': changed}
    assert {**base['file_seconds'], **changed} == current['file_seconds']
    timings.write_bytes(base_raw)
    (root / 'utils/ci_scheduling_estimates.json').write_text(json.dumps(estimates, indent=2) + '\n')
    plugin = root / 'utils/pytest_shard.py'
    text = plugin.read_text()
    old = '        config._d4d_shard_weights = read_weights(timing_path)\n'
    new = '''        estimates_path = None
        repository_timings = Path(__file__).with_name("ci_test_durations.json")
        if lane == "ordinary" and Path(timing_path).resolve() == repository_timings.resolve():
            # Only the explicit ordinary lane using this repository's measured
            # base opts into its bound estimates. Custom inputs stay standalone.
            estimates_path = repository_timings.with_name("ci_scheduling_estimates.json")
        config._d4d_shard_weights = read_weights(timing_path, estimates_path=estimates_path)
'''
    assert text.count(old) == 1
    text = text.replace(old, new)
    start = text.index('def read_weights(path):')
    end = text.index('\n\ndef _estimates(', start)
    replacement = '''def _unique_timing_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate timing key: {key}")
        result[key] = value
    return result


def _timing_file_seconds(data):
    if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
            or data["schema_version"] != 1):
        raise ValueError("expected timing schema version 1")
    weights = data.get("file_seconds")
    if not isinstance(weights, dict) or not weights:
        raise ValueError("file_seconds must be a nonempty mapping")
    for name, duration in weights.items():
        if (not isinstance(name, str) or not name.endswith(".py")
                or type(duration) not in (int, float)
                or not math.isfinite(duration) or duration <= 0):
            raise ValueError(f"invalid file duration: {name}")
    return weights


def read_weights(path, *, estimates_path=None):
    """Read measured timings, optionally applying their explicitly bound estimates."""
    try:
        raw = Path(path).read_bytes()
        data = json.loads(raw, object_pairs_hook=_unique_timing_keys)
        weights = _timing_file_seconds(data)
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError) as exc:
        raise pytest.UsageError(f"invalid --ci-shard-timings: {exc}") from exc
    if estimates_path is None:
        return weights
    try:
        estimates = json.loads(Path(estimates_path).read_bytes(),
                               object_pairs_hook=_unique_timing_keys)
        if (not isinstance(estimates, dict) or set(estimates) != {
                "schema_version", "base_sha256", "source", "file_seconds"}):
            raise ValueError("expected schema_version, base_sha256, source and file_seconds")
        overlay = _timing_file_seconds(estimates)
        if estimates["base_sha256"] != hashlib.sha256(raw).hexdigest():
            raise ValueError("scheduling estimates base SHA-256 mismatch; refresh explicitly")
        if not isinstance(estimates["source"], dict) or not estimates["source"]:
            raise ValueError("scheduling estimates require source provenance")
        for name in overlay:
            if (Path(name).is_absolute() or ".." in Path(name).parts
                    or Path(name).as_posix() != name or "\\\\" in name):
                raise ValueError(f"invalid scheduling estimate path: {name}")
        return {**weights, **overlay}
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError) as exc:
        raise pytest.UsageError(f"invalid ordinary scheduling estimates: {exc}") from exc
'''
    text = text[:start] + replacement + text[end:]
    plugin.write_text(text)
    docs = root / 'utils/ci_sharding.md'
    text = docs.read_text()
    anchor = 'Timings are scheduling hints. They cannot select or omit tests.'
    assert text.count(anchor) == 1
    paragraph = '''The ordinary lane explicitly using this repository's
`utils/ci_test_durations.json` also loads its required sibling
`utils/ci_scheduling_estimates.json`. This separate document records conservative
scheduling estimates and their provenance without rewriting measured history.
Its schema version must be 1 and its `base_sha256` must match the exact measured
file bytes. Missing or malformed estimates, duplicate keys, invalid durations,
noncanonical paths, and a stale base digest refuse before tests run. Refresh the
measured file through the timing updater, then deliberately rederive or review
the estimates and rebind their digest; a refresh never silently approves them.

The estimates apply only in `--ci-lane=ordinary` with the repository timing path.
Unlaned sharding and custom timing files retain their standalone behavior.
Dedicated lanes forbid timing options and cannot activate these estimates.
No workflow change or additional timing authority is implicit in other modes.

'''
    docs.write_text(text.replace(anchor, paragraph + anchor))
    print(json.dumps({'base_sha256': hashlib.sha256(base_raw).hexdigest(),
        'overrides': len(changed), 'effective_weights_preserved': True}))


if __name__ == '__main__':
    main()
