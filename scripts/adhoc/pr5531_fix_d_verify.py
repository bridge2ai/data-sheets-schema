"""Verify fix-D case accounting from saved evidence, 2026-11-08.

Inputs: scratch manifests, interrupted/completed JUnit, final environment retry.
Output: scratch-pr5531-fix/fix-d-verification.json. Serves PR5531 fix D.
"""
from collections import Counter
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

SCRATCH = Path(
    os.environ.get(
        'D4D_PR5531_FIX_SCRATCH',
        Path(__file__).resolve().parents[2].parent / 'scratch-pr5531-fix',
    )
)


def results(name):
    rows = {}
    for case in ET.parse(SCRATCH / name).iter('testcase'):
        if 'classname' not in case.attrib:
            continue
        status = next((tag for tag in ('failure', 'error', 'skipped')
                       if case.find(tag) is not None), 'passed')
        rows[(case.get('classname'), case.get('name'))] = status
    return rows


def key(node):
    path, *parts = node.split('::')
    return ('.'.join([path[:-3].replace('/', '.'), *parts[:-1]]), parts[-1])


manifest = json.loads((SCRATCH / 'fix-d-shard-remaining.json').read_text())
shard = results('fix-d-shard-remaining.xml')
prior = {key(node): 'passed' for node in manifest['completed']}
assert not shard.keys() & prior.keys()
shard.update(prior)
retry = results('fix-d-poetry-final.xml')
assert retry.keys() <= shard.keys()
shard.update(retry)
assert set(shard) == {key(node) for node in manifest['selected']}
focused = results('fix-d-focused.xml')
remaining = results('fix-d-remaining.xml')
assert not focused.keys() & remaining.keys()
focused.update(remaining)
assert len(focused) == json.loads((SCRATCH / 'fix-d-remaining.json').read_text())['collected']
summary = {'focused': dict(Counter(focused.values())),
           'shard': dict(Counter(shard.values())),
           'shard_selected': len(shard),
           'shard_unsuccessful': [list(k) + [v] for k, v in shard.items()
                                  if v in ('failure', 'error')],
           'prior_passes_before_submodule_overlay': manifest['completed']}
(SCRATCH / 'fix-d-verification.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
