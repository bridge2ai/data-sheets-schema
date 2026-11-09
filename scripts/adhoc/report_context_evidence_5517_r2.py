"""#5517 Round 2 audit and handoff, 2026-11-08.
Inputs: final local diff, context audit, pin ledger and test XML in authorized scratch.
Outputs: scratch verification/report; --handoff appends the named shared report and
exactly one codex STATUS entry after commit. Never contacts a service.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-codex-5517'
REPORT = ROOT.parent / 'plans/reviews/codex_5517_2026-11-08.md'
STATUS = ROOT.parent.parent / 'data-sheets-schema/notes/coordination/STATUS.md'
BASE = '5ab230659799923741ba24dec1ef3ec06e326ab0'
MARKER = '## Round 2 — D101 quotations and D102 live pins'
STATUS_MARKER = '**#5517 Round 2 / D101–D102 complete; stopped.**'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True)

rows = json.loads((SCRATCH / 'r2-audit.json').read_text())
pins = json.loads((SCRATCH / 'r2-pin-ledger.json').read_text())
assert len(rows) == 42
assert Counter(row['state'] for row in rows) == {'quoted': 40, 'needs_owner': 2}
for row in rows:
    path = ROOT / f'data/context/{row["project"]}_context.yaml'
    current = yaml.safe_load(path.read_text())[row['predicate']]
    baseline = yaml.safe_load(git('show', f'{BASE}:{path.relative_to(ROOT)}'))[row['predicate']]
    assert current['evidence'] == row['evidence']
    assert current['value'] is baseline['value'] is row['value']
    assert re.findall(r'\[curator_assertion:[^]]+\]', current['evidence']) == re.findall(r'\[curator_assertion:[^]]+\]', baseline['evidence'])
    assert hashlib.sha256((ROOT / row['bundle']).read_bytes()).hexdigest() == row['bundle_sha256']
# The decision record changes only its six live pins.
note = Path('notes/reviews/v10_human_decisions_and_context_review_2026-10-20.md')
expected_note = git('show', f'{BASE}:{note}')
for pin in pins:
    assert expected_note.count(pin['old']) == 1
    expected_note = expected_note.replace(pin['old'], pin['new'])
assert (ROOT / note).read_text() == expected_note
allowed = {f'data/context/{r["project"]}_context.yaml' for r in rows} | {
    str(note), 'tests/test_context_evidence_verbatim.py', 'tests/test_evaluation_context_files.py',
    'scripts/adhoc/run_context_evidence_5517_tests.py', 'scripts/adhoc/context_evidence_5517_r2.py',
    'scripts/adhoc/context_evidence_5517_r2_pins.py', 'scripts/adhoc/report_context_evidence_5517_r2.py',
}
assert set(git('diff', BASE, '--name-only').splitlines()) <= allowed
assert set(git('ls-files', '--others', '--exclude-standard').splitlines()) <= allowed
assert not git('diff', BASE, '--', 'src/', 'data/preprocessed/', 'data/rubric/', 'notes/matched_cborg_2026-09-17_v10t/registration.public.json')
assert not git('diff', '--check')
results = []
all_ids = set()
for label in ('canary-r2', 'literal-r2review', 'focused-r2review', 'evaluation-r2'):
    log = SCRATCH / (label + '.log')
    xml = SCRATCH / (label + '.xml')
    assert log.stat().st_size and xml.stat().st_size
    tree = ET.parse(xml)
    suite = tree.getroot().find('testsuite')
    assert suite is not None
    counts = {k: int(suite.get(k)) for k in ('tests', 'failures', 'errors', 'skipped')}
    assert counts['failures'] == counts['errors'] == counts['skipped'] == 0
    cases = tree.findall('.//testcase')
    assert len(cases) == counts['tests']
    all_ids.update((case.get('classname'), case.get('name')) for case in cases)
    results.append(dict(label=label, **counts, seconds=suite.get('time'), xml_sha256=hashlib.sha256(xml.read_bytes()).hexdigest()))
# Preserve complete keyword search output, not just terminal excerpts.
for project, terms in [('cm4ai', r'access|restricted|unrestricted|public|download|licens|embargo'),
                       ('kids_first', r'machine learning|training|\bAI\b|model|research|resource')]:
    bundle = next(row['bundle'] for row in rows if row['project'] == project)
    with (SCRATCH / f'r2-search-{project}.txt').open('w') as out:
        result = subprocess.run(['rg', '--hidden', '--no-ignore', '-n', '-i', terms, bundle], cwd=ROOT, stdout=out)
    assert result.returncode == 0
verification = {'base': BASE, 'head': git('rev-parse', 'HEAD').strip(), 'values_preserved': 42,
                'owner_metadata_preserved': 2, 'counts': dict(Counter(r['state'] for r in rows)),
                'test_results': results, 'distinct_test_cases': len(all_ids),
                'protected_and_historical_diff_empty': True,
                'dependency_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ('pyproject.toml', 'poetry.lock')}}
(SCRATCH / 'r2-verification.json').write_text(json.dumps(verification, indent=2) + '\n')
head = verification['head']
body = f'''\n\n{MARKER}

Local head: `{head}`; parent proposal: `{BASE}`. Branch: `codex/5517-context-evidence-20261108`. Offline local handoff only; no push or PR action. This section supersedes Round 1's red literal gate and stale live-pin disposition, not its historical observations.

All 42 values and both exact D52 curator-decision strings are preserved. **40 entries are quotation-backed; 2 are explicitly `needs_owner`.** These are not two skipped tests or two proved negative values. The closed evidence grammar requires cited JSON-quoted source text, rejects uncited suffixes, case/whitespace mutations and wrong chunk citations, and checks both bundle and chunk SHA256. It validates all quotations even within unresolved entries, requires substantive search notes, checks the exact unresolved inventory and counts 40 + 2 = 42. Each narrative has its own passing test; the inventory test prevents accidental hiding or expansion of unresolved states. Lexical acceptance does not automate entailment or replace #2912 owner review.

The two unresolved entries are:
'''
for row in rows:
    if row['state'] == 'needs_owner':
        body += f'\n- **{row["project"]}.{row["predicate"]} = {str(row["value"]).lower()}**: {row["search_notes"]} The quotation in the table is contextual evidence, not proof of the retained negative.\n'
body += '''
The pediatric ML entry combines the pediatric release's AI-tool purpose with the declared parent protocol's predictive-model objective; it does not assert that trained models were released. AI-READI's software quote names the documented REDCap acquisition tool (E8.4 is “Software and Tools Documented”). Its shared-data quote states actual sharing through FAIRhub. The older AI-READI regression demanded a paraphrase absent from the entire declared bundle; it now requires the exact `WaveForm DataBase (WFDB)` name plus the quoted OMOP mapping, while the new strict gate verifies source provenance. No rubric or production evaluator changed.

### Validation and constraints

The CHORUS write canary was read back before applying the remaining contexts. A one-test canary used the same launcher, interpreter, environment, scratch location and two-worker mode as the suites; its nonempty log/XML and passing testcase were inspected before suite execution. It proves test launch and artifact persistence, not source entailment. Earlier strict runs passed 44 tests; final strict/focused runs followed the stronger actual-sharing quotation for AI-READI and the review correction to Kids First collection evidence.

| Run | Passed | Failures / errors / skips | Seconds | Evidence |
| --- | ---: | --- | ---: | --- |
'''
for result in results:
    body += f'| {result["label"]} | {result["tests"]} | 0 / 0 / 0 | {result["seconds"]} | `{SCRATCH / result["label"]}.log`, `.xml` |\n'
body += f'''
These final executions cover **{len(all_ids)} distinct tests** (the canary/mutation test overlaps). Focused validation includes the now-green decision-table synchronization test. Evaluation validation covers `tests/test_evaluation/test_general_context.py` and `tests/test_evaluation/test_semantic_context_scope.py`. Full repository tests were not requested or run.

Interpreter: existing primary `.venv/bin/python`. Absolute `PYTHONPATH={ROOT}/src:{ROOT}`. Every pytest invocation has `-n 2`, a process-group 3600-second deadline, scratch-only basetemp/TMPDIR, no pytest cache, and bytecode disabled. The quiet lock was absent before starts and the supervisor checked during runs; no interruption occurred. No native agent executable, provider/network call, fetch, push, gh, or notification. No new top-level execution directory. All scratch, logs, XML, audit and search evidence reside in `{SCRATCH}`. Committed helpers under `scripts/adhoc/` are provenance source, not scratch.

### D102 pin inventory and rotation

The repository-wide `rg --hidden --no-ignore --text -n -F -f r2-pin-patterns.txt .` search included ignored/hidden files. Patterns cover all six context paths/basenames, the old live normalized hashes, and raw/normalized hashes at both Round 1 and its pre-proposal baseline. `r2-pin-search.txt` retains the complete results. Only the decision table contains live hash pins. Other matches are context filename fixtures/tests, the Round 1 report helper, and historical CI collection evidence. **No context path or old raw/normalized hash is pinned in `src/download/prompts/canonical_hashes.yaml`; no protected packet or `d4d api prompts pin` command is needed.** The protected registry, production code, source bundles/manifests, rubrics and all historical registrations are byte-unchanged against the starting commit. The v10t registration references a separate Kids First applicability file and was not rotated.

Only the six normalized hashes in `notes/reviews/v10_human_decisions_and_context_review_2026-10-20.md` §1.1 changed; every other byte of that decision record is preserved. Exact old/new table lines are in `r2-pin-ledger.json`.

| Project | Old live normalized SHA256 | New normalized SHA256 |
| --- | --- | --- |
'''
for pin in pins:
    body += f'| {pin["project"]} | `{pin["old"]}` | `{pin["new"]}` |\n'
body += '''
### Reviewer table: all 42 narratives

Each cell uses JSON string notation so `\\n` denotes an actual source newline and embedded quotes remain unambiguous. Each quotation is paired in order with its bundle line and containing chunk. `needs_owner` quotations supply context only. Original and final evidence strings are recoverable from Git; `r2-audit.json` records the final strings, source hashes, locations and search notes.

| Predicate | Retained value | Quotations (JSON notation) | Bundle line / chunk, in quotation order | State |
| --- | --- | --- | --- | --- |
'''
for row in rows:
    quotes = '<br>'.join('<code>' + html.escape(json.dumps(q, ensure_ascii=False)).replace('|', '&#124;') + '</code>' for q in row['quotations'])
    locs = '<br>'.join('`' + loc + '`' for loc in row['locations'])
    body += f'| {row["project"]}.{row["predicate"]} | {str(row["value"]).lower()} | {quotes} | {locs} | {row["state"]} |\n'
body += '''
### Read-only review and disposition

A separate read-only pass checked the complete patch, quotation-to-predicate support, unchanged D52 values/metadata, explicit unresolved-state accounting, mutation refusals, exact pin-only decision-record diff, protected/historical paths and test artifacts. It found R2-F1 below. The review pass ended before fixing it; a subsequent read-only pass checked the corrected cohort quotation and live digest. The two unresolved evidence questions remain with the already assigned #5517/#2912 owner review; neither is silently treated as a proven negative. No merge or scientific completion is claimed. The authoring, pin-inventory and report helpers are committed with the change. After this report and exactly one codex STATUS entry, stopped.

**R2-F1 — issue-ready finding for agy (fixed locally; GitHub filing deferred by explicit offline/no-gh instruction).** Title: “Applicability evidence: literal matching can accept acknowledgment-template language.” The first Round 2 Kids First data_collection selection used “Additional funds supported assembling the cohorts, collecting the phenotypic data and samples, and/or data analysis.” from c004, line 224. Surrounding text includes placeholders for acknowledgment authors, so it does not establish a specific actual collection despite passing lexical matching. Replaced with the c034 cohort statement at line 3268 describing 550 kidney/urinary-tract-anomaly trios and their collected phenotypic data; the exact verified chunk is listed in the reviewer table. Values remain unchanged. Acceptance: a non-template collection quotation, strict literal/chunk gate, focused synchronization all pass. This is addressed within this patch; agy must still file the review record when online. The lexical gate intentionally cannot judge entailment or distinguish all templates from study assertions, so human review remains required.
'''
(SCRATCH / 'r2-report-section.md').write_text(body)
if '--handoff' in sys.argv:
    assert not git('status', '--porcelain'), 'commit first; worktree must be clean'
    old_report, status = REPORT.read_text(), STATUS.read_text()
    assert MARKER not in old_report and STATUS_MARKER not in status
    assert status.count('\n### codex\n') == 1
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    summary = ', '.join(f'{r["label"]}: {r["tests"]} passed' for r in results)
    entry = f'\n- {timestamp} — {STATUS_MARKER} Local commit `{head}` on `codex/5517-context-evidence-20261108`, no push. All 42 values / both D52 strings retained; 40 quotation-backed and 2 counted `needs_owner` (CM4AI regulated_access; KIDS_FIRST ml_training_dataset). Six live normalized pins rotated; no canonical pin packet, protected edit or historical-registration change. {summary}; {len(all_ids)} distinct final tests, zero failures/errors/skips, synchronization green. Report: `d4d-executions/plans/reviews/codex_5517_2026-11-08.md`, Round 2; all evidence in `d4d-executions/scratch-codex-5517`. Offline, quiet-lock/deadline/two-worker rules observed; no native executable/network/gh. Lead/agy review and owner disposition of the two unresolved entries next. Stopped.\n'
    updated = status.replace('\n### codex\n', '\n### codex\n' + entry, 1)
    REPORT.write_text(old_report + body)
    assert REPORT.read_text() == old_report + body
    # Refuse to overwrite a concurrent STATUS change.
    assert STATUS.read_text() == status
    STATUS.write_text(updated)
    assert STATUS.read_text() == updated and updated.count(STATUS_MARKER) == 1
print(json.dumps(verification, indent=2))
