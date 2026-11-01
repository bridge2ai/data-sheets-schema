# D52 original validation, compact publication view

The original baseline failure and fixed result are preserved verbatim under
`compact/run-01/` and `compact/run-02/`. This is an evidence-packaging change
for Claude's review D3, assigned in STATUS at 2026-10-28T18:24Z. It does not
rerun scoring, change a result, or erase the original evidence.

The unchanged `manifest.json` is the **original archive manifest**, not a file
inventory of this publication checkout. Each compact run has its own
`compact-manifest.json` naming the original archive, every retained file's
bytes/mode/SHA-256, both omitted source inventories, and exact recovery commands.
The original archives remain in Git at
`4cd8f2a5191d7cb58d7bf639603a820d38e825d5` and in the original D52 and Wave5
evaluation worktrees. Their existing external evidence directories remain intact.

| Run | Original result | Original compressed bytes | Retained result bytes |
|---|---|---:|---:|
| run-01 | 20 passed / 11 failed baseline | 1,497,408 | 33,232 |
| run-02 | 112 passed fixed | 1,498,111 | 38,772 |

Retained bytes include logs, JUnit, outcomes, plans, import-origin checks,
bootstrap and scoring identity. Compact manifests are additional metadata.
The two source inventory files per run are represented by hashes and recovery
commands. A tracked-tree listing can be regenerated from each named source
commit with the recorded `git ls-tree -r -l` command; it is not claimed to
reproduce the original JSON's run metadata. Exact original JSON is recovered
from the preserved archive object instead.

Example exact inventory recovery, without modifying any checkout:

```sh
git show 4cd8f2a5191d7cb58d7bf639603a820d38e825d5:notes/d52_scoring_validation_2026-10-28/run-01.tar.gz | tar -xzOf - results/source-before.json
```

The helper `scripts/adhoc/compact_d52_publication_evidence_20261028.py` checks
the immutable archive against the original manifest, validates every regular
member's bytes and mode, and refuses unexpected paths or an existing output.
Run1 was generated and its persisted outcome/JUnit checked before run2. The
helper never mutates originals, extracts into historical directories or makes
a network request. Only the two tarballs are omitted from the new publication
tree; no Git history is rewritten, so this reduces the PR's file payload rather
than claiming to reduce the size of historical Git objects.

Compact manifest SHA-256:

- run-01: `0f0d3e73bcba049b8c53ef9142c815b2b4d80446ecfb98f2e970ecbcbbeb5970`
- run-02: `ffb653a48560a99ef91d8f612e16c9a4e904eaae106910f7b2c1d382f1d54133`
