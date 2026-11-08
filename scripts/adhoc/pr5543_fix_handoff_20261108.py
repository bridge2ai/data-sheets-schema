"""PR #5543 fix handoff, 2026-11-08.
Inputs: committed Git state and scratch evidence; outputs: named report and one STATUS entry.
Offline, no send/provider path. Run only after validation and commit.
"""
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-d100-cleanup'
REPORT = ROOT.parent / 'plans/reviews/pr5543_fix_2026-11-08.md'
STATUS = ROOT.parent.parent / 'data-sheets-schema/notes/coordination/STATUS.md'
BASE = 'a98259dff'
MERGE = 'c6b74042adf5ef7c3355996240a69b9d25e449ca'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

assert not REPORT.exists(), 'Do not overwrite an existing handoff'
assert not git('status', '--porcelain'), 'Commit the completed work first'
head = git('rev-parse', 'HEAD')
twins = json.loads((SCRATCH / 'pr5543-draft-twins.json').read_text())
for row in twins:
    assert not (ROOT / row['path']).exists()
    assert hashlib.sha256((ROOT / row['attic']).read_bytes()).hexdigest() == row['sha256']
hashes = json.loads((SCRATCH / 'pr5543-stats-hashes.json').read_text())
for path, digest in hashes.items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
suite = ET.parse(SCRATCH / 'pr5543-schema.xml').getroot().find('testsuite')
assert suite is not None
assert suite.attrib['failures'] == suite.attrib['errors'] == suite.attrib['skipped'] == '0'
count = int(suite.attrib['tests'])
assert count > 0
own = git('diff', '--name-status', MERGE, head)
inherited = git('diff', '--name-status', BASE, MERGE)
assert not git('diff', MERGE, head, '--', 'src', 'tests', '.claude', 'data/ATTIC', 'README.md', 'CLAUDE.md')
table = '\n'.join(f"| `{r['path']}` | `{r['attic']}` | `{r['sha256']}` |" for r in twins)
stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
report = f"""# PR #5543 fix handoff — 2026-11-08

Completed offline on `agy/prepub-cleanup-20261108`; final commit `{head}`.
Start `{BASE}`; merge `{MERGE}` has second parent
`75463cb38e5c2528a409477968cfc3735dc0cd8f`. The requested no-fast-forward merge
completed without conflicts, rebasing or force. No push or GitHub operation.

## Results and PR-body facts

Statistics live in `data/schema_stats/`. Schema 3.2.0 has 79 classes, 301 slots,
18 enums, 242 permissible values, 19 types, 9 subsets, 39 prefixes and 36
multivalued slots. `data_use_permission` remains multivalued. D100's first item,
the version in `D4D_Core.yaml`, was already done by PR #5531.

Removed all 12 root drafts under owner decision D119. A whole-tree snapshot
manifest is not a blocking reference. All original bytes survive in ATTIC and
Git history; recovery is possible from `{BASE}`. No ATTIC file changed.
Hashes were recorded before removal and byte comparisons repeated immediately
before git rm. `D4D_Uses.yaml` was the single canary: its absence and surviving
nonempty twin were checked before removing the remaining eleven. This proves
tracked-path removal and retained content, not APFS physical space recovery.

| Removed root draft | Retained byte-identical twin | SHA-256 of both |
|---|---|---|
{table}

The exporter reads the actual merged-schema version and rejects a mismatching
JSON version. Every output resolves under the repository root. Recommendation
counts are assigned by issue label; their editorial input file remains required.
The header now names PR #5543. README documents the correct paths/command,
39 prefixes, prior label changes and the Main 70 / Unknown 9 attribution caveat.

Exactly four generated files changed relative to the starting head:
`extended_prefix_mappings.tsv` loses EFO, GO, MESH, MeSH and NCIT;
`extended_schema_metadata.tsv`, `level1_summary.tsv` and `ALL_STATS_COMBINED.tsv`
change 44 to 39. Other generated and supplementary exports are unchanged.
No unexpected generated-statistics change occurred. The merge brings 30 files
from the release branch, including source, tests, digest inventory and generated
OWL/JSON-LD churn; these are inherited changes, not extra cleanup edits.

## Validation and limitations

- `make check-sync`: exit 0. It checks existence and compares merged-YAML and
  Python-model modification times against the top-level full schema and its
  directly listed D4D imports. It does not compare semantic content, schema
  digests, core products, or committed statistics.
- Two-worker canary: 1 passed; nonempty JUnit checked before the full suite.
- `python -m pytest tests/test_schema/ -n 2 -q -p no:cacheprovider`: {count} passed,
  zero failures/errors/skips. Both invocations used the existing 3600-second
  process-group supervisor, explicit scratch basetemps/JUnit, TMPDIR and bytecode
  cache location. No full-suite or native-runtime acceptance is claimed.
- Regenerated using the two README commands through the existing offline runner,
  with selected-worktree `PYTHONPATH` and the primary checkout's existing venv.
  Re-ran the adapter by absolute path from `{SCRATCH}` using relative input
  `pr5543-level4.json`: all 25 statistics directory files are byte-identical to
  the root-cwd run. SHA-256 manifest: `pr5543-stats-hashes.json`.
- The schema tests exercise schema tooling; they do not detect stale committed
  TSVs. Draft follow-up issue below records that gap.
- Separate read-only diff review found no additional finding in this round.
  Whitespace check passes with existing TSV trailing-field/CRLF conventions
  allowed (`git -c core.whitespace=-blank-at-eol diff --check`).
- Cleanup edits introduce no changes under src, tests, .claude, ATTIC, or root
  README/CLAUDE relative to the merge. No protected file was manually edited.
  No network, fetch, push, gh, provider call or native agent executable was run.
  Quiet-window lock was absent at work-launch guards; no lock was removed.
  Git metadata writes required sandbox escalation; the first merge attempt was
  denied by the filesystem and then succeeded through the approved escalation.

Evidence is solely under `{SCRATCH}`: `pr5543-draft-twins.json`,
`pr5543-level4.json`, `pr5543-stats-hashes.json`, `pr5543-generate.log`,
`pr5543-export.log`, `pr5543-export-other-cwd.log`, `pr5543-sync.log`,
`pr5543-canary.log`, `pr5543-canary.xml`, `pr5543-schema-tests.log`,
`pr5543-schema.xml` and their basetemp/cache outputs. Helper provenance is committed
under scripts/adhoc. The report and STATUS entry are the explicitly named handoffs.

## Full changed-file lists

This fix relative to the merge:

```text
{own}
```

Inherited merge changes relative to the supplied starting head:

```text
{inherited}
```

## Draft issue for agy: D100-R1

Title: D100-R1: preserve Value-column alignment in combined statistics export

The initial D100 adapter placed reuse and quality values in the wrong columns
of `data/schema_stats/ALL_STATS_COMBINED.tsv`. A separate read-only review found
the defect; it was fixed before the original PR #5543 handoff. Reuse rows now
emit section, slot, usage count and units; quality rows emit section, metric,
count and status/examples. Record this review finding even though already fixed.
Link PR #5543 and close as fixed after confirming those rows against their basic
TSVs. This is an issue draft only; no issue has been filed during this offline task.

## Draft issue for agy: stale statistics detection

Title: Add a reproducibility gate for committed data/schema_stats exports

PR #5543's exports stayed green while the final PR #5531 schema removed five
prefixes. Existing schema tests do not compare committed TSVs, and check-sync
only compares file timestamps. Add a check-schema-stats target or test that
rebuilds generated exports into an isolated temporary directory and compares
their bytes to the committed files. Include every generated basic and extended
TSV, keep editorial recommendations explicit, exclude the documented historical
supplementary tables, and report the exact stale paths. Verify that a prefix
change fails the gate, regeneration passes, alternate working directories are
supported, and the check leaves the checkout unchanged. Use the comprehensive
SSSOM reproducibility tests as an existing pattern. Link PR #5543 and P3-1 in
the independent review. This is a draft for agy to file, not a filed issue.

Stopped after the report and one STATUS entry. Written {stamp}.
"""
assert chr(64) not in report
status = STATUS.read_text()
marker = 'PR #5543 fix round complete'
assert marker not in status
assert status.count('### codex\n') == 1
entry = f"\n- {stamp} — **{marker}; stopped.** `{head}` on `agy/prepub-cleanup-20261108`; merged `75463cb38` without conflicts, removed 12 hash-verified ATTIC duplicates under D119, hardened exporter and refreshed exactly four TSVs to 39 prefixes. check-sync exit 0 (timestamps only); schema tests {count} passed, canary 1 passed, at most two workers and 3600-second supervisors; alternate-cwd export identical across 25 files. Report: `d4d-executions/plans/reviews/pr5543_fix_2026-11-08.md`, with full paths/hashes and two issue drafts for agy. All scratch in scratch-d100-cleanup. Offline; no push/gh/provider/native executable or protected manual edits.\n"
REPORT.write_text(report)
assert REPORT.stat().st_size > 0
STATUS.write_text(status.replace('### codex\n', '### codex\n' + entry, 1))
assert STATUS.read_text().count(marker) == 1
print(REPORT)
print('Exactly one STATUS entry written; stop.')
