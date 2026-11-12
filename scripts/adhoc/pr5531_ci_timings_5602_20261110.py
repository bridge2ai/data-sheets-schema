"""PR #5531 P3-e (#5602) CI timing refresh, 2026-11-10.

Purpose: Replace the unscaled local macOS weights added in Fix C
(source.pr5531_fix_c_local_20261108) for tests/test_pr5531_regressions.py and
tests/test_bc1_pipeline.py with measured GitHub Actions runner JUnit timings
from PR #5531 green CI run 42534095997 (commit 4ac73609c328bce8d7a48469eba4a0c73a07ee49).
Inputs: downloaded CI JUnit XML artifacts for shards 2 and 6 of run 42534095997.
Outputs: additive provenance block source.pr5531_ci_refresh_5602_20261110 and
updated file_seconds in utils/ci_test_durations.json.
"""
import hashlib
import json
import os
from pathlib import Path

from utils.update_ci_shard_timings import build

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACTS = (
    ROOT.parent
    / 'scratch-pr5531-rereview'
    / 'ci-artifacts'
    / 'run42534095997'
)
RUN_ID = 42534095997
COMMIT = '4ac73609c328bce8d7a48469eba4a0c73a07ee49'
TARGETS = ('tests/test_pr5531_regressions.py', 'tests/test_bc1_pipeline.py')


def main(artifact_dir=None):
    folder = Path(
        artifact_dir
        or os.environ.get('D4D_PR5531_CI_ARTIFACTS', DEFAULT_ARTIFACTS)
    )
    path = ROOT / 'utils/ci_test_durations.json'
    baseline = path.read_text()
    data = json.loads(baseline)
    result = build(folder, ROOT, RUN_ID, COMMIT)
    updates = {target: result['file_seconds'][target] for target in TARGETS}
    artifacts = [
        {
            'path': f'run{RUN_ID}/{rel.relative_to(folder).as_posix()}',
            'sha256': hashlib.sha256(rel.read_bytes()).hexdigest(),
        }
        for rel in sorted(folder.glob('*/pytest.xml'))
    ]
    before = {name: data['file_seconds'].get(name) for name in TARGETS}
    data['file_seconds'].update(updates)
    data['file_seconds'] = dict(sorted(data['file_seconds'].items()))
    data['source']['pr5531_ci_refresh_5602_20261110'] = {
        'run_id': RUN_ID,
        'commit': COMMIT,
        'url': f'https://github.com/bridge2ai/data-sheets-schema/actions/runs/{RUN_ID}',
        'kind': 'GitHub Actions Python 3.12 shard JUnit measurement (#5602)',
        'method': 'utils.update_ci_shard_timings.build; sum CI JUnit case seconds for target files',
        'artifacts': artifacts,
        'previous_file_seconds': before,
        'file_seconds': updates,
    }
    marker = '  "union_provenance": '
    rendered = (
        (json.dumps(data, indent=2) + '\n').split(marker)[0]
        + marker
        + baseline.split(marker)[1]
    )
    assert json.loads(rendered) == data
    path.write_text(rendered)
    print(json.dumps(data['source']['pr5531_ci_refresh_5602_20261110'], indent=2))


if __name__ == '__main__':
    main()
