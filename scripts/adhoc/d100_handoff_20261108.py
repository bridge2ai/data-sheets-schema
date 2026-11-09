"""D100 / PR #5531 follow-up handoff, 2026-11-08.
Inputs: scratch audit/JUnit, generated exports, committed Git identity.
Outputs: verification JSON, named review report, exactly one codex STATUS entry.
Run 'verify' before commit and 'report' after commit. Offline only.
"""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-d100-cleanup'
REPORT = ROOT.parent / 'plans/reviews/d100_cleanup_2026-11-08.md'
STATUS = ROOT.parent.parent / 'data-sheets-schema/notes/coordination/STATUS.md'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

def table(name):
    with (ROOT / 'data/schema_stats' / name).open(newline='') as f:
        return list(csv.reader(f, delimiter='\t'))

rows = json.loads((SCRATCH / 'draft-audit.json').read_text())
manifest_path = 'notes/legacy_semantic_publication_2026-10-11_01/provenance/publication/source-before.json'
manifest = json.loads((ROOT / manifest_path).read_text())
assert len(rows) == 12
for row in rows:
    root = ROOT / row['path']
    assert root.read_bytes() == (ROOT / 'data/ATTIC/root_schema_drafts_2026-08-08' / root.name).read_bytes()
    assert hashlib.sha256(root.read_bytes()).hexdigest() == row['sha256'] == manifest[root.name]['sha256']
metadata = dict(table('extended_schema_metadata.tsv')[1:])
assert metadata['Version'] == '3.2.0'
for filename, key in [('extended_class_details.tsv', 'Total Classes'), ('extended_slot_details.tsv', 'Total Slots'), ('extended_enum_summary.tsv', 'Total Enums'), ('extended_type_system.tsv', 'Total Types'), ('extended_prefix_mappings.tsv', 'Total Prefixes')]:
    assert len(table(filename)) - 1 == int(metadata[key]), (filename, key)
summary = dict(table('level1_summary.tsv')[1:])
assert all(summary[k] == metadata[k] for k in summary)
assert len(table('extended_enum_values.tsv')) - 1 == 242
assert not git('diff', '5d6dd97c2', '--', 'src', 'tests', '.claude', 'README.md', 'CLAUDE.md', 'data/ATTIC')
suites = ET.parse(SCRATCH / 'schema.xml').getroot().findall('testsuite')
counts = {k: sum(int(s.get(k, 0)) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
assert counts['tests'] > 0 and not any(counts[k] for k in ('failures', 'errors', 'skipped')), counts
verification = {'metadata': metadata, 'pytest': counts, 'retained_root_drafts': rows, 'protected_diff': 'empty', 'root_reference_manifest': manifest_path}
(SCRATCH / 'verification.json').write_text(json.dumps(verification, indent=2) + '\n')
if sys.argv[1] == 'verify':
    print(json.dumps({'metadata': metadata, 'pytest': counts}, indent=2))
    raise SystemExit
assert sys.argv[1] == 'report'
assert not git('status', '--porcelain')
head = git('rev-parse', 'HEAD')
now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
ledger = '\n'.join(f"| `{r['path']}` | {r['bytes']} | identical | retained: manifest reference |" for r in rows)
text = f'''# D100 cleanup handoff — 2026-11-08

Completed at {now}, offline in `{ROOT}`.
Branch: `agy/prepub-cleanup-20261108`; base `5d6dd97c290e99047a11a89362eab75990d225a8`;
local commit `{head}`. No push or PR creation; agy owns publication.

## Disposition

All 12 root drafts are byte-identical to their ATTIC counterparts, but all 12
have explicit repository-root path/hash references in `{manifest_path}` (and
its source-after counterpart). The brief says to keep referenced copies, so
**none were deleted**. These are historical provenance references, not a claim
that runtime code needs the drafts. ATTIC copies and provenance are unchanged.
No disk space was reclaimed; no deletion canary was applicable.

| Root path | Bytes | ATTIC comparison | Action |
|---|---:|---|---|
{ledger}

Search used `rg --files --hidden --no-ignore`, then `rg --no-ignore --hidden -n -F`
on enumerated non-secret files, including ignored material. Exclusions: Git
metadata, dependency/bytecode directories, .aws/.ssh, .env names and filenames
containing credential/secret/token. Binary content was not forced to text.
No absence claim is needed: the explicit manifest references suffice to retain.
The initial argument list exceeded macOS limits; the helper was corrected to
search 200 paths per invocation and the complete audit succeeded.

## Statistics and documentation

The repository command `python -m data_sheets_schema.cli schema stats --level 4
--format json --output <scratch>/level4.json` produced schema 3.2.0 statistics.
The persisted canary JSON was nonempty and inspected before generating exports.
The committed TSV adapter uses that JSON and the existing
`.claude/agents/scripts/schema_stats_extended.py` exporter.

Current exports: **79 classes, 301 slots, 18 enums, 242 permissible values,
19 types, 44 prefixes, 9 subsets**. Basic level 1–4 tables, combined table and
extended tables were regenerated. Extended type data remained byte-identical.
The combined table now includes every range category from the statistics command.

`rai_*.tsv` and `d4d_properties*.txt` are retained historical selected/editorial
lists, not outputs of the repository stats command. No generator for these
selected tables was found in the hidden/ignored-inclusive non-data search;
their completeness for 3.2.0 is **not claimed**. The directory README now makes
this boundary and the repeatable regeneration command explicit. This is a
limitation of the directory refresh, for lead disposition if those lists must
also become current.

Root README.md and CLAUDE.md contain no current schema-version declaration to
replace. Both remain unchanged. CLAUDE.md's 3.0.0 historical release-note link
is a historical reference and was preserved.

## Validation and review

- `make check-sync`: exit 0 (the repository gate checks timestamps, not semantic equivalence).
- Two-worker canary: 1 passed; nonempty JUnit verified before full run.
- `pytest tests/test_schema/ -n 2 -q -p no:cacheprovider`: {counts['tests']} passed,
  zero failures/errors/skips. Each invocation used a 3600-second supervisor,
  explicit scratch basetemp/JUnit, scratch TMPDIR and PYTHONPYCACHEPREFIX.
- Python 3.13.12 from the existing primary checkout virtual environment;
  `PYTHONPATH={ROOT}/src:{ROOT}`. No dependency install.
- Export readback verified TSV record counts against schema metadata, basic
  counts against extended counts, and all 12 retained root/ATTIC/manifest hashes.
- Separate read-only diff review found a combined-table column alignment issue
  in the initial adapter; fixed outside the review pass and regenerated. Final
  inspection confirms metric values occupy the Value column. Local finding
  **D100-R1**: issue filing deferred to agy because this task forbids gh/network.
- Ordinary `git diff --check` flags the existing exporter’s CRLF and empty TSV
  fields; `git -c core.whitespace=-blank-at-eol diff --check` passes. No source
  exporter or protected file was changed to suppress these formatting diagnostics.
- Final protected/source/test/ATTIC/root-document diff is empty. Only statistics
  exports/documentation and three provenance helpers changed; worktree clean.

Quiet-window lock was absent before each scan/generator/test launch; no lock was
removed. No native agent executable, provider call, network, fetch, push or gh.
No new top-level execution directory. No merge or branch cleanup.

## Evidence and handoff

All scratch/evidence lives in `{SCRATCH}`: `draft-audit.json`, `inventory.txt`,
12 per-draft reference logs, `level4.json`, generator logs, `check-sync.log`,
`pytest-canary.log`, `canary.xml`, `pytest-schema.log`, `schema.xml`,
`verification.json`, basetemps and bytecode. Commands are recorded in run logs.

Committed helpers: `scripts/adhoc/d100_cleanup_20261108.py`,
`scripts/adhoc/d100_export_stats_20261108.py`,
`scripts/adhoc/d100_handoff_20261108.py`.

The requested report is written here; exactly one entry is added under
`### codex` in canonical STATUS.md. Stop after handoff. Ag y's publication lane
should review the retention decisions, supplementary-table limitation and
D100-R1 issue record before opening the stacked PR; no merge is authorized.
'''.replace("Ag y's", "Agy's")
assert not REPORT.exists(), 'Refuse to overwrite an existing report'
status = STATUS.read_text()
marker = '### codex\n'
assert status.count(marker) == 1
entry = f"\n- {now} — **D100 cleanup local handoff; stopped.** Commit `{head}` on `agy/prepub-cleanup-20261108` (base `5d6dd97c2`), no push. All 12 root drafts match ATTIC but are retained per the brief because preserved provenance manifests reference their root paths. Basic/extended schema stats refreshed to 3.2.0; historical RAI/property selections retained and labeled. Root README/CLAUDE have no current version declaration to replace. `make check-sync` passed; schema suite **{counts['tests']} passed**, zero failures/errors/skips, plus one canary; max two workers and 3600-second deadline. Protected files unchanged. Offline, no native executable/network/provider/gh. [Report](../../../d4d-executions/plans/reviews/d100_cleanup_2026-11-08.md); all evidence in `scratch-d100-cleanup`. D100-R1 local review finding fixed; GitHub issue filing deferred to agy under offline restriction. Exactly one STATUS entry; agy owns publication.\n"
assert 'D100 cleanup local handoff' not in status
REPORT.write_text(text)
STATUS.write_text(status.replace(marker, marker + entry, 1))
assert REPORT.stat().st_size > 0
assert STATUS.read_text().count(entry) == 1
print(head, REPORT)
